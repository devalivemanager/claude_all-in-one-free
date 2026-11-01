"""API 요청/응답 스키마 (Pydantic v2).

Decimal 금액은 JSON 응답에서 정밀도 손실을 막기 위해 문자열(예: "1000.00")로 직렬화된다.
요청에서는 숫자와 문자열을 모두 받는다.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from app.domain import AccountType, Side

# 양수, 소수점 둘째 자리까지 허용하는 금액 타입
Amount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class AccountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=10, examples=["1200"])
    name: str = Field(min_length=1, max_length=50, examples=["미수금"])
    type: AccountType


class AccountOut(BaseModel):
    code: str
    name: str
    type: AccountType
    normal_side: Side


class JournalLineIn(BaseModel):
    account_code: str
    side: Side
    amount: Amount


class JournalEntryCreate(BaseModel):
    entry_date: date
    description: str = Field(default="", max_length=200)
    lines: list[JournalLineIn] = Field(min_length=2)


class JournalLineOut(BaseModel):
    account_code: str
    side: Side
    amount: Decimal


class JournalEntryOut(BaseModel):
    id: int
    entry_date: date
    description: str
    lines: list[JournalLineOut]
    debit_total: Decimal
    credit_total: Decimal


class TrialBalanceRowOut(BaseModel):
    account_code: str
    account_name: str
    account_type: AccountType
    normal_side: Side
    debit_total: Decimal
    credit_total: Decimal
    balance: Decimal


class TrialBalanceOut(BaseModel):
    rows: list[TrialBalanceRowOut]
    debit_total: Decimal
    credit_total: Decimal
    is_balanced: bool


class LedgerRowOut(BaseModel):
    entry_id: int
    entry_date: date
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class AccountLedgerOut(BaseModel):
    account: AccountOut
    rows: list[LedgerRowOut]
    debit_total: Decimal
    credit_total: Decimal
    ending_balance: Decimal
