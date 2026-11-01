# 000_sample_project — 샘플 프로젝트 모음

ERP(인사·회계·재고·근태), 풀스택 웹, 게임, AI 에이전트, 유튜브 분석 도구를 여러 언어로 구현한 교육용 샘플 모음입니다.
모든 샘플은 외부 DB 없이 인메모리로 동작하고, 각 폴더의 README에 실행·테스트 방법이 있습니다.

## 샘플 목록

| 폴더 | 주제 | 기술 스택 | 테스트 |
|---|---|---|---|
| [001_hr_payroll](001_hr_payroll/) | ERP 인사(HR): 부서·사원 관리, 월 급여 계산(4대보험·소득세) | Java 21 · Spring Boot 3 · Maven · JUnit 5 | 47개 |
| [002_fi_ledger](002_fi_ledger/) | ERP 회계(FI): 계정과목, 분개 전표, 시산표, 계정별 원장 | Python 3.13 · FastAPI · pytest | 34개 |
| [003_fullstack_todo](003_fullstack_todo/) | 풀스택 업무 할 일 관리 웹 앱 | TypeScript · Express · esbuild · Vitest | 35개 |
| [004_web_game](004_web_game/) | 오리지널 미니 게임 「야근 탈출」 | TypeScript · Vite · Canvas · Vitest | 27개 |
| [005_inventory_api](005_inventory_api/) | ERP 재고(MM): 입출고, 현재고, 안전재고 미달 조회 | Go 1.24 · net/http · go test | 53개(서브테스트 포함) |
| [006_ai_agent](006_ai_agent/) | Claude 도구 호출 기반 HR·회계 도우미 에이전트 | TypeScript · Anthropic SDK · Vitest | 31개 |
| [007_attendance_cli](007_attendance_cli/) | ERP 인사 근태 집계 CLI(연장·야간·휴일·지각) | Rust · cargo test · clippy | 27개 |
| [008_youtube_analyzer](008_youtube_analyzer/) | 유튜브 영상을 대본·장면 캡처·보고서로 변환해 Claude가 통째로 분석 | Python · yt-dlp · ffmpeg · pytest | 48개 |

## 테스트 실행

```bash
cd 000_sample_project/001_hr_payroll     && mvn test
cd 000_sample_project/002_fi_ledger      && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest -q
cd 000_sample_project/003_fullstack_todo && npm ci && npm test
cd 000_sample_project/004_web_game       && npm ci && npm test
cd 000_sample_project/005_inventory_api  && go test ./...
cd 000_sample_project/006_ai_agent       && npm ci && npm test
cd 000_sample_project/007_attendance_cli && cargo test
cd 000_sample_project/008_youtube_analyzer && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest -q
```

## 참고

- 급여·세금·근태 계산 규칙은 교육용으로 단순화한 것이며 실제 법정 기준과 다릅니다.
- `006_ai_agent`를 실제로 실행하려면 `ANTHROPIC_API_KEY` 환경변수가 필요합니다. 키는 커밋하지 마세요.
- 구조도: [docs/structure.svg](docs/structure.svg)
