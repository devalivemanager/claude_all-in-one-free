# 001_hr_payroll — ERP 인사(HR) 급여 계산 API

부서·사원을 관리하고, 사원의 월 급여(4대 보험·소득세 공제 후 실수령액)를 계산하는 교육용 REST API 샘플입니다.
외부 DB 없이 인메모리 저장소(`ConcurrentHashMap`)를 사용하므로 애플리케이션을 재시작하면 데이터가 초기화됩니다.

> **주의**: 소득세는 실제 국세청 근로소득 간이세액표가 아닌 **교육용 단순화** 누진세율입니다.
> 4대 보험의 기준소득월액 상·하한, 부양가족 공제 등도 반영하지 않았습니다. 실무 급여 계산에 사용하지 마세요.

## 기술 스택

- Java 21
- Spring Boot 3.4 (Web, Validation)
- Maven (시스템에 설치된 `mvn` 사용, mvnw 없음)
- JUnit 5, AssertJ, MockMvc
- 금액 계산: `BigDecimal`

## 폴더 구조

```
001_hr_payroll
├── pom.xml
├── src/main/java/com/example/hr
│   ├── HrPayrollApplication.java      # 진입점
│   ├── config/PayrollRates.java       # 급여 요율·한도·누진세 구간 상수 (한 곳에 모음)
│   ├── domain/                        # Department, Employee (record)
│   ├── dto/                           # 요청/응답 DTO (@Valid 검증 어노테이션 포함)
│   ├── repository/                    # 인메모리 저장소
│   ├── service/
│   │   ├── PayrollCalculator.java     # 순수 급여 계산 로직
│   │   ├── PayrollService.java        # 사원 조회 + 계산 조합
│   │   ├── DepartmentService.java
│   │   └── EmployeeService.java
│   ├── controller/                    # REST 컨트롤러
│   └── exception/                     # ApiException, ErrorResponse, GlobalExceptionHandler
└── src/test/java/com/example/hr
    ├── service/PayrollCalculatorTest.java   # 급여 계산 단위 테스트(경계값 포함)
    └── controller/                          # MockMvc 테스트 (부서/사원/급여)
```

## 실행 방법

```bash
cd 000_sample_project/001_hr_payroll
mvn spring-boot:run
# 또는
mvn package -DskipTests && java -jar target/hr-payroll-0.0.1-SNAPSHOT.jar
```

기본 포트는 `8080` 입니다.

## 테스트 방법

```bash
cd 000_sample_project/001_hr_payroll
mvn -q test
```

- `PayrollCalculatorTest`: 표준 케이스, 원 단위 절사, 식대 비과세 한도 경계(199,999 / 200,000 / 200,001원), 누진세 구간 경계 등
- `DepartmentControllerTest`, `EmployeeControllerTest`, `PayrollControllerTest`: CRUD, 검증 실패(400), 없는 리소스(404), 충돌(409)

## 급여 계산 규칙

모든 요율은 `config/PayrollRates.java` 에 모여 있습니다.

| 항목 | 계산식 |
|---|---|
| 지급 총액 | 기본급 + 식대 + 기타 수당 |
| 비과세액 | min(식대, 200,000원) |
| 과세 대상액 | 지급 총액 − 비과세액 |
| 국민연금 | 과세 대상액 × 4.5% |
| 건강보험 | 과세 대상액 × 3.545% |
| 장기요양보험 | 건강보험료 × 12.95% |
| 고용보험 | 과세 대상액 × 0.9% |
| 소득세 | 과세 대상액에 아래 교육용 누진세율 적용 |
| 지방소득세 | 소득세 × 10% |
| 실수령액 | 지급 총액 − 공제 합계 |

각 공제 항목은 계산 직후 **원 단위 미만을 절사**합니다.

### 교육용 간이 누진세율 (실제 간이세액표가 아닌 교육용 단순화)

월 과세 대상액 중 각 구간에 해당하는 금액에만 그 구간 세율을 적용해 합산합니다.

| 월 과세 대상액 구간 | 세율 |
|---|---|
| 1,060,000원 이하 | 0% |
| 1,060,000원 초과 ~ 3,000,000원 이하 | 2% |
| 3,000,000원 초과 ~ 5,000,000원 이하 | 4% |
| 5,000,000원 초과 ~ 10,000,000원 이하 | 8% |
| 10,000,000원 초과 | 15% |

