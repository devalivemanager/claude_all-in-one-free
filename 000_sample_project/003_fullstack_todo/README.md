# 003_fullstack_todo — 풀스택 업무 할 일 관리 웹 앱

팀 업무 할 일을 등록·수정·삭제하고, 상태와 담당자로 걸러 보며, 마감이 지난 항목을 한눈에 확인하는 작은 풀스택 웹 앱입니다.
백엔드는 Express REST API이고, 프론트엔드는 프레임워크 없이 TypeScript와 HTML/CSS로 만들었습니다. 데이터는 외부 DB 없이 메모리에 저장되므로 **서버를 재시작하면 초기화**됩니다.

## 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| 런타임 | Node.js 22 |
| 언어 | TypeScript |
| 백엔드 | Express 5 (REST API + 정적 파일 서빙) |
| 프론트엔드 | 순수 TypeScript + HTML/CSS (esbuild 로 번들) |
| 테스트 | Vitest, supertest |
| 개발 도구 | tsx (개발 서버 자동 재시작) |

## 폴더 구조

```
003_fullstack_todo/
├── public/                # 정적 파일 (HTML, CSS)
│   ├── index.html
│   └── styles.css
├── src/
│   ├── server/
│   │   ├── types.ts       # 서버·클라이언트 공용 타입
│   │   ├── errors.ts      # ValidationError(400), NotFoundError(404)
│   │   ├── todoService.ts # 비즈니스 로직 + 입력 검증 + 인메모리 저장소
│   │   ├── app.ts         # Express 앱 (라우트, 정적 파일, 에러 처리)
│   │   └── index.ts       # 서버 진입점 (샘플 데이터 등록 후 실행)
│   └── client/
│       └── main.ts        # 화면 로직 (fetch 로 API 호출, DOM 렌더링)
├── tests/
│   ├── todoService.test.ts # 서비스 단위 테스트
│   └── api.test.ts         # API 테스트 (supertest)
├── tsconfig.json          # 서버 빌드 설정 → dist/server
├── tsconfig.client.json   # 클라이언트 타입 검사 설정
├── vitest.config.ts
└── package.json
```

빌드하면 `dist/server/`(서버 JS)와 `dist/public/app.js`(프론트 번들)가 만들어집니다. Express는 `public/`과 `dist/public/`을 함께 정적 파일로 제공합니다.

## 실행 방법

```bash
cd 000_sample_project/003_fullstack_todo
npm install

# 개발 모드: 프론트를 빌드한 뒤 서버를 tsx watch 로 실행 (서버 코드 변경 시 자동 재시작)
npm run dev

# 운영 모드: 전체 빌드 후 실행
npm run build
npm start
```

브라우저에서 <http://localhost:3000> 을 엽니다. 포트는 `PORT` 환경 변수로 바꿀 수 있습니다 (예: `PORT=4000 npm start`).
서버를 시작하면 화면 확인용 샘플 할 일 4건이 등록됩니다 (그중 1건은 마감 지남).

> 개발 모드에서 프론트 코드(`src/client/main.ts`)를 바꿨다면 `npm run build:client` 를 다시 실행하고 새로고침하세요.

## 테스트 방법

```bash
npm test
```

- `tests/todoService.test.ts`: 생성 기본값, 입력 검증, 정렬, 마감 지남 판정, 상태·담당자 필터, 수정·삭제를 검사합니다.
- `tests/api.test.ts`: supertest로 실제 HTTP 요청을 보내 상태 코드(200/201/204/400/404)와 응답 본문을 검사합니다.
- 테스트에서는 `TodoService` 에 "오늘" 날짜를 주입(2026-10-31 고정)해서 마감 지남 판정이 실행 날짜에 따라 달라지지 않게 합니다.

## 기능

- 할 일 추가 / 수정 / 삭제, 체크박스로 완료 처리
- 항목: 제목, 담당자, 우선순위(높음·보통·낮음), 마감일, 완료 여부
- 상태 필터(전체·진행 중·완료·마감 지남), 담당자 필터
- 마감일이 오늘보다 이전인 미완료 항목은 빨간 배경과 "마감 지남" 배지로 표시
- 정렬: 미완료 → 마감일 빠른 순(마감일 없으면 뒤) → 우선순위 높은 순
- 입력 오류 시 서버가 돌려준 상세 오류 메시지를 화면에 표시

## API 목록

| 메서드 | 경로 | 설명 | 성공 응답 |
| --- | --- | --- | --- |
| GET | `/api/todos` | 목록 조회. 쿼리 `status`(`all`/`active`/`completed`/`overdue`), `assignee` 로 필터 | 200 |
| GET | `/api/todos/:id` | 단건 조회 | 200 |
| POST | `/api/todos` | 생성 | 201 |
| PATCH | `/api/todos/:id` | 일부 필드 수정 | 200 |
| DELETE | `/api/todos/:id` | 삭제 | 204 |
| GET | `/api/assignees` | 등록된 담당자 목록 (중복 제거) | 200 |

### 요청 본문 (POST / PATCH)

```json
{
  "title": "주간 보고서 작성",
  "assignee": "김민수",
  "priority": "high",
  "dueDate": "2026-11-03",
  "completed": false
}
```

| 필드 | 규칙 |
| --- | --- |
| `title` | 필수(POST), 공백 제외 1~100자 |
| `assignee` | 필수(POST), 공백 제외 1~30자 |
| `priority` | `high` / `medium` / `low`, 생략 시 `medium` |
| `dueDate` | `YYYY-MM-DD` 형식의 실제 날짜, `null` 이면 마감일 없음 |
| `completed` | `true` / `false`, 생략 시 `false` |

응답의 각 할 일에는 서버가 계산한 `overdue`(마감 지남 여부)가 함께 들어 있습니다.

### 에러 응답

```json
{ "error": "입력값이 올바르지 않습니다.", "details": ["title(제목)은 비어 있지 않은 문자열이어야 합니다."] }
```

- `400`: 입력 검증 실패, 잘못된 JSON, 숫자가 아닌 id, 알 수 없는 `status` 값, 빈 PATCH 요청
- `404`: 존재하지 않는 할 일 id, 정의되지 않은 API 경로

### curl 예시

```bash
curl -X POST http://localhost:3000/api/todos \
  -H 'Content-Type: application/json' \
  -d '{"title":"회의록 정리","assignee":"이지은","priority":"medium","dueDate":"2026-11-05"}'

curl 'http://localhost:3000/api/todos?status=overdue'
curl -X PATCH http://localhost:3000/api/todos/1 -H 'Content-Type: application/json' -d '{"completed":true}'
curl -X DELETE http://localhost:3000/api/todos/1
```

---

Copyright (c) 2026 devalivemanager · [MIT 라이선스](../../LICENSE)
