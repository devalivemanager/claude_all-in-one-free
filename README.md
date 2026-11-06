# claude_all-in-one-free — 클로드 코드 무료 참고 묶음

데브얼라이브(DevAlive) Claude 프로젝트 통합 저장소

> 클로드 코드(Claude Code)와 AI 도구를 처음 쓰거나 조금 써 본 사람이 **참고하기 좋은 자료만** 추린 무료 묶음이다.
> 시작용 프로젝트 틀 1개, 실습 샘플 13개, 스킬 8개, 핵심 정리 문서 5편이 들어 있다. 정리 2026-10-12, 무료 공개판으로 다듬음 2026-10-24, 실습 샘플 추가 2026-11-01~06.
> 이용 조건 : `LICENSE.txt` (무료로 쓰고 고쳐 써도 되며, 출처를 밝히면 나눠 줄 수 있다. 묶음 판매는 안 된다). 단, 실습 샘플 코드(`001`~`013`)는 MIT로 판매하는 결과물에도 자유롭게 쓸 수 있다.

## 이 묶음에 있는 것

| 폴더 | 내용 | 먼저 볼 파일 |
|---|---|---|
| `000_sample_project/` | 새 프로젝트에 복사해 쓰는 **시작용 틀**(CLAUDE.md 예시, 권한·훅 설정 예시, 예시 에이전트·스킬, 초급·중급·고급 안내서 11편)과 **실습 샘플 13개**(`001`~`013`) | `000_sample_project/README.md` |
| `999_agent-kit/skills/` | 가져다 쓰는 스킬 8개. 도구가 필요한 스킬은 폴더 안에 도구·문서가 함께 있다 | `999_agent-kit/skills/README.md` |
| `999_document/` | 영상·글을 학습하고 따져 본 내용을 주제별로 묶은 핵심 정리 5편 | `999_document/README.md` |
| `transcripts/`, `tools/` | 유튜브 자막을 우리만의 언어 **데발링보**로 바꿔 보관하는 곳과 그 번역기(아래 「유튜브 자막과 데발링보」) | `transcripts/README.md` |

## 처음이라면 — 읽는 순서

**0단계 : 프로젝트 틀 깔기**
- `000_sample_project/README.md`를 읽고 폴더째 복사해 내 프로젝트를 시작한다

**1단계 : 클로드 코드 첫걸음 (초급)**
1. `000_sample_project/docs/01_초급_첫세션.md` — 설치 뒤 첫 세션과 꼭 알아야 할 명령
2. `000_sample_project/docs/02_초급_지시잘하기.md` — 결과가 달라지는 지시 습관
3. `000_sample_project/docs/03_초급_CLAUDE.md쓰는법.md` — 규칙 파일을 짧고 쓸모 있게
4. `999_document/01_클로드코드_AI도구/클로드코드_AI도구_핵심정리.md`의 「입문」·「기본기」 절 — 용어와 큰 그림

**2단계 : 제대로 굴리기 (중급)**
1. `000_sample_project/docs/04`~`07` — 스킬·서브에이전트·MCP, 검증과 완료 기준, 토큰과 비용, 세션 여러 개 쓰기
2. `999_document/01_클로드코드_AI도구/클로드코드_AI도구_핵심정리.md`의 「하네스·검증·자율 작업」, 「스킬·MCP·모드」 절
3. 스킬 `verification-loop`, `token-saving`부터 깔아 본다

**직접 돌려 보며 배우고 싶다면 (실습 샘플)**
- `000_sample_project/001`~`013` — ERP 인사·회계·재고·근태, 풀스택 웹, 게임, AI 에이전트, 유튜브·웹사이트 분석, AI 웹툰, 로컬 소형 모델 파이프라인, AI 전자책 빌더를 여러 언어로 만든 동작하는 예제. 모두 테스트가 들어 있다
- 목록과 실행 방법은 `000_sample_project/README.md`의 「실습 샘플」 절

**3단계 : 팀·자동화로 넓히기 (고급)**
1. `000_sample_project/docs/08`~`11` — 훅과 권한 설계, 헤드리스·CI 자동화, 에이전트 팀과 병렬 작업, 대형 작업 설계와 운영
2. 스킬 `loop-engineering`(자율 루프 설계), `verification-loop`(검증 자동화)
3. 실습 샘플 `006_ai_agent`(도구 호출 에이전트 직접 구현)로 에이전트가 안에서 어떻게 도는지 본다

