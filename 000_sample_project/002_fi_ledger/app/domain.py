"""총계정원장 도메인 로직.

웹 프레임워크와 무관한 순수 파이썬 코드로, 계정과목·분개 전표·시산표·계정별 원장을 다룬다.
모든 금액은 float 오차를 피하기 위해 Decimal 로 계산한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

ZERO = Decimal("0")


class AccountType(str, Enum):
    """계정 유형."""

    ASSET = "asset"  # 자산
    LIABILITY = "liability"  # 부채
    EQUITY = "equity"  # 자본
    REVENUE = "revenue"  # 수익
    EXPENSE = "expense"  # 비용


class Side(str, Enum):
    """차변/대변."""

    DEBIT = "debit"  # 차변
    CREDIT = "credit"  # 대변


# 계정 유형별 정상잔액 방향: 자산·비용은 차변, 부채·자본·수익은 대변
NORMAL_SIDE: dict[AccountType, Side] = {
    AccountType.ASSET: Side.DEBIT,
    AccountType.EXPENSE: Side.DEBIT,
    AccountType.LIABILITY: Side.CREDIT,
    AccountType.EQUITY: Side.CREDIT,
    AccountType.REVENUE: Side.CREDIT,
}


class LedgerError(Exception):
    """도메인 규칙 위반의 공통 부모 예외."""


class AccountNotFoundError(LedgerError):
    """존재하지 않는 계정과목."""


class DuplicateAccountError(LedgerError):
    """이미 등록된 계정 코드."""


class EntryNotFoundError(LedgerError):
    """존재하지 않는 전표."""


class InvalidEntryError(LedgerError):
    """차대 불일치, 라인 부족, 음수 금액 등 잘못된 전표."""


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    type: AccountType

    @property
    def normal_side(self) -> Side:
        return NORMAL_SIDE[self.type]


@dataclass(frozen=True)
class JournalLine:
    account_code: str
    side: Side
    amount: Decimal


@dataclass(frozen=True)
class JournalEntry:
    id: int
    entry_date: date
    description: str
    lines: tuple[JournalLine, ...]

    def total(self, side: Side) -> Decimal:
        return sum((ln.amount for ln in self.lines if ln.side == side), ZERO)


@dataclass(frozen=True)
class TrialBalanceRow:
    account: Account
    debit_total: Decimal
    credit_total: Decimal
    # 정상잔액 방향 기준 잔액 (음수면 반대 방향 잔액이라는 뜻)
    balance: Decimal


@dataclass(frozen=True)
class LedgerRow:
    entry_id: int
    entry_date: date
    description: str
    debit: Decimal
    credit: Decimal
    # 정상잔액 방향 기준 누적 잔액
    balance: Decimal


def signed_amount(account: Account, debit: Decimal, credit: Decimal) -> Decimal:
    """정상잔액 방향 기준으로 잔액 증감액을 계산한다."""
    if account.normal_side == Side.DEBIT:
        return debit - credit
    return credit - debit


# 시드용 기본 계정과목
DEFAULT_ACCOUNTS: list[Account] = [
    Account("1010", "현금", AccountType.ASSET),
    Account("1100", "매출채권", AccountType.ASSET),
    Account("2010", "매입채무", AccountType.LIABILITY),
    Account("3010", "자본금", AccountType.EQUITY),
    Account("4010", "매출", AccountType.REVENUE),
    Account("5010", "급여", AccountType.EXPENSE),
    Account("5020", "임차료", AccountType.EXPENSE),
]


@dataclass
class Ledger:
    """인메모리 총계정원장."""

    accounts: dict[str, Account] = field(default_factory=dict)
    entries: dict[int, JournalEntry] = field(default_factory=dict)
    _next_entry_id: int = 1

    @classmethod
    def with_defaults(cls) -> "Ledger":
        ledger = cls()
        for account in DEFAULT_ACCOUNTS:
            ledger.add_account(account.code, account.name, account.type)
        return ledger

    # ---- 계정과목 ----
    def add_account(self, code: str, name: str, type: AccountType) -> Account:
        if code in self.accounts:
            raise DuplicateAccountError(f"이미 존재하는 계정 코드입니다: {code}")
        account = Account(code=code, name=name, type=AccountType(type))
        self.accounts[code] = account
        return account

    def get_account(self, code: str) -> Account:
        try:
            return self.accounts[code]
        except KeyError:
            raise AccountNotFoundError(f"존재하지 않는 계정입니다: {code}") from None

    def list_accounts(self) -> list[Account]:
        return sorted(self.accounts.values(), key=lambda a: a.code)

    # ---- 분개 전표 ----
    def post_entry(
        self, entry_date: date, description: str, lines: list[JournalLine]
    ) -> JournalEntry:
        """규칙을 검증한 뒤 전표를 기표한다."""
        if len(lines) < 2:
            raise InvalidEntryError("전표 라인은 최소 2개 이상이어야 합니다.")
        for line in lines:
            if line.amount <= ZERO:
                raise InvalidEntryError("금액은 0보다 커야 합니다.")
            # 존재하지 않는 계정이면 기표하지 않는다
            if line.account_code not in self.accounts:
                raise InvalidEntryError(f"존재하지 않는 계정입니다: {line.account_code}")

        entry = JournalEntry(
            id=self._next_entry_id,
            entry_date=entry_date,
            description=description,
            lines=tuple(lines),
        )
        debit, credit = entry.total(Side.DEBIT), entry.total(Side.CREDIT)
        if debit != credit:
            raise InvalidEntryError(
                f"차변 합계({debit})와 대변 합계({credit})가 일치하지 않습니다."
            )

        self.entries[entry.id] = entry
        self._next_entry_id += 1
        return entry

    def get_entry(self, entry_id: int) -> JournalEntry:
        try:
            return self.entries[entry_id]
        except KeyError:
            raise EntryNotFoundError(f"존재하지 않는 전표입니다: {entry_id}") from None

    def list_entries(self) -> list[JournalEntry]:
        return list(self.entries.values())

    def _sorted_entries(self) -> list[JournalEntry]:
        # 일자 순, 같은 일자면 기표 순
        return sorted(self.entries.values(), key=lambda e: (e.entry_date, e.id))

    # ---- 조회 ----
    def trial_balance(self) -> list[TrialBalanceRow]:
        """계정별 차변·대변 합계와 정상잔액 방향 기준 잔액을 계산한다."""
        totals = {code: [ZERO, ZERO] for code in self.accounts}
        for entry in self.entries.values():
            for line in entry.lines:
                idx = 0 if line.side == Side.DEBIT else 1
                totals[line.account_code][idx] += line.amount

        rows = []
        for account in self.list_accounts():
            debit, credit = totals[account.code]
            rows.append(
                TrialBalanceRow(
                    account=account,
                    debit_total=debit,
                    credit_total=credit,
                    balance=signed_amount(account, debit, credit),
                )
            )
        return rows

    def account_ledger(self, code: str) -> list[LedgerRow]:
        """한 계정의 거래 내역과 누적 잔액을 반환한다."""
        account = self.get_account(code)
        rows: list[LedgerRow] = []
        balance = ZERO
        for entry in self._sorted_entries():
            for line in entry.lines:
                if line.account_code != code:
                    continue
                debit = line.amount if line.side == Side.DEBIT else ZERO
                credit = line.amount if line.side == Side.CREDIT else ZERO
                balance += signed_amount(account, debit, credit)
                rows.append(
                    LedgerRow(
                        entry_id=entry.id,
                        entry_date=entry.entry_date,
                        description=entry.description,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                    )
                )
        return rows
