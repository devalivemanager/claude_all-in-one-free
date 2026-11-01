"""API 테스트: TestClient(httpx)로 HTTP 계층을 검증한다."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

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


def test_계정과목_목록에_시드가_포함된다(client):
    res = client.get("/accounts")
    assert res.status_code == 200
    codes = {a["code"] for a in res.json()}
    assert {"1010", "1100", "2010", "3010", "4010", "5010"} <= codes


def test_계정과목_등록과_조회(client):
    res = client.post("/accounts", json={"code": "2100", "name": "미지급금", "type": "liability"})
    assert res.status_code == 201
    assert res.json() == {
        "code": "2100",
        "name": "미지급금",
        "type": "liability",
        "normal_side": "credit",
    }
    assert client.get("/accounts/2100").json()["name"] == "미지급금"


def test_중복_계정코드는_409(client):
    res = client.post("/accounts", json={"code": "1010", "name": "현금2", "type": "asset"})
    assert res.status_code == 409


def test_잘못된_계정유형은_422(client):
    res = client.post("/accounts", json={"code": "9000", "name": "?", "type": "unknown"})
    assert res.status_code == 422


def test_없는_계정_조회는_404(client):
    assert client.get("/accounts/9999").status_code == 404


def test_전표_등록과_조회(client):
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


def test_없는_전표_조회는_404(client):
    assert client.get("/journal-entries/99").status_code == 404


def test_차대_불일치는_422(client):
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", "100"), ("3010", "credit", "90")),
    )
    assert res.status_code == 422
    assert "일치하지 않습니다" in res.json()["detail"]
    assert client.get("/journal-entries").json() == []


def test_라인_1개는_422(client):
    res = client.post("/journal-entries", json=entry_body(("1010", "debit", "100")))
    assert res.status_code == 422


@pytest.mark.parametrize("amount", ["0", "-10"])
def test_양수가_아닌_금액은_422(client, amount):
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", amount), ("3010", "credit", amount)),
    )
    assert res.status_code == 422


def test_소수점_셋째자리_금액은_422(client):
    res = client.post(
        "/journal-entries",
        json=entry_body(("1010", "debit", "1.001"), ("3010", "credit", "1.001")),
    )
    assert res.status_code == 422


def test_존재하지_않는_계정의_전표는_422(client):
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


def test_시산표_조회(client):
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


def test_계정별_원장_조회(client):
    _post_samples(client)
    res = client.get("/accounts/1010/ledger")
    assert res.status_code == 200
    body = res.json()
    assert body["account"]["name"] == "현금"
    assert [Decimal(r["balance"]) for r in body["rows"]] == [Decimal("1000"), Decimal("800")]
    assert Decimal(body["ending_balance"]) == Decimal("800")
    assert Decimal(body["debit_total"]) == Decimal("1000")
    assert Decimal(body["credit_total"]) == Decimal("200")


def test_거래없는_계정의_원장은_빈_목록(client):
    body = client.get("/accounts/2010/ledger").json()
    assert body["rows"] == []
    assert Decimal(body["ending_balance"]) == Decimal("0")


def test_없는_계정의_원장은_404(client):
    assert client.get("/accounts/9999/ledger").status_code == 404
