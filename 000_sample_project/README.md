# 000_sample_project — 클로드 코드 시작용 프로젝트 틀 + 실습 샘플

> 샘플 프로젝트 및 템플릿 공간이다. 두 가지가 들어 있다.
> - **시작용 틀** : 새 프로젝트를 시작할 때 **폴더째 복사해서** 쓰는 틀(`CLAUDE.md`, `.claude/`, `docs/`)
> - **실습 샘플 10개** : 클로드 코드로 실제로 만들고 테스트까지 통과시킨 예제(`001_*`~`010_*`)
>
> 시작용 틀은 클로드 코드를 처음 쓰는 사람(초급)부터 몇 주 써 본 사람(중급), 팀·자동화로 넓혀 쓰려는 사람(고급)까지를 대상으로 했다.
> 무료 공개판(`claude_all-in-one-free`)의 일부이며, 이용 조건은 묶음 맨 위 `LICENSE.txt`를 따른다. 실습 샘플 코드(`001_*`~`010_*`)만 MIT(`LICENSE-MIT`)다.

## 들어 있는 것

```
000_sample_project/
├─ README.md                 ← 지금 읽는 파일
├─ LICENSE-MIT               ← 실습 샘플 코드(001~010)의 라이선스
├─ CLAUDE.md                 ← 클로드가 세션마다 읽는 프로젝트 규칙(예시, 고쳐 쓴다)
├─ .claude/
│  ├─ settings.example.json  ← 권한 설정 예시(비밀 파일 읽기 차단 등)
│  ├─ settings.hooks.example.json ← 훅 예시(고급, docs/08)
│  ├─ agents/reviewer.md     ← 서브에이전트 예시 : 읽기 전용 검토자
│  └─ skills/done-check/     ← 스킬 예시 : 「다 했다」고 말하기 전 점검표
├─ docs/
│  ├─ 01_초급_첫세션.md           ← 설치 뒤 첫 세션, 꼭 알아야 할 명령
│  ├─ 02_초급_지시잘하기.md        ← 결과가 달라지는 지시 습관
│  ├─ 03_초급_CLAUDE.md쓰는법.md   ← 규칙 파일을 짧고 쓸모 있게
│  ├─ 04_중급_스킬·서브에이전트·MCP.md
│  ├─ 05_중급_검증과완료기준.md
│  ├─ 06_중급_토큰과비용.md
│  ├─ 07_중급_세션여러개쓸때.md
│  ├─ 08_고급_훅과권한설계.md
│  ├─ 09_고급_헤드리스와자동화.md
│  ├─ 10_고급_에이전트팀과병렬작업.md
│  ├─ 11_고급_대형작업설계와운영.md
│  └─ structure.svg              ← 묶음 전체 구조도
└─ 001_hr_payroll/ … 010_site_analyzer/   ← 실습 샘플 10개(아래 「실습 샘플」)
```

## 쓰는 순서

1. 이 폴더를 복사해 이름을 내 프로젝트 이름으로 바꾼다. 실습 샘플 폴더(`001_*`~`010_*`)는 필요한 것만 남기고 지운다.
2. `CLAUDE.md`의 `[채운다]` 칸을 내 프로젝트 값으로 채운다. 쓸 일이 없는 줄은 지운다.
3. `.claude/settings.example.json`을 읽어 보고, 마음에 들면 `.claude/settings.json`으로 이름을 바꾼다.
4. 그 폴더에서 `claude`를 실행한다. 첫 세션에서 할 일은 `docs/01_초급_첫세션.md`에 있다.
5. 예시 에이전트·스킬은 동작을 확인하는 용도다. 필요 없으면 지운다.

## 수준별로 읽을 문서

| 수준 | 문서 | 이것을 읽고 나면 |
|---|---|---|
| 초급 | `docs/01`~`03` | 세션을 열고, 일을 시키고, 규칙 파일을 쓸 수 있다 |
| 중급 | `docs/04`~`07` | 반복 작업을 스킬로 묶고, 결과를 검증하고, 비용을 관리하고, 세션을 여러 개 써도 꼬이지 않는다 |
| 고급 | `docs/08`~`11` | 규칙을 훅·권한으로 강제하고, 사람 없이 돌게 자동화하고, 에이전트 여러 개에 일을 나누고, 며칠짜리 큰일을 쪼개 굴린다 |

더 깊은 자료는 묶음의 `999_document/README.md` 색인과 `999_agent-kit/skills/`에 있다.

## 미리 알아 둘 것

