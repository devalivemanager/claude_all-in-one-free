"""API 테스트: TestClient(httpx)로 HTTP 계층을 검증한다."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.domain import JournalEntry, JournalLine, Ledger, Side
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    # 테스트마다 새 인메모리 원장을 가진 앱을 만들어 서로 격리한다
    return TestClient(create_app())


def entry_body(*lines, entry_date="2026-01-01", description="테스트"):
    return {
        "entry_date": entry_date,
        "description": description,
        "lines": [
            {"account_code": code, "side": side, "amount": amount}
            for code, side, amount in lines
        ],
    }


def test_account_list_includes_seed_accounts(client):
    """계정과목 목록에 시드가 포함된다"""
    res = client.get("/accounts")
    assert res.status_code == 200
    codes = {a["code"] for a in res.json()}
    assert {"1010", "1100", "2010", "3010", "4010", "5010"} <= codes


def test_create_and_get_account(client):
    """계정과목 등록과 조회"""
    res = client.post("/accounts", json={"code": "2100", "name": "미지급금", "type": "liability"})
    assert res.status_code == 201
    assert res.json() == {
        "code": "2100",
        "name": "미지급금",
        "type": "liability",
        "normal_side": "credit",
    }
    assert client.get("/accounts/2100").json()["name"] == "미지급금"


def test_duplicate_account_code_returns_409(client):
    """중복 계정코드는 409"""
    res = client.post("/accounts", json={"code": "1010", "name": "현금2", "type": "asset"})
    assert res.status_code == 409


def test_invalid_account_type_returns_422(client):
    """잘못된 계정유형은 422"""
    res = client.post("/accounts", json={"code": "9000", "name": "?", "type": "unknown"})
    assert res.status_code == 422


def test_unknown_account_returns_404(client):
    """없는 계정 조회는 404"""
    assert client.get("/accounts/9999").status_code == 404


def test_post_and_get_journal_entry(client):
    """전표 등록과 조회"""
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", "1000.50"), ("3010", "credit", 1000.50)),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1
    # Decimal 은 문자열로 직렬화된다
    assert Decimal(body["debit_total"]) == Decimal(body["credit_total"]) == Decimal("1000.50")

    assert client.get("/journal-entries/1").json() == body
    assert client.get("/journal-entries").json() == [body]


def test_unknown_entry_returns_404(client):
    """없는 전표 조회는 404"""
    assert client.get("/journal-entries/99").status_code == 404


def test_unbalanced_entry_returns_422(client):
    """차대 불일치는 422"""
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", "100"), ("3010", "credit", "90")),
    )
    assert res.status_code == 422
    assert "일치하지 않습니다" in res.json()["detail"]
    assert client.get("/journal-entries").json() == []


def test_single_line_entry_returns_422(client):
    """라인 1개는 422"""
    res = client.post("/journal-entries", json=entry_body(("1010", "debit", "100")))
    assert res.status_code == 422


@pytest.mark.parametrize("amount", ["0", "-10"])
def test_non_positive_amount_returns_422(client, amount):
    """양수가 아닌 금액은 422"""
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", amount), ("3010", "credit", amount)),
    )
    assert res.status_code == 422


def test_amount_with_three_decimals_returns_422(client):
    """소수점 셋째자리 금액은 422"""
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", "1.001"), ("3010", "credit", "1.001")),
    )
    assert res.status_code == 422


def test_entry_with_unknown_account_returns_422(client):
    """존재하지 않는 계정의 전표는 422"""
    res = client.post(
        "/journal-entries",
        json=entry_body(("9999", "debit", "100"), ("3010", "credit", "100")),
    )
    assert res.status_code == 422
    assert "9999" in res.json()["detail"]


def _post_samples(client: TestClient) -> None:
    samples = [
        entry_body(("1010", "debit", "1000"), ("3010", "credit", "1000"), entry_date="2026-01-01"),
        entry_body(("1100", "debit", "300"), ("4010", "credit", "300"), entry_date="2026-01-05"),
        entry_body(("5010", "debit", "200"), ("1010", "credit", "200"), entry_date="2026-01-25"),
    ]
    for body in samples:
        assert client.post("/journal-entries", json=body).status_code == 201


def test_trial_balance(client):
    """시산표 조회"""
    _post_samples(client)
    res = client.get("/trial-balance")
    assert res.status_code == 200
    body = res.json()
    assert body["is_balanced"] is True
    assert Decimal(body["debit_total"]) == Decimal(body["credit_total"]) == Decimal("1500")

    rows = {r["account_code"]: r for r in body["rows"]}
    assert Decimal(rows["1010"]["balance"]) == Decimal("800")
    assert rows["1010"]["normal_side"] == "debit"
    assert Decimal(rows["4010"]["balance"]) == Decimal("300")
    assert rows["4010"]["normal_side"] == "credit"


def test_trial_balance_reports_unbalanced_ledger():
    """장부가 어긋나면 시산표가 is_balanced=false 로 드러낸다

    정상 경로(전표 등록)는 차대 불일치를 막으므로 시산표가 어긋날 일이 없다.
    그래서 이 검사는 일괄 업로드·데이터 손상처럼 검증을 우회한 경우의 마지막 방어선이다.
    검증을 거치지 않은 불일치 전표를 장부에 직접 넣어 그 상황을 만든다.
    """
    ledger = Ledger.with_defaults()
    ledger.entries[1] = JournalEntry(
        id=1,
        entry_date=date(2026, 1, 1),
        description="검증을 우회한 불일치 전표",
        lines=(
            JournalLine("1010", Side.DEBIT, Decimal("1000")),
            JournalLine("3010", Side.CREDIT, Decimal("900")),
        ),
    )
    body = TestClient(create_app(ledger)).get("/trial-balance").json()

    assert body["is_balanced"] is False
    assert Decimal(body["debit_total"]) == Decimal("1000")
    assert Decimal(body["credit_total"]) == Decimal("900")


def test_account_ledger(client):
    """계정별 원장 조회"""
    _post_samples(client)
    res = client.get("/accounts/1010/ledger")
    assert res.status_code == 200
    body = res.json()
    assert body["account"]["name"] == "현금"
    assert [Decimal(r["balance"]) for r in body["rows"]] == [Decimal("1000"), Decimal("800")]
    assert Decimal(body["ending_balance"]) == Decimal("800")
    assert Decimal(body["debit_total"]) == Decimal("1000")
    assert Decimal(body["credit_total"]) == Decimal("200")


def test_ledger_of_unused_account_is_empty(client):
    """거래없는 계정의 원장은 빈 목록"""
    body = client.get("/accounts/2010/ledger").json()
    assert body["rows"] == []
    assert Decimal(body["ending_balance"]) == Decimal("0")


def test_ledger_of_unknown_account_returns_404(client):
    """없는 계정의 원장은 404"""
    assert client.get("/accounts/9999/ledger").status_code == 404
