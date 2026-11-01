# skills — 가져다 쓰는 스킬 8개

> 스킬은 클로드 코드가 상황에 맞춰 스스로 꺼내 읽는 작업 안내서다. 폴더 안 `SKILL.md` 맨 위의 `description`이 「언제 꺼낼지」를 정한다.
> 예전에 따로 있던 키트(토큰 절약, 유튜브 → 스킬, 유니티 MCP 도우미, 유니티 치트시트)는 짝 스킬 폴더 안으로 합쳤다. **한 주제는 한 폴더**이고, 그 안에 절차(`SKILL.md`)와 도구·문서가 함께 들어 있다.

## 설치

- 쓰고 싶은 스킬을 **폴더째** 복사한다
  - 모든 프로젝트에서 쓰려면 : `~/.claude/skills/<스킬이름>/` (Windows는 `%USERPROFILE%\.claude\skills\<스킬이름>\`)
  - 한 프로젝트에서만 쓰려면 : `<프로젝트>/.claude/skills/<스킬이름>/`
- 새 세션을 열면 걸린다. 스킬 설명은 모든 세션에 실리므로 **자주 쓰는 것만** 넣는다
- 스킬 본문의 `<스킬폴더>`는 그 스킬 폴더를 복사해 둔 자리다(예 : `~/.claude/skills/token-saving`)

## 들어 있는 스킬

| 스킬 | 언제 쓰나 | 폴더 안에 함께 있는 것 | 수준 |
|---|---|---|---|
| `verification-loop` | AI가 결과를 스스로 확인하고 고치게 하는 틀(과제·지킬 선·확인 방법·끝나는 조건), 같은 지적이 반복될 때 규칙·자동 검사로 올리기 | — | 초급~중급 |
| `token-saving` | 위임 손익분기·effort·상시 적재 파일을 점검해 토큰을 아낀다 | 원칙·지시문·점검표, 점검 도구(PowerShell·bash), 요금 계량기(Python) | 초급~중급 |
| `youtube-to-skill` | 유튜브 영상을 두 번 독립 분석해 둘 다 찾은 내용만 믿고, 학습 정리본이나 스킬로 만든다 | 원칙·지시문, 자막 도구(Python), 스킬 틀, 완성 예시 | 중급 |
| `loop-engineering` | 자율 루프·재귀 분석 루프를 설계하고 검토할 때 | — | 중급 |
| `game-dev-planning` | 엔진과 상관없는 작은 인디 게임 기획·검사·출시 점검 | — | 초급~중급 |
| `godot-pitfalls` | 고도 4 게임 제작·테스트·웹 내보내기 함정 | — | 중급 |
| `unity-pitfalls` | 유니티 6을 CLI·MCP로 다룰 때 함정 | MCP 도우미(`tools/`), 유니티 공식 스킬 치트시트 | 중급 |
| `publishing-workflow` | 블로그·전자책 원고 작성, 사실·저작권 점검, 발행, EPUB 묶기 | — | 초급~중급 |

처음이라면 `verification-loop`와 `token-saving` 둘부터 넣어 본다. 나머지는 해당 일을 할 때 넣는다.

## 남이 만든 스킬 (이 묶음에 넣지 않음, 출처에서 받는다)

라이선스가 제각각이라 넣지 않았다. 필요하면 원 저장소에서 받고, 받기 전에 라이선스를 확인한다.

| 스킬 | 용도 | 받는 곳 |
|---|---|---|
| gstack 묶음(review·qa·ship·design-review 등) | 리뷰·QA·배포 워크플로 | gstack |
| gsd 묶음(gsd-*) | 단계별 기획·실행·검증 | Get Shit Done |
| `impeccable` | 프론트엔드 디자인 점검(Apache-2.0) | impeccable |
| `design-taste-frontend`, `supanova-design` | 랜딩 페이지·「AI 티」 없는 화면 | 각 저장소 |
| `prompt-master` | 도구별 프롬프트 작성 | 원 저장소 |
| `find-skills` | 스킬 검색·설치 | skills.sh |
| `agent-browser` | 브라우저 자동화 CLI | vercel-labs |
