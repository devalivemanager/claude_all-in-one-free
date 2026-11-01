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


def test_기본_계정과목이_시드된다(ledger):
    names = {a.name for a in ledger.list_accounts()}
    assert {"현금", "매출채권", "매입채무", "자본금", "매출", "급여"} <= names


def test_계정_유형별_정상잔액_방향(ledger):
    assert ledger.get_account("1010").normal_side == Side.DEBIT  # 자산
    assert ledger.get_account("5010").normal_side == Side.DEBIT  # 비용
    assert ledger.get_account("2010").normal_side == Side.CREDIT  # 부채
    assert ledger.get_account("3010").normal_side == Side.CREDIT  # 자본
    assert ledger.get_account("4010").normal_side == Side.CREDIT  # 수익


def test_계정_등록과_중복_거부(ledger):
    account = ledger.add_account("1200", "미수금", AccountType.ASSET)
    assert ledger.get_account("1200") == account
    with pytest.raises(DuplicateAccountError):
        ledger.add_account("1200", "중복", AccountType.ASSET)


def test_없는_계정_조회는_예외(ledger):
    with pytest.raises(AccountNotFoundError):
        ledger.get_account("9999")


def test_균형_잡힌_전표는_기표된다(ledger):
    entry = ledger.post_entry(
        date(2026, 1, 1), "자본금 납입", [dr("1010", "1000000"), cr("3010", "1000000")]
    )
    assert entry.id == 1
    assert ledger.get_entry(1) is entry
    assert entry.total(Side.DEBIT) == entry.total(Side.CREDIT) == D("1000000")


def test_전표_번호는_순차_증가(ledger):
    e1 = ledger.post_entry(date(2026, 1, 1), "", [dr("1010", "1"), cr("3010", "1")])
    e2 = ledger.post_entry(date(2026, 1, 2), "", [dr("1010", "1"), cr("3010", "1")])
    assert (e1.id, e2.id) == (1, 2)


def test_차대_불일치_전표는_거부(ledger):
    with pytest.raises(InvalidEntryError, match="일치하지 않습니다"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("1010", "100"), cr("3010", "99")])
    assert ledger.list_entries() == []


def test_라인이_2개_미만이면_거부(ledger):
    with pytest.raises(InvalidEntryError, match="최소 2개"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("1010", "100")])


@pytest.mark.parametrize("amount", ["0", "-100"])
def test_금액이_양수가_아니면_거부(ledger, amount):
    with pytest.raises(InvalidEntryError, match="0보다"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("1010", amount), cr("3010", amount)])


def test_존재하지_않는_계정이_포함되면_거부(ledger):
    with pytest.raises(InvalidEntryError, match="존재하지 않는 계정"):
        ledger.post_entry(date(2026, 1, 1), "", [dr("9999", "100"), cr("3010", "100")])


def test_없는_전표_조회는_예외(ledger):
    with pytest.raises(EntryNotFoundError):
        ledger.get_entry(42)


def test_Decimal_로_정확히_계산된다(ledger):
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


def test_시산표는_차대_합계가_같고_정상잔액_방향을_반영한다(ledger):
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


def test_계정별_원장은_일자순_누적잔액을_보여준다(ledger):
    _post_sample_entries(ledger)
    rows = ledger.account_ledger("1010")

    # 1/10 전표가 나중에 기표됐어도 일자순으로 정렬된다
    assert [r.entry_date.day for r in rows] == [1, 10, 25]
    assert [r.balance for r in rows] == [D("1000"), D("1100"), D("900")]
    assert rows[2].credit == D("200") and rows[2].debit == D("0")


def test_대변_정상계정의_원장_잔액(ledger):
    _post_sample_entries(ledger)
    rows = ledger.account_ledger("4010")
    assert [r.balance for r in rows] == [D("300")]


def test_없는_계정의_원장_조회는_예외(ledger):
    with pytest.raises(AccountNotFoundError):
        ledger.account_ledger("9999")