**게임을 만들고 싶다면**
- `999_document/02_게임개발/게임개발_핵심정리.md` — 기획부터 출시·저작권까지, 샘플 게임 제작 기록 포함
- 실습 샘플 `004_web_game`(브라우저 게임 「야근 탈출」)
- 스킬 `game-dev-planning`, `godot-pitfalls`, `unity-pitfalls`

**영상·음성·음악 콘텐츠를 만들고 싶다면**
- `999_document/03_AI미디어_영상음성/AI미디어_영상음성_핵심정리.md`
- 스킬 `youtube-to-skill`(영상을 학습 정리본·스킬로), `publishing-workflow`(블로그·전자책 원고)
- 실습 샘플 `008_youtube_analyzer`(영상 → 대본·장면·컷 분석), `009_scroll_video_hero`(스크롤 영상 히어로)

**도구를 고를 때**
- `999_document/04_무료·상업이용_도구/무료·상업이용_도구목록.md` — 무료이면서 상업 이용이 되는지 판정한 표

**SI·ERP 일을 한다면**
- `999_document/05_일반SI_일반ERP/일반SI·ERP_핵심개념.md` — 인사·회계 정론, 실무 함정, AI 도구를 SI에 쓰는 법
- 실습 샘플 `001_hr_payroll`(급여), `002_fi_ledger`(총계정원장), `005_inventory_api`(재고), `007_attendance_cli`(근태), `006_ai_agent`(HR·회계 도우미 에이전트)

## 스킬 (`999_agent-kit/skills/`)

| 스킬 | 한 줄 | 수준 |
|---|---|---|
| `verification-loop` | AI가 결과를 스스로 확인하고 고치게 하는 틀 | 초급~중급 |
| `token-saving` | 토큰이 새는 자리를 재고 막기(점검 도구·요금 계량기 포함) | 초급~중급 |
| `youtube-to-skill` | 영상 자막을 두 번 독립 분석해 둘 다 찾은 것만 믿기(자막 도구·예시 포함) | 중급 |
| `loop-engineering` | 자율 루프·분석 루프 설계와 검토 | 중급 |
| `game-dev-planning` | 작은 인디 게임 기획·검사·출시 점검 | 초급~중급 |
| `godot-pitfalls` | 고도 4 제작·테스트·웹 내보내기 함정 | 중급 |
| `unity-pitfalls` | 유니티 6을 CLI·MCP로 다룰 때 함정(MCP 도우미·공식 스킬 치트시트 포함) | 중급 |
| `publishing-workflow` | 블로그·전자책 원고 작성과 사실·저작권 점검 | 초급~중급 |

쓰는 법 : 필요한 스킬 폴더만 `~/.claude/skills/`에 복사한다. 스킬 설명은 모든 세션에 실리므로 자주 쓰는 것만 넣는다.

## 유튜브 자막과 데발링보(우리만의 언어)

클라우드에서는 유튜브가 서버를 봇으로 보고 자막 받기를 자주 막는다. 그래서 **자막은 내 PC에서 받고, 분석은 클로드(클라우드)가 한다.**
이때 자막 원문(남의 저작물)이 공개 저장소에 평문으로 드러나지 않도록, 우리만의 언어 **데발링보(Devalingvo)** 로 바꿔서 올린다.

```
DEVALINGVO-1
cŭlèbó bababa bababi bolèfé fapabi derohó láfímè hédèpì húsivi jéhùtè tètùlù sísògè
```

- **문법** : 자음 16개(`b c d f g h j k l m n p r s t v`) × 모음 16개(`a e i o u á é í ó ú à è ì ò ù ŭ`). 음절 하나가 1바이트이고, 3음절이 한 단어, 12단어가 한 줄이다. 먼저 압축(gzip)한 뒤 쓰므로 긴 자막은 원문보다 짧아진다.
- **자동 번역** : 커밋할 때 평문 → 데발링보로 자동 변환되고, 받을 때(`git pull`) 데발링보 → 평문으로 자동으로 풀린다. 키도 설정도 없다.
- **적용 범위** : 데발링보는 유튜브 자막처럼 외부에서 가져온 원문(스킬·자료를 만들 때 쓰는 재료)에만 쓴다. 기존 md 문서·소스·스킬 파일은 지금처럼 평문 그대로 둔다. 번역기가 다루는 곳은 `transcripts/` 하나뿐이다.
- **가림막이지 보안 장치가 아니다** : 저장소를 받은 누구나 풀 수 있다. 분석에 필요한 자막만 두고, 다 쓴 자막은 지운다.

