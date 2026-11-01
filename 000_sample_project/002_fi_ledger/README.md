# 002_fi_ledger — ERP 회계(FI) 총계정원장 API

## 개요

ERP 재무회계(FI) 모듈의 핵심인 **총계정원장(General Ledger)** 을 아주 작게 구현한 교육용 샘플이다.
계정과목을 등록하고, 복식부기 분개 전표를 기표한 뒤 시산표와 계정별 원장을 조회할 수 있다.
데이터는 외부 DB 없이 메모리에만 저장되므로 서버를 재시작하면 초기화된다.

핵심 회계 규칙:

- 전표 라인은 **최소 2개**이고, 각 라인은 차변(`debit`) 또는 대변(`credit`) 중 하나다.
- 금액은 **양수**여야 하며 소수점 둘째 자리까지 허용한다.
- **차변 합계 = 대변 합계**가 아니면 전표를 거부한다(422).
- **존재하지 않는 계정**이 포함된 전표는 거부한다(422).
- 금액은 float 오차를 피하기 위해 **`Decimal`** 로 계산한다. JSON 응답에서는 정밀도 보존을 위해 문자열(예: `"1000.50"`)로 내려간다.
- 잔액은 계정 유형별 **정상잔액 방향** 기준으로 계산한다.

| 유형 | 값 | 정상잔액 방향 |
| --- | --- | --- |
| 자산 | `asset` | 차변 |
| 비용 | `expense` | 차변 |
| 부채 | `liability` | 대변 |
| 자본 | `equity` | 대변 |
| 수익 | `revenue` | 대변 |

예를 들어 매출(수익) 계정에 대변 300이 기록되면 잔액은 `+300` 이다. 잔액이 음수이면 정상 방향과 반대쪽 잔액이 남아 있다는 뜻이다.

기본 시드 계정과목:

| 코드 | 이름 | 유형 |
| --- | --- | --- |
| 1010 | 현금 | 자산 |
| 1100 | 매출채권 | 자산 |
| 2010 | 매입채무 | 부채 |
| 3010 | 자본금 | 자본 |
| 4010 | 매출 | 수익 |
| 5010 | 급여 | 비용 |
| 5020 | 임차료 | 비용 |

## 기술 스택

- Python 3.13
- FastAPI, Pydantic v2
- pytest, httpx(FastAPI `TestClient`)
- uvicorn(로컬 실행용)

## 폴더 구조

```
002_fi_ledger/
├── app/
│   ├── domain.py    # 순수 도메인 로직(계정, 전표, 시산표, 원장, 검증 규칙)
│   ├── schemas.py   # Pydantic 요청/응답 스키마
│   └── main.py      # FastAPI 앱과 라우트
├── tests/
│   ├── test_domain.py  # 도메인 단위 테스트
│   └── test_api.py     # API 테스트(TestClient)
├── pytest.ini
├── requirements.txt
└── README.md
```

## 실행 방법

```bash
cd 000_sample_project/002_fi_ledger
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

브라우저에서 <http://127.0.0.1:8000/docs> 를 열면 Swagger UI 로 API 를 시험해 볼 수 있다.

요청 예시:

```bash
# 자본금 1,000,000원 현금 납입
curl -X POST localhost:8000/journal-entries -H 'Content-Type: application/json' -d '{
  "entry_date": "2026-01-01",
  "description": "자본금 납입",
  "lines": [
    {"account_code": "1010", "side": "debit",  "amount": "1000000"},
    {"account_code": "3010", "side": "credit", "amount": "1000000"}
  ]
}'

curl localhost:8000/trial-balance
curl localhost:8000/accounts/1010/ledger
```

## 테스트 방법

```bash
cd 000_sample_project/002_fi_ledger
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt && .venv/bin/pytest -q
```

## API 목록

| 메서드 | 경로 | 설명 | 주요 응답 코드 |
| --- | --- | --- | --- |
| `POST` | `/accounts` | 계정과목 등록 | 201, 409(코드 중복), 422(입력 오류) |
| `GET` | `/accounts` | 계정과목 목록(코드순) | 200 |
| `GET` | `/accounts/{code}` | 계정과목 단건 조회 | 200, 404 |
| `POST` | `/journal-entries` | 분개 전표 등록 | 201, 422(차대 불일치·라인 부족·금액 오류·없는 계정) |
| `GET` | `/journal-entries` | 전표 목록 | 200 |
| `GET` | `/journal-entries/{id}` | 전표 단건 조회 | 200, 404 |
| `GET` | `/trial-balance` | 시산표(계정별 차변·대변 합계와 잔액, 전체 합계, 균형 여부) | 200 |
| `GET` | `/accounts/{code}/ledger` | 계정별 원장(일자순 거래 내역과 누적 잔액) | 200, 404 |

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