### 계산 예시 (기본급 3,000,000원 + 식대 200,000원)

| 항목 | 금액 |
|---|---:|
| 지급 총액 | 3,200,000 |
| 과세 대상액 | 3,000,000 |
| 국민연금 | 135,000 |
| 건강보험 | 106,350 |
| 장기요양보험 | 13,772 |
| 고용보험 | 27,000 |
| 소득세 | 38,800 |
| 지방소득세 | 3,880 |
| 공제 합계 | 324,802 |
| **실수령액** | **2,875,198** |

## API 목록

### 부서

| 메서드 | 경로 | 설명 | 성공 코드 |
|---|---|---|---|
| POST | `/api/departments` | 부서 등록 `{"name":"인사팀"}` | 201 |
| GET | `/api/departments` | 부서 목록 | 200 |
| GET | `/api/departments/{id}` | 부서 단건 조회 | 200 |
| PUT | `/api/departments/{id}` | 부서명 수정 | 200 |
| DELETE | `/api/departments/{id}` | 부서 삭제 (소속 사원이 있으면 409) | 204 |

### 사원

| 메서드 | 경로 | 설명 | 성공 코드 |
|---|---|---|---|
| POST | `/api/employees` | 사원 등록 | 201 |
| GET | `/api/employees` | 사원 목록 | 200 |
| GET | `/api/employees/{employeeNo}` | 사원 단건 조회 | 200 |
| PUT | `/api/employees/{employeeNo}` | 사원 수정 (본문에 사번 제외) | 200 |
| DELETE | `/api/employees/{employeeNo}` | 사원 삭제 | 204 |

사원 등록 요청 예시:

```json
{
  "employeeNo": "E0001",
  "name": "홍길동",
  "departmentId": 1,
  "basePay": 3000000,
  "hireDate": "2024-03-01"
}
```

검증 규칙: 사번은 `E` + 숫자 4자리, 이름 필수(30자 이하), 부서 ID 필수(존재해야 함), 기본급은 0 이상의 원 단위 정수, 입사일은 오늘 이전.

### 급여 계산

| 메서드 | 경로 | 설명 | 성공 코드 |
|---|---|---|---|
| POST | `/api/payrolls/calculate` | 월 급여 계산 (결과는 저장하지 않음) | 200 |

```bash
curl -X POST localhost:8080/api/payrolls/calculate \
  -H 'Content-Type: application/json' \
  -d '{"employeeNo":"E0001","payMonth":"2026-10","mealAllowance":200000,"otherAllowance":0}'
```

- `payMonth` (필수, `yyyy-MM`): 입사월 이전이면 400
- `mealAllowance`, `otherAllowance` (선택, 0 이상 정수): 생략 시 0

응답 예시:

```json
{
  "employeeNo": "E0001",
  "employeeName": "홍길동",
  "departmentName": "인사팀",
  "payMonth": "2026-10",
  "payroll": {
    "basePay": 3000000, "mealAllowance": 200000, "otherAllowance": 0,
    "grossPay": 3200000, "nonTaxableAmount": 200000, "taxableAmount": 3000000,
    "nationalPension": 135000, "healthInsurance": 106350, "longTermCareInsurance": 13772,
    "employmentInsurance": 27000, "incomeTax": 38800, "localIncomeTax": 3880,
    "totalDeduction": 324802, "netPay": 2875198
  }
}
```

## 에러 응답 형식

모든 에러는 같은 형식으로 응답합니다.

```json
{
  "status": 400,
  "code": "VALIDATION_FAILED",
  "message": "입력값 검증에 실패했습니다.",
  "errors": [{ "field": "basePay", "message": "기본급은 0 이상이어야 합니다." }]
}
```

| code | HTTP | 상황 |
|---|---|---|
| `VALIDATION_FAILED` | 400 | `@Valid` 검증 실패 (필드별 오류 포함) |
| `MALFORMED_REQUEST` | 400 | JSON 문법·날짜 형식 오류 |
| `TYPE_MISMATCH` | 400 | 경로 변수 타입 오류 (예: `/api/departments/abc`) |
| `BAD_REQUEST` | 400 | 입사월 이전 급여 계산 요청 |
| `NOT_FOUND` | 404 | 부서·사원 없음 |
| `CONFLICT` | 409 | 사번 중복, 사원이 있는 부서 삭제 |

---

Copyright (c) 2026 devalivemanager · [MIT 라이선스](../../LICENSE)