- 클로드 코드는 계속 바뀐다. 명령 이름이나 메뉴가 문서와 다르면 공식 문서(https://code.claude.com/docs)가 맞다.
- 이 틀은 「이렇게 하면 덜 헤맨다」는 예시다. 정답이 아니니 내 일에 맞게 줄이거나 고친다.

## 실습 샘플

클로드 코드 클라우드 세션으로 만든 동작하는 예제다. 모두 외부 DB 없이 돌아가고, 폴더마다 README에 실행·테스트 방법이 있다.

| 폴더 | 주제 | 기술 스택 | 테스트 |
|---|---|---|---|
| [001_hr_payroll](001_hr_payroll/) | ERP 인사(HR): 부서·사원 관리, 월 급여 계산(4대보험·소득세) | Java 21 · Spring Boot 3 · Maven · JUnit 5 | 48개 |
| [002_fi_ledger](002_fi_ledger/) | ERP 회계(FI): 계정과목, 분개 전표, 시산표, 계정별 원장 | Python 3.13 · FastAPI · pytest | 35개 |
| [003_fullstack_todo](003_fullstack_todo/) | 풀스택 업무 할 일 관리 웹 앱 | TypeScript · Express · esbuild · Vitest | 35개 |
| [004_web_game](004_web_game/) | 오리지널 미니 게임 「야근 탈출」 | TypeScript · Vite · Canvas · Vitest | 27개 |
| [005_inventory_api](005_inventory_api/) | ERP 재고(MM): 입출고, 현재고, 안전재고 미달 조회 | Go 1.24 · net/http · go test | 53개(서브테스트 포함) |
| [006_ai_agent](006_ai_agent/) | Claude 도구 호출 기반 HR·회계 도우미 에이전트 | TypeScript · Anthropic SDK · Vitest | 31개 |
| [007_attendance_cli](007_attendance_cli/) | ERP 인사 근태 집계 CLI(연장·야간·휴일·지각) | Rust · cargo test · clippy | 27개 |
| [008_youtube_analyzer](008_youtube_analyzer/) | 유튜브 영상을 대본·장면 캡처·보고서로 변환해 Claude가 통째로 분석 | Python · yt-dlp · ffmpeg · pytest | 65개 |
| [009_scroll_video_hero](009_scroll_video_hero/) | 영상을 프레임으로 쪼개 스크롤에 맞춰 재생·역재생하는 랜딩 페이지 히어로 | JavaScript · ffmpeg · Canvas · node:test · Playwright | 31개 |
| [010_site_analyzer](010_site_analyzer/) | 웹사이트 구조·기술·디자인 특징을 분석 보고서로 정리(복제 없음, robots.txt 준수) | JavaScript · Playwright · node:test | 61개 |

### 테스트 실행

```bash
cd 000_sample_project/001_hr_payroll     && mvn test
cd 000_sample_project/002_fi_ledger      && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest -q
cd 000_sample_project/003_fullstack_todo && npm ci && npm test
cd 000_sample_project/004_web_game       && npm ci && npm test
cd 000_sample_project/005_inventory_api  && go test ./...
cd 000_sample_project/006_ai_agent       && npm ci && npm test
cd 000_sample_project/007_attendance_cli && cargo test
cd 000_sample_project/008_youtube_analyzer && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest -q
cd 000_sample_project/009_scroll_video_hero && npm test
cd 000_sample_project/010_site_analyzer   && npm test
```

### 참고

- 급여·세금·근태 계산 규칙은 교육용으로 단순화한 것이며 실제 법정 기준과 다릅니다.
- `006_ai_agent`를 실제로 실행하려면 `ANTHROPIC_API_KEY` 환경변수가 필요합니다. 키는 커밋하지 마세요.
- `009`, `010`의 브라우저 테스트는 Playwright가 필요합니다. 없으면 해당 테스트만 건너뜁니다. 설치 방법은 각 README에 있습니다.
- `010_site_analyzer`는 내 사이트나 허락받은 사이트를 공부하는 용도입니다. 콘텐츠·이미지·로고를 복제하지 않습니다.
- 전체 구조도 : [docs/structure.svg](docs/structure.svg)

## 저작권

Copyright (c) 2026 devalive (데브얼라이브, https://devalive.tistory.com)

- 시작용 틀(`CLAUDE.md`, `.claude/`, `docs/`) : 묶음의 [`LICENSE.txt`](../LICENSE.txt)
- 실습 샘플 코드(`001_*`~`010_*`) : [`LICENSE-MIT`](LICENSE-MIT) — 판매하는 결과물을 포함해 자유롭게 사용 가능, 저작권 표시와 MIT 문구만 남긴다
- 급여·세금·근태 계산 등은 교육용으로 단순화한 것이라 실무에 그대로 쓰면 안 된다(보증 없음)
