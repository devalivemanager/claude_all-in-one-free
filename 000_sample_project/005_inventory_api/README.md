# 005_inventory_api — ERP 재고(MM) 관리 REST API

## 개요

ERP 자재관리(MM) 모듈의 핵심인 **재고 관리**를 단순화한 교육용 REST API 샘플입니다.

- 품목(품번, 품명, 단위, 안전재고) 등록·조회·수정·삭제(CRUD)
- 입고(`IN`) / 출고(`OUT`) 트랜잭션 등록
- 현재고 조회
- 품목별 재고 이동 이력 조회
- 안전재고 미달 품목 조회

### 업무 규칙

| 규칙 | 응답 |
| --- | --- |
| 출고 수량이 현재고보다 크면 거부 (재고는 바뀌지 않음) | `409 Conflict` |
| 수량은 양수여야 함 (0, 음수 거부) | `400 Bad Request` |
| 없는 품목 | `404 Not Found` |
| 품번 중복 등록 | `409 Conflict` |
| 품번·품명·단위 누락, 안전재고 음수, 잘못된 JSON | `400 Bad Request` |

- 현재고는 품목 수정으로 바꿀 수 없고 **입출고 트랜잭션으로만** 변경됩니다.
- "안전재고 미달"은 `현재고 < 안전재고` 인 경우입니다 (같으면 정상).
- 품목을 삭제하면 해당 품목의 이동 이력도 함께 삭제됩니다.
- 데이터는 인메모리에 저장되며 서버를 재시작하면 사라집니다. `sync.Mutex` 로 보호되어 동시 요청에도 안전합니다.

## 기술 스택

- Go 1.24
- 표준 라이브러리 `net/http` (Go 1.22+ 라우팅 패턴 `"GET /items/{code}"`, `r.PathValue`)
- 테스트: `testing`, `net/http/httptest`
- 외부 의존성 없음

## 폴더 구조

```
005_inventory_api/
├── go.mod                       # module example.com/inventory
├── main.go                      # 서버 진입점 (기본 :8080, ADDR 환경변수로 변경)
├── internal/inventory/
│   ├── model.go                 # 도메인 타입과 오류 정의
│   ├── service.go               # 인메모리 저장소 + 업무 규칙 (sync.Mutex)
│   ├── handler.go               # HTTP 라우팅, JSON 입출력, 오류→상태 코드 변환
│   ├── service_test.go          # 서비스 단위 테스트 (테이블 기반, 동시성 테스트 포함)
│   └── handler_test.go          # 핸들러 테스트 (httptest)
├── .gitignore
└── README.md
```

## 실행 방법

```bash
cd 000_sample_project/005_inventory_api
go run .                  # http://localhost:8080
ADDR=:9090 go run .       # 포트 변경
```

### 사용 예시

```bash
# 품목 등록
curl -X POST localhost:8080/items \
  -d '{"code":"P-001","name":"볼트","unit":"EA","safetyStock":10}'

# 입고 30
curl -X POST localhost:8080/items/P-001/movements \
  -d '{"type":"IN","quantity":30,"note":"구매입고"}'

# 출고 25
curl -X POST localhost:8080/items/P-001/movements \
  -d '{"type":"OUT","quantity":25,"note":"생산출고"}'

# 현재고 조회 → {"code":"P-001","stock":5,"unit":"EA","safetyStock":10,"belowSafety":true}
curl localhost:8080/items/P-001/stock

# 초과 출고 → 409
curl -i -X POST localhost:8080/items/P-001/movements -d '{"type":"OUT","quantity":100}'

# 이력 / 안전재고 미달 품목
curl localhost:8080/items/P-001/movements
curl localhost:8080/reports/below-safety-stock
```

## 테스트 방법

```bash
cd 000_sample_project/005_inventory_api
go vet ./... && go test ./...
go test -race -v ./...    # 레이스 검출 + 상세 출력
```

## API 목록

| 메서드 | 경로 | 설명 | 성공 응답 |
| --- | --- | --- | --- |
| `POST` | `/items` | 품목 등록 (`code`, `name`, `unit`, `safetyStock`) | `201` 품목 |
| `GET` | `/items` | 품목 목록 (품번 순) | `200` 품목 배열 |
| `GET` | `/items/{code}` | 품목 단건 조회 | `200` 품목 |
| `PUT` | `/items/{code}` | 품목 수정 (`name`, `unit`, `safetyStock`) | `200` 품목 |
| `DELETE` | `/items/{code}` | 품목 삭제 (이력 포함) | `204` |
| `POST` | `/items/{code}/movements` | 입출고 등록 (`type`: `IN`/`OUT`, `quantity`, `note`) | `201` 이동 기록 |
| `GET` | `/items/{code}/movements` | 재고 이동 이력 (등록 순) | `200` 이동 기록 배열 |
| `GET` | `/items/{code}/stock` | 현재고 조회 (`belowSafety` 포함) | `200` |
| `GET` | `/reports/below-safety-stock` | 안전재고 미달 품목 (품번 순) | `200` 품목 배열 |

오류 응답 형식: `{"error": "메시지"}`

### 데이터 형식

```json
// 품목
{"code":"P-001","name":"볼트","unit":"EA","safetyStock":10,"stock":5}

// 이동 기록
{"id":2,"itemCode":"P-001","type":"OUT","quantity":25,"balanceAfter":5,"note":"생산출고","createdAt":"2026-01-01T09:00:00Z"}
```

---

Copyright (c) 2026 devalivemanager · [MIT 라이선스](../../LICENSE)
