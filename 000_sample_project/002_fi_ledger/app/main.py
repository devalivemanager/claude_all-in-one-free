"""FastAPI 애플리케이션: 도메인 객체를 HTTP API 로 노출한다."""

from __future__ import annotations

from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Request

from app.domain import (
    ZERO,
    Account,
    AccountNotFoundError,
    DuplicateAccountError,
    EntryNotFoundError,
    InvalidEntryError,
    JournalEntry,
    JournalLine,
    Ledger,
    Side,
)
from app.schemas import (
    AccountCreate,
    AccountLedgerOut,
    AccountOut,
    JournalEntryCreate,
    JournalEntryOut,
    JournalLineOut,
    LedgerRowOut,
    TrialBalanceOut,
    TrialBalanceRowOut,
)


def get_ledger(request: Request) -> Ledger:
    """앱 상태에 보관된 인메모리 원장을 꺼낸다."""
    return request.app.state.ledger


def to_account_out(account: Account) -> AccountOut:
    return AccountOut(
        code=account.code,
        name=account.name,
        type=account.type,
        normal_side=account.normal_side,
    )


def to_entry_out(entry: JournalEntry) -> JournalEntryOut:
    return JournalEntryOut(
        id=entry.id,
        entry_date=entry.entry_date,
        description=entry.description,
        lines=[
            JournalLineOut(account_code=ln.account_code, side=ln.side, amount=ln.amount)
            for ln in entry.lines
        ],
        debit_total=entry.total(Side.DEBIT),
        credit_total=entry.total(Side.CREDIT),
    )


def create_app(ledger: Ledger | None = None) -> FastAPI:
    """앱을 만든다. 테스트에서는 매번 새 원장을 넣어 서로 격리한다."""
    app = FastAPI(title="FI 총계정원장 API", version="0.1.0")
    app.state.ledger = ledger if ledger is not None else Ledger.with_defaults()

    # ---- 계정과목 ----
    @app.post("/accounts", response_model=AccountOut, status_code=201)
    def create_account(body: AccountCreate, ledger: Ledger = Depends(get_ledger)):
        try:
            account = ledger.add_account(body.code, body.name, body.type)
        except DuplicateAccountError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return to_account_out(account)

    @app.get("/accounts", response_model=list[AccountOut])
    def list_accounts(ledger: Ledger = Depends(get_ledger)):
        return [to_account_out(a) for a in ledger.list_accounts()]

    @app.get("/accounts/{code}", response_model=AccountOut)
    def get_account(code: str, ledger: Ledger = Depends(get_ledger)):
        try:
            return to_account_out(ledger.get_account(code))
        except AccountNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ---- 분개 전표 ----
    @app.post("/journal-entries", response_model=JournalEntryOut, status_code=201)
    def create_entry(body: JournalEntryCreate, ledger: Ledger = Depends(get_ledger)):
        lines = [
            JournalLine(account_code=ln.account_code, side=ln.side, amount=ln.amount)
            for ln in body.lines
        ]
        try:
            entry = ledger.post_entry(body.entry_date, body.description, lines)
        except InvalidEntryError as e:
            # 차대 불일치, 존재하지 않는 계정 등은 처리할 수 없는 요청(422)으로 거부
            raise HTTPException(status_code=422, detail=str(e))
        return to_entry_out(entry)

    @app.get("/journal-entries", response_model=list[JournalEntryOut])
    def list_entries(ledger: Ledger = Depends(get_ledger)):
        return [to_entry_out(e) for e in ledger.list_entries()]

    @app.get("/journal-entries/{entry_id}", response_model=JournalEntryOut)
    def get_entry(entry_id: int, ledger: Ledger = Depends(get_ledger)):
        try:
            return to_entry_out(ledger.get_entry(entry_id))
        except EntryNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ---- 조회 ----
    @app.get("/trial-balance", response_model=TrialBalanceOut)
    def trial_balance(ledger: Ledger = Depends(get_ledger)):
        rows = ledger.trial_balance()
        debit_total = sum((r.debit_total for r in rows), ZERO)
        credit_total = sum((r.credit_total for r in rows), ZERO)
        return TrialBalanceOut(
            rows=[
                TrialBalanceRowOut(
                    account_code=r.account.code,
                    account_name=r.account.name,
                    account_type=r.account.type,
                    normal_side=r.account.normal_side,
                    debit_total=r.debit_total,
                    credit_total=r.credit_total,
                    balance=r.balance,
                )
                for r in rows
            ],
            debit_total=debit_total,
            credit_total=credit_total,
            is_balanced=debit_total == credit_total,
        )

    @app.get("/accounts/{code}/ledger", response_model=AccountLedgerOut)
    def account_ledger(code: str, ledger: Ledger = Depends(get_ledger)):
        try:
            account = ledger.get_account(code)
        except AccountNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        rows = ledger.account_ledger(code)
        return AccountLedgerOut(
            account=to_account_out(account),
            rows=[LedgerRowOut(**vars(r)) for r in rows],
            debit_total=sum((r.debit for r in rows), ZERO),
            credit_total=sum((r.credit for r in rows), ZERO),
            ending_balance=rows[-1].balance if rows else Decimal("0"),
        )

    return app


# `uvicorn app.main:app` 으로 실행할 때 사용하는 기본 인스턴스
app = create_app()
