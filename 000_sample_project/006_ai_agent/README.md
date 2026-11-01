# 006_ai_agent — Claude 도구 호출(tool use) 기반 사내 HR/회계 도우미 에이전트

## 개요

Claude 의 도구 호출(tool use) 기능으로 만든 작은 업무 에이전트 샘플입니다.
사용자가 자연어로 질문하면 Claude 가 필요한 도구를 골라 호출하고, 에이전트가 도구를 실행해 결과를 돌려주면
Claude 가 그 결과를 바탕으로 최종 답변을 작성합니다.

AI 에이전트 FDE(Forward Deployed Engineer) 관점에서 꼭 알아야 할 요소를 최소한의 코드로 보여 줍니다.

- 에이전트 루프 직접 구현: `messages.create` → `stop_reason === 'tool_use'` 이면 도구 실행 → `tool_result` 로 다시 호출
- 최대 반복 횟수 제한(무한 루프 방지)
- 도구 오류를 예외로 끝내지 않고 `is_error: true` 로 모델에 전달 → 모델이 사용자에게 이유를 설명
- 클라이언트 주입으로 실제 API 호출 없이 테스트

### 제공 도구 (데이터는 인메모리 목업)

| 도구 | 설명 |
| --- | --- |
| `get_employee` | 사번 또는 이름으로 사원 정보 조회 |
| `get_leave_balance` | 사원의 총/사용/잔여 연차 조회 |
| `get_expense_policy` | 경비 항목별 1건당 한도·영수증 필요 여부 조회 |
| `submit_expense` | 경비 신청 등록(사원·항목·금액 검증, **정책 한도 초과 시 거절**) |

## 기술 스택

- Node.js 22, TypeScript
- 공식 SDK [`@anthropic-ai/sdk`](https://www.npmjs.com/package/@anthropic-ai/sdk)
- Vitest(테스트), tsx(TypeScript 직접 실행)

## 폴더 구조

```
006_ai_agent/
├── src/
│   ├── agent.ts    # 에이전트 루프(runAgent), 시스템 프롬프트, MaxIterationsError
│   ├── tools.ts    # 도구 정의(JSON Schema)와 도구 로직, executeTool
│   ├── data.ts     # 사원·연차·경비 정책 목업 데이터
│   ├── config.ts   # 환경변수(모델 ID, API 키 유무) 읽기
│   └── cli.ts      # 명령행 진입점
├── tests/
│   ├── agent.test.ts  # 가짜 클라이언트로 에이전트 루프 검증
│   └── tools.test.ts  # 각 도구 로직과 설정 검증
├── .env.example
├── package.json
└── tsconfig.json
```

## 실행 방법

```bash
cd 000_sample_project/006_ai_agent
npm install

# API 키 설정(둘 중 하나)
export ANTHROPIC_API_KEY=발급받은_키
# 또는 cp .env.example .env 후 .env 에 키 입력 (.env 는 Git 에 올라가지 않음)

npm start -- "김민준 님의 잔여 연차를 알려줘"
npm start -- "E001 김민준, 야근 식대 25000원 경비 신청해줘"
npm start -- "박지호 님 택시비 80000원 신청 가능해?"
```

- 모델 ID 는 `ANTHROPIC_MODEL` 환경변수로 바꿀 수 있으며 기본값은 `claude-opus-5-5` 입니다.
- `ANTHROPIC_API_KEY` 가 없으면 안내 메시지를 출력하고 종료합니다.
- API 키는 절대 코드나 커밋되는 파일에 쓰지 마세요.

출력 예시(실제 문구는 모델 응답에 따라 다름):

```
[모델] claude-opus-5-5
[질문] 박지호 님 택시비 80000원 신청 가능해?

[도구 성공] get_employee {"name":"박지호"}
[도구 실패] submit_expense {"employee_id":"E003","category":"taxi","amount":80000,"description":"택시비"}

[답변]
택시비 1건당 한도는 50,000원이라 80,000원은 신청할 수 없습니다. ...
```

## 테스트 방법

```bash
npm test          # Vitest (실제 API 호출 없음)
npx tsc --noEmit  # 타입체크
```

`agent.test.ts` 는 `messages.create` 를 `vi.fn()` 으로 만든 가짜 클라이언트를 주입해 다음을 검증합니다.

- 도구 호출 → `tool_result` 전달 → 최종 답변
- 한 응답에 여러 도구 호출이 있을 때 모두 실행
- 도구 오류·알 수 없는 도구·실행기 예외를 `is_error: true` 로 전달
- 최대 반복 횟수 초과 시 `MaxIterationsError`

`tools.test.ts` 는 조회 로직, 경비 한도 검증(경계값 포함), 입력값 검증, 설정 읽기를 검증합니다.

## 동작 흐름

```
사용자 질문
   │
   ▼
messages = [user: 질문]
   │
   ▼  (반복, 최대 maxIterations 회)
client.messages.create({ model, system, tools, messages })
   │
   ├─ stop_reason === 'max_tokens' / 'refusal' ──▶ IncompleteAnswerError (끊긴·빈 답변을 답으로 쓰지 않음)
   │
   ├─ stop_reason !== 'tool_use' ──▶ text 블록을 모아 최종 답변 반환
   │
   └─ stop_reason === 'tool_use'
        1. assistant 응답(tool_use 블록 포함)을 messages 에 추가
        2. 각 tool_use 블록의 도구 실행
             - 성공: { type: 'tool_result', tool_use_id, content: JSON }
             - 실패: { ..., content: '오류: 이유', is_error: true }
        3. tool_result 들을 하나의 user 메시지로 messages 에 추가
        4. 다시 호출
   │
   ▼
반복 횟수를 넘기면 MaxIterationsError
```

핵심 코드는 `src/agent.ts` 의 `runAgent` 한 함수에 모여 있습니다.
`MessagesClient` 인터페이스(필요한 `messages.create` 만 정의)에 의존하기 때문에 실제 `Anthropic` 클라이언트와 테스트용 가짜 클라이언트를 똑같이 주입할 수 있습니다.

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
