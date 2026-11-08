# 000_sample_project — 클로드 코드 시작용 프로젝트 틀 + 실습 샘플

> 샘플 프로젝트 및 템플릿 공간이다. 두 가지가 들어 있다.
> - **시작용 틀** : 새 프로젝트를 시작할 때 **폴더째 복사해서** 쓰는 틀(`CLAUDE.md`, `.claude/`, `docs/`)
> - **실습 샘플 16개** : 클로드 코드로 실제로 만들고 테스트까지 통과시킨 예제(`001_*`~`016_*`)
>
> 시작용 틀은 클로드 코드를 처음 쓰는 사람(초급)부터 몇 주 써 본 사람(중급), 팀·자동화로 넓혀 쓰려는 사람(고급)까지를 대상으로 했다.
> 무료 공개판(`claude_all-in-one-free`)의 일부이며, 이용 조건은 묶음 맨 위 `LICENSE.txt`를 따른다. 실습 샘플 코드(`001_*`~`016_*`)만 MIT(`LICENSE-MIT`)다.

## 들어 있는 것

```
000_sample_project/
├─ README.md                 ← 지금 읽는 파일
├─ LICENSE-MIT               ← 실습 샘플 코드(001~016)의 라이선스
├─ CLAUDE.md                 ← 클로드가 세션마다 읽는 프로젝트 규칙(예시, 고쳐 쓴다)
├─ .claude/
│  ├─ settings.example.json  ← 권한 설정 예시(비밀 파일 읽기 차단 등)
│  ├─ settings.hooks.example.json ← 훅 예시(고급, docs/08)
│  ├─ hooks/                 ← 훅 스크립트와 자체 시험(bash .claude/hooks/test-hooks.sh)
│  ├─ agents/reviewer.md     ← 서브에이전트 예시 : 읽기 전용 검토자
│  └─ skills/done-check/     ← 스킬 예시 : 「다 했다」고 말하기 전 점검표
├─ scripts/
│  └─ headless-run.sh         ← 사람 없이 돌리는 실행 틀(고급, docs/09). 시험: bash scripts/test-headless-run.sh
├─ docs/
│  ├─ plan.example.md          ← 큰 작업의 계획서 견본(고급, docs/11)
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
└─ 001_hr_payroll/ … 016_always_on_agent_runner/  ← 실습 샘플 16개(아래 「실습 샘플」)
```

## 쓰는 순서

