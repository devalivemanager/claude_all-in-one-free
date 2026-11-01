# 000_sample_project — 샘플 프로젝트 모음

ERP(인사·회계·재고·근태), 풀스택 웹, 게임, AI 에이전트, 유튜브·웹사이트 분석 도구를 여러 언어로 구현한 교육용 샘플 모음입니다.
모든 샘플은 외부 DB 없이 동작하고, 각 폴더의 README에 실행·테스트 방법이 있습니다.

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
| [008_youtube_analyzer](008_youtube_analyzer/) | 유튜브 영상을 대본·장면 캡처·보고서로 변환해 Claude가 통째로 분석 | Python · yt-dlp · ffmpeg · pytest | 65개 |
| [009_scroll_video_hero](009_scroll_video_hero/) | 영상을 프레임으로 쪼개 스크롤에 맞춰 재생·역재생하는 랜딩 페이지 히어로 | JavaScript · ffmpeg · Canvas · node:test · Playwright | 31개 |
| [010_site_analyzer](010_site_analyzer/) | 웹사이트 구조·기술·디자인 특징을 분석 보고서로 정리(복제 없음, robots.txt 준수) | JavaScript · Playwright · node:test | 61개 |

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
cd 000_sample_project/009_scroll_video_hero && npm test
cd 000_sample_project/010_site_analyzer   && npm test
```

## 참고

- 급여·세금·근태 계산 규칙은 교육용으로 단순화한 것이며 실제 법정 기준과 다릅니다.
- `006_ai_agent`를 실제로 실행하려면 `ANTHROPIC_API_KEY` 환경변수가 필요합니다. 키는 커밋하지 마세요.
- `009`, `010`의 브라우저 테스트는 Playwright가 필요합니다. 없으면 해당 테스트만 건너뜁니다. 설치 방법은 각 README에 있습니다.
- `010_site_analyzer`는 내 사이트나 허락받은 사이트를 공부하는 용도입니다. 콘텐츠·이미지·로고를 복제하지 않습니다.
- 구조도: [docs/structure.svg](docs/structure.svg)

## 라이선스

Copyright (c) 2026 devalive

[MIT 라이선스](../LICENSE)입니다. 누구나 자유롭게 복사·수정·배포하고 상업적으로 사용할 수 있습니다. 단, 저작권 표시와 라이선스 문구는 남겨 주세요.

- 각 샘플이 사용하는 외부 라이브러리(npm, pip, Maven 등)는 각자의 라이선스를 따릅니다.
- 급여·세금 계산 등은 교육용으로 단순화한 것이라 실무에 그대로 쓰면 안 됩니다(라이선스상 "있는 그대로" 제공, 보증 없음).