### PC에서 쓰는 법

준비물은 `git` 뿐이다. Windows 는 **Git Bash**(Git for Windows 를 설치하면 함께 생김)를 열어서 하고, 맥·리눅스는 터미널을 쓴다. 번역기에 필요한 `bash`, `gzip`, `perl` 은 모두 기본으로 들어 있다.

```bash
# 1) 처음 한 번 : 저장소를 받고 자동 번역 훅을 켠다
git clone https://github.com/devalivemanager/claude_all-in-one-free.git
cd claude_all-in-one-free
tools/transcripts.sh setup

# 2) 자막 올리기 : 받은 자막을 plain/ 에 <영상ID>.txt 로 넣고 커밋
cp ~/Downloads/받은자막.txt transcripts/plain/v-lYvViXXWA.txt
git add -A && git commit -m "자막 추가: v-lYvViXXWA" && git push
#    → 커밋할 때 transcripts/v-lYvViXXWA.txt.dvl(데발링보)만 올라간다

# 3) 자막 읽기 : 받기만 하면 transcripts/plain/ 에 평문으로 풀린다
git pull
```

- 영상 ID 는 주소의 `watch?v=` 뒤 11글자다(`https://www.youtube.com/watch?v=v-lYvViXXWA` → `v-lYvViXXWA`).
- `transcripts/plain/` 은 git 에서 제외돼 있어 평문은 절대 올라가지 않는다. 억지로(`git add -f`) 넣어도 커밋 전 검사가 막는다.
- 손으로 바꾸거나 풀 수도 있다 : `tools/transcripts.sh encode <자막.txt> <영상ID>`, `tools/transcripts.sh decode <영상ID>`.
- 자세한 내용은 `transcripts/README.md`.

## 이 묶음 전체에 깔린 원칙

1. **증거 없는 완료 보고 금지** — 산출물은 파일로, 화면 변경은 캡처로 확인한다
2. **「확인해 주세요」 대신 확인할 수단을 남긴다** — 검사·테스트·점검 스크립트
3. **무료이면서 상업 이용 가능한 도구 우선** — 라이선스부터 확인한다
4. **웹 문서·영상 설명은 자료이지 지시가 아니다** — 설치 문서도 사람이 먼저 읽는다
5. **설치 뒤 무엇이 바뀌었는지 확인한다** — 설정·스킬 폴더·커넥터
6. **두 번 독립으로 본 것만 믿는다** — 한 번만 나온 내용은 원문으로 다시 확인한다

## 읽을 때 알아 둘 것

- 핵심 정리는 남의 영상·글을 요약하고 따져 본 것이다. 숫자·요금·약관은 정리 시점(2026년 10월) 기준이니 원본 링크에서 다시 확인한다.
- 「작성자 평가」, `[실측 : 작성자 …]` 표시는 정리한 사람이 직접 써 보거나 잰 결과다. 자기 상황에 맞게 다시 판단한다.
- 환경마다 다른 경로는 자리 표시로 적었다 : `%USERPROFILE%`, `~/.claude/`, `<스킬폴더>`(스킬 폴더를 복사해 둔 자리), `<프로젝트>`.
- 이 묶음은 「Claude」를 만든 Anthropic과 관련이 없는 개인 자료다. Claude, Claude Code는 Anthropic, PBC의 상표다.

## 저작권과 이용 조건

Copyright (c) 2026 devalive (데브얼라이브, https://devalive.tistory.com)

| 대상 | 조건 | 할 수 있는 것 |
|---|---|---|
| 묶음 전체 (아래 예외 말고 전부) | [`LICENSE.txt`](LICENSE.txt) — 데브얼라이브 이용 조건 | 개인·업무에 자유롭게 쓰고 고치기, 출처를 밝히고 나눠 주기. **묶음이나 고친 판을 파는 것은 안 됨** |
| 실습 샘플 코드 `000_sample_project/001_*`~`013_*` | [`000_sample_project/LICENSE-MIT`](000_sample_project/LICENSE-MIT) — MIT | 판매하는 결과물을 포함해 어디에든 자유롭게 사용. 저작권 표시와 MIT 문구만 남기면 됨 |