1. 이 폴더를 복사해 이름을 내 프로젝트 이름으로 바꾼다. 실습 샘플 폴더(`001_*`~`016_*`)는 필요한 것만 남기고 지운다.
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
| [003_fullstack_todo](003_fullstack_todo/) | 풀스택 업무 할 일 관리 웹 앱 | TypeScript · Express · esbuild · Vitest | 42개 |
| [004_web_game](004_web_game/) | 오리지널 미니 게임 「야근 탈출」 | TypeScript · Vite · Canvas · Vitest | 35개 |
| [005_inventory_api](005_inventory_api/) | ERP 재고(MM): 입출고, 현재고, 안전재고 미달 조회 | Go 1.24 · net/http · go test | 53개(서브테스트 포함) |
| [006_ai_agent](006_ai_agent/) | Claude 도구 호출 기반 HR·회계 도우미 에이전트 | TypeScript · Anthropic SDK · Vitest | 34개 |
| [007_attendance_cli](007_attendance_cli/) | ERP 인사 근태 집계 CLI(연장·야간·휴일·지각) | Rust · cargo test · clippy | 29개 |
| [008_youtube_analyzer](008_youtube_analyzer/) | 유튜브 영상을 대본·장면 캡처·보고서로 변환해 Claude가 통째로 분석 | Python · yt-dlp · ffmpeg · pytest | 65개 |
| [009_scroll_video_hero](009_scroll_video_hero/) | 영상을 프레임으로 쪼개 스크롤에 맞춰 재생·역재생하는 랜딩 페이지 히어로 | JavaScript · ffmpeg · Canvas · node:test · Playwright | 35개 |
| [010_site_analyzer](010_site_analyzer/) | 웹사이트 구조·기술·디자인 특징을 분석 보고서로 정리(복제 없음, robots.txt 준수) | JavaScript · Playwright · node:test | 66개 |
| [011_ai_webtoon](011_ai_webtoon/) | 대본 JSON 으로 세로 스크롤 웹툰 만들기(코드 그림 기본, 이미지 AI 연결 가능, 말풍선은 코드로, 기획 스킬·콘티 표·영어 프롬프트·연출 여백) | JavaScript · SVG · node:test · Playwright | 85개 |
| [012_hybrid_slm_pipeline](012_hybrid_slm_pipeline/) | 로컬 소형 모델(Ollama)이 댓글·원문을 분류·요약하고 클로드 코드가 블로그 글·시나리오·보고서를 쓰는 2단계 파이프라인(스킬 3종 포함) | Python(표준 라이브러리) · Ollama · Claude Code · unittest | 33개 |
| [013_ai_ebook_builder](013_ai_ebook_builder/) | 대본·기획서·소설 원고를 목차 분할·SVG 표지까지 거쳐 HTML 뷰어·EPUB·인쇄용 HTML·웹북 ZIP 4종으로 묶는 전자책 파이프라인 | Python(표준 라이브러리) · unittest · pytest | 35개 |
| [014_youtube_to_ebook](014_youtube_to_ebook/) | 유튜브 URL 하나로 자막 대본·스틸컷 삽화를 뽑아 삽화가 박힌 HTML 뷰어·EPUB 전자책을 만드는 파이프라인(008+013 결합) | Python · yt-dlp · ffmpeg · unittest · pytest | 48개 |
| [015_sprite_sheet_to_gif](015_sprite_sheet_to_gif/) | 도트 캐릭터 프레임을 코드로 직접 찍거나 챗GPT 스프라이트 시트를 받아 잘라 무한 루프 GIF로 만드는 변환기(클로드 코드 단독 실행형) | Python · Pillow · unittest · pytest | 51개 |
| [016_always_on_agent_runner](016_always_on_agent_runner/) | 사람 없이 돌아가는 비동기 태스크 큐·백그라운드 워커에, 위험 작업 전 사람 승인 토큰을 기다리는 HITL 승인 게이트(레드라인 5종)를 얹은 올웨이즈온 자율 에이전트 러너 | Python(표준 라이브러리) · asyncio · unittest · pytest | 38개 |

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
cd 000_sample_project/011_ai_webtoon      && npm test
cd 000_sample_project/012_hybrid_slm_pipeline && python3 -m unittest discover -s tests -t .
cd 000_sample_project/013_ai_ebook_builder    && python3 -m unittest discover -s tests -t .
cd 000_sample_project/014_youtube_to_ebook    && python3 -m unittest discover -s tests -t .
cd 000_sample_project/015_sprite_sheet_to_gif && python3 -m unittest discover -s tests -t .
cd 000_sample_project/016_always_on_agent_runner && python3 -m unittest discover -s tests -t .
```

한꺼번에 돌리고 위 표의 「테스트」 숫자와 맞춰 보려면(설치는 위 명령으로 먼저 해 둡니다):

```bash
cd 000_sample_project && bash scripts/check-sample-tests.sh            # 16개 전부, 1분 안팎
bash scripts/check-sample-tests.sh 003_fullstack_todo 009_scroll_video_hero   # 일부만
```

예제마다 README 숫자·통과·실패를 보여 주고, 하나라도 실패하거나 숫자가 다르면 종료 코드 1, 도구가 없어 건너뛴 예제가 있으면 2로 끝납니다. 브라우저 시험을 건너뛰면 통과 수가 줄어 「README 와 다름」으로 나옵니다.

### 참고

- 급여·세금·근태 계산 규칙은 교육용으로 단순화한 것이며 실제 법정 기준과 다릅니다.
- `006_ai_agent`를 실제로 실행하려면 `ANTHROPIC_API_KEY` 환경변수가 필요합니다. 키는 커밋하지 마세요.
- `009`, `010`, `011`의 브라우저 테스트는 Playwright가 필요합니다. 없으면 해당 테스트만 건너뜁니다. 설치 방법은 각 README에 있습니다.
- `010_site_analyzer`는 내 사이트나 허락받은 사이트를 공부하는 용도입니다. 콘텐츠·이미지·로고를 복제하지 않습니다.
- 전체 구조도 : [docs/structure.svg](docs/structure.svg)

## 저작권

Copyright (c) 2026 devalive (데브얼라이브, https://devalive.tistory.com)

- 시작용 틀(`CLAUDE.md`, `.claude/`, `docs/`) : 묶음의 [`LICENSE.txt`](../LICENSE.txt)
- 실습 샘플 코드(`001_*`~`016_*`) : [`LICENSE-MIT`](LICENSE-MIT) — 판매하는 결과물을 포함해 자유롭게 사용 가능, 저작권 표시와 MIT 문구만 남긴다
- 급여·세금·근태 계산 등은 교육용으로 단순화한 것이라 실무에 그대로 쓰면 안 된다(보증 없음)
