"""도메인 단위 테스트: 웹 계층 없이 Ledger 규칙을 검증한다."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain import (
    AccountNotFoundError,
    AccountType,
    DuplicateAccountError,
    EntryNotFoundError,
    InvalidEntryError,
    JournalLine,
    Ledger,
    Side,
)

D = Decimal


def dr(code: str, amount: str) -> JournalLine:
    return JournalLine(code, Side.DEBIT, D(amount))


def cr(code: str, amount: str) -> JournalLine:
    return JournalLine(code, Side.CREDIT, D(amount))


@pytest.fixture
def ledger() -> Ledger:
    return Ledger.with_defaults()


def test_default_accounts_are_seeded(ledger):
    """기본 계정과목이 시드된다"""
    names = {a.name for a in ledger.list_accounts()}
    assert {"현금", "매출채권", "매입채무", "자본금", "매출", "급여"} <= names


def test_normal_side_by_account_type(ledger):
    """계정 유형별 정상잔액 방향"""
    assert ledger.get_account("1010").normal_side == Side.DEBIT  # 자산
    assert ledger.get_account("5010").normal_side == Side.DEBIT  # 비용
    assert ledger.get_account("2010").normal_side == Side.CREDIT  # 부채
    assert ledger.get_account("3010").normal_side == Side.CREDIT  # 자본
    assert ledger.get_account("4010").normal_side == Side.CREDIT  # 수익


def test_add_account_and_reject_duplicate(ledger):
    """계정 등록과 중복 거부"""
    account = ledger.add_account("1200", "미수금", AccountType.ASSET)
    assert ledger.get_account("1200") == account
    with pytest.raises(DuplicateAccountError):
        ledger.add_account("1200", "중복", AccountType.ASSET)


def test_unknown_account_raises(ledger):
    """없는 계정 조회는 예외"""
    with pytest.raises(AccountNotFoundError):
        ledger.get_account("9999")


def test_balanced_entry_is_posted(ledger):
    """균형 잡힌 전표는 기표된다"""
    entry = ledger.post_entry(
        date(2026, 1, 1), "자본금 납입", [dr("1010", "1000000"), cr("3010", "1000000")]
    )
    assert entry.id == 1
    assert ledger.get_entry(1) is entry
    assert entry.total(Side.DEBIT) == entry.total(Side.CREDIT) == D("1000000")


def test_entry_ids_increase_sequentially(ledger):
    """전표 번호는 순차 증가"""
    e1 = ledger.post_entry(date(2026, 1, 1), "", [dr("1010", "1"), cr("3010", "1")])
    e2 = ledger.post_entry(date(2026, 1, 2), "", [dr("1010", "1"), cr("3010", "1")])
    assert (e1.id, e2.id) == (1, 2)


def test_unbalanced_entry_is_rejected(ledger):
    """차대 불일치 전표는 거부"""
    with pytest.raises(InvalidEntryError, match="일치하지 않습니다"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("1010", "100"), cr("3010", "99")])
    assert ledger.list_entries() == []


def test_entry_with_fewer_than_two_lines_is_rejected(ledger):
    """라인이 2개 미만이면 거부"""
    with pytest.raises(InvalidEntryError, match="최소 2개"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("1010", "100")])


@pytest.mark.parametrize("amount", ["0", "-100"])
def test_non_positive_amount_is_rejected(ledger, amount):
    """금액이 양수가 아니면 거부"""
    with pytest.raises(InvalidEntryError, match="0보다"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("1010", amount), cr("3010", amount)])


def test_entry_with_unknown_account_is_rejected(ledger):
    """존재하지 않는 계정이 포함되면 거부"""
    with pytest.raises(InvalidEntryError, match="존재하지 않는 계정"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("9999", "100"), cr("3010", "100")])


def test_unknown_entry_raises(ledger):
    """없는 전표 조회는 예외"""
    with pytest.raises(EntryNotFoundError):
        ledger.get_entry(42)


def test_decimal_arithmetic_is_exact(ledger):
    """Decimal 로 정확히 계산된다"""
    # float 이라면 0.1 + 0.2 != 0.3 이 되어 차대가 맞지 않는다
    entry = ledger.post_entry(
        date(2026, 1, 1),
        "",
        [dr("1010", "0.1"), dr("1010", "0.2"), cr("3010", "0.3")],
    )
    assert entry.total(Side.DEBIT) == D("0.3")


def _post_sample_entries(ledger: Ledger) -> None:
    ledger.post_entry(date(2026, 1, 1), "자본금 납입", [dr("1010", "1000"), cr("3010", "1000")])
    ledger.post_entry(date(2026, 1, 5), "외상 매출", [dr("1100", "300"), cr("4010", "300")])
    ledger.post_entry(date(2026, 1, 25), "급여 지급", [dr("5010", "200"), cr("1010", "200")])
    ledger.post_entry(date(2026, 1, 10), "매출채권 회수", [dr("1010", "100"), cr("1100", "100")])


def test_trial_balance_totals_match_and_follow_normal_side(ledger):
    """시산표는 차대 합계가 같고 정상잔액 방향을 반영한다"""
    _post_sample_entries(ledger)
    rows = {r.account.code: r for r in ledger.trial_balance()}

    assert sum(r.debit_total for r in rows.values()) == sum(
        r.credit_total for r in rows.values()
    )
    assert rows["1010"].balance == D("900")  # 현금(자산): 1000 + 100 - 200
    assert rows["1100"].balance == D("200")  # 매출채권(자산)
    assert rows["3010"].balance == D("1000")  # 자본금(자본): 대변 잔액이 양수
    assert rows["4010"].balance == D("300")  # 매출(수익): 대변 잔액이 양수
    assert rows["5010"].balance == D("200")  # 급여(비용): 차변 잔액이 양수
    assert rows["2010"].balance == D("0")  # 거래 없는 계정도 포함


def test_account_ledger_shows_running_balance_by_date(ledger):
    """계정별 원장은 일자순 누적잔액을 보여준다"""
    _post_sample_entries(ledger)
    rows = ledger.account_ledger("1010")

    # 1/10 전표가 나중에 기표됐어도 일자순으로 정렬된다
    assert [r.entry_date.day for r in rows] == [1, 10, 25]
    assert [r.balance for r in rows] == [D("1000"), D("1100"), D("900")]
    assert rows[2].credit == D("200") and rows[2].debit == D("0")


def test_ledger_balance_of_credit_normal_account(ledger):
    """대변 정상계정의 원장 잔액"""
    _post_sample_entries(ledger)
    rows = ledger.account_ledger("4010")
    assert [r.balance for r in rows] == [D("300")]


def test_ledger_of_unknown_account_raises(ledger):
    """없는 계정의 원장 조회는 예외"""
    with pytest.raises(AccountNotFoundError):
        ledger.account_ledger("9999")
