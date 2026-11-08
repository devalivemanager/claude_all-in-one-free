# 토큰 절약 스킬 (token-saving)

> 이 폴더째 `~/.claude/skills/`에 복사하면 「토큰 아껴 줘」 같은 말에 클로드가 `SKILL.md`의 절차를 따른다. 이 README는 사람이 처음 읽는 안내이고, 작업 절차는 `SKILL.md` 한 곳에만 있다.

> 판 : v1.0 (2026-10-02) · 대상 : Claude Code (데스크톱·CLI) 중심, 원칙 다수는 다른 AI 도구에도 통함 · 무료 · 만든 곳 : 데브얼라이브 블로그 https://devalive.tistory.com
> 실측·흡수한 토큰 절약의 정수를 한 묶음으로 모았다. 특정 회사·프로젝트 정보는 담지 않았다.
> **필요한 것** : Claude Code를 써 본 기록(세션 파일). 점검 도구는 Windows PowerShell 5.1 이상 또는 bash, 요금 계량기는 Python 3. 설치할 것은 없다. 폴더는 아무 곳에 두어도 된다

## 3분 시작

1. 이 폴더를 `~/.claude/skills/token-saving/`(아래 `<스킬폴더>`)에 복사한다. 스킬로 쓰지 않고 도구만 쓸 거라면 아무 곳에 두어도 된다
2. 점검하고 싶은 프로젝트 폴더에서 현황을 잰다(읽기 전용, 아무것도 안 바꾼다)
   - Windows : `powershell -ExecutionPolicy Bypass -File <스킬폴더>\tools\token-audit.ps1`
   - macOS·Linux·Git Bash : `bash <스킬폴더>/tools/token-audit.sh`
   - 요금 계량기(Python 3) : `python <스킬폴더>/tools/token-meter.py <프로젝트폴더> --days 7`
3. 출력에서 숫자가 큰 절 하나를 골라 한 가지만 고치고, 같은 도구로 다시 잰다. 자세한 순서는 `SKILL.md` 2절이다
4. 설정을 바꾸는 도구 `apply-token-saving.ps1`은 먼저 `-WhatIf`로 대상만 본다

## 누가 어떻게 쓰나

| 상황 | 볼 것 |
|---|---|
| Claude Code · **Windows** | 전부. `token-audit.ps1`·`apply-token-saving.ps1` (Windows PowerShell 5.1 이상). Git Bash 가 있으면 `token-audit.sh` 도 된다 |
| Claude Code · **macOS / Linux** | 문서 3개 + **`token-audit.sh`**(bash·기본 도구만, python3 있으면 MCP 목록까지). effort 낮추기는 `03_점검표.md` 대로 손으로(설정 한 줄 + Opus 5.5 이후는 `modelSettings` + 에이전트 `effort:` 줄) |
| Claude Code · **WSL 안에서 실행** | `TOKEN_AUDIT_POSIX_KEY=1 bash tools/token-audit.sh` — 리눅스식 경로 키로 찾는다 |
| **다른 AI 도구**(챗GPT·제미나이 등) | `01_원칙_정수.md` 의 **1장(재작업)·3장(읽기)·4장(쓰기)·7장(함정)** + `02_지시문.md` ①·④·⑦ — 대화형 AI 어디에나 통한다 |
| 처음 보는 사람 | 아래 「꼭 기억할 것 세 가지」 → 1장만 읽어도 절반은 건진다 |

## 나눠 줄 때

- 폴더째 복사하거나 압축해서 보낸다(`LICENSE.txt` 조건 : 출처를 밝히면 나눠 줄 수 있고, 판매는 안 된다)
- 받는 사람 PC 경로·설정 폴더가 달라도 된다 — 도구가 `CLAUDE_CONFIG_DIR` 와 `-ProjectDir` 로 스스로 찾는다
- 숫자(`[실측]`)는 작성자 환경 값이다. **자기 환경에서 다시 재서** 판단하라(원칙 39)

## 오래 쓰려면 — 바뀌는 것과 안 바뀌는 것

| 안 바뀐다 (원칙 · 계속 씀) | 바뀐다 (명령어 · 도구 · 요금 · 화면 위치) |
|---|---|
| 구체적으로 시키기 · 계획 먼저 · 확인 수단 · 컨텍스트 관리 · 두 번 실패하면 새로 · 규칙 파일 한 장 · 공통 프롬프트 원칙 | `/btw`·`/compact`·`/goal`·`ultrathink`·`skillOverrides` 같은 이름, 모델 단가, 설정 키, 메뉴 위치 |

이 키트의 **원칙(01 장 본문)은 왼쪽**, 괄호 안 명령어·숫자·단가는 **오른쪽**이다. 오른쪽은 기준일(**2026-10-02**)이 지나면 공식 문서로 다시 확인한다. 실제로 반년 사이 「답변 앞부분 채우기(prefill)」 지원 종료, 할 일 목록 도구(TodoWrite) 제거, 「think hard」류 키워드 무효화, 기본 권한 모드 변경이 있었다 `[외부]` — 하네스에 이런 죽은 지시어가 남아 있으면 토큰만 쓴다.

## 들어 있는 것

| 파일 | 내용 | 언제 |
|---|---|---|
| `01_원칙_정수.md` | **원칙 40개를 효과 큰 순서로** 7장(재작업·위임·읽기·쓰기·상시 적재·세션·함정). Ponytail·카파시·검증 루프·Graphify·공식 문서·업무 파일화 정수 포함, 근거 표시 `[실측]`·`[외부]`·`[공식]` | 처음 한 번 정독 |
| `02_지시문.md` | 그대로 붙여 쓰는 지시문 7개(⑦ 어떤 AI 에나 통하는 공통 6원칙 틀) | 일 맡길 때 |
| `03_점검표.md` | 절약 조치 전·후 점검 순서와 측정법 · 함정 | 절약 조치를 할 때 |
| `tools/token-audit.ps1` | **읽기 전용** 현황 점검(Windows) — 출력 절 [1]~[5] 마다 해당 원칙 번호가 붙어 나온다 | 조치 전후 비교 |
| `tools/token-audit.sh` | 같은 점검의 **macOS·Linux·Git Bash 판** — 같은 절·같은 숫자 | 조치 전후 비교 |
| `tools/token-meter.py` | **요금 계량기**(읽기 전용·설치 없음·모든 OS) — 대화 기록에서 입력·캐시 쓰기·캐시 읽기·출력 네 줄의 토큰·비용·**비용 비중**과 원화. `--days`·`--compare`·`--session`·`--all` | 「돈이 어디로 나가나」·도구 켜기 전후 비교 |
| `tools/idle-cost.py` | **읽기 전용** — 「1시간 넘게 쉬었다가 다시 부른 턴」이 비용의 몇 %인지 잰다(원칙 41). `python tools/idle-cost.py <설정폴더>/projects/<프로젝트 기록 폴더>` | 오래 쉰 세션을 이어 쓸지 판단할 때 |
| `tools/apply-token-saving.ps1` | 전역 effort=low(최상위 + Opus 5.5 이후용 `modelSettings`) + 에이전트 high/xhigh→medium. **`-WhatIf` 로 대상만 미리 보기**, `CLAUDE_CONFIG_DIR`·`-ProjectDir` 반영, 자동 백업 | 한도가 빠듯할 때 |

기간 비교 예 : `python tools/token-meter.py --all --compare 2026-09-01..2026-09-10 2026-09-11..2026-09-20`. 구독제는 금액 대신 「한도를 어디서 먹나」 비율로 읽는다.

## 시험 기록 `(2026-10-02)`

실행 전에 기대값을 적고 돌렸다. 맥·리눅스 기계는 없어서 **같은 조건을 흉내 낸 시뮬레이션**으로 시험했다.

| 시험 | 조건 | 결과 |
|---|---|---|
| A | Git Bash 판 ↔ PowerShell 판, 실제 프로젝트 2개 | ✅ 에이전트 분포·파일 크기·위임 17건·세션 5,562줄·스킬 끄기 109개가 **같은 숫자** |
| B | 가짜 홈 + 맥식 경로 키(`TOKEN_AUDIT_POSIX_KEY=1`) + 다른 설정 폴더 | ✅ 기대값 7개 전부 일치(effort·에이전트·색인·MCP·스킬 끄기 2·세션 3,100줄 heavy·위임 1) |
| C | PowerShell 5.1 + 다른 설정 폴더(`CLAUDE_CONFIG_DIR`) | ✅ — ★처음엔 MCP·스킬 끄기 줄이 빠지는 **결함을 잡았고**(사전 객체 메서드 차이) 고친 뒤 통과 |
| D | `apply-token-saving.ps1 -WhatIf` + 다른 설정 폴더 | ✅ 대상 1개(high) 정확히 표시 · 아무것도 안 바꿈 |
| E | 상대경로 `.` · 끝의 `\` · 없는 경로 | ✅ 정상 처리 · 없는 경로는 안내 후 종료 |
| F | **계량기 단가식 ↔ 기록된 실제 청구액**(`costUSD`) | ✅ **$29.439337 = $29.439337** 소수점 여섯째 자리까지 일치(Opus 5 · 캐시 쓰기 1시간 2배·읽기 0.1배) |
| G | 계량기 ↔ 「토큰 계량기」 원본(방구석컴퍼니), 같은 7일 기록 | ✅ 네 줄 토큰 수 한 자리까지 동일 · 금액 차이는 Opus 5.5 단가 가정 차이뿐(정확히 1.25배) |
| H | 108회 원본 기록 재계산(소넷 5) | ✅ 기록 금액과 비율 1.000 일치 · effort 낮춤 −15.9%, 도구 4종 −1.8%~+37.7% 재현 |
| I `(2026-10-03)` | `apply-token-saving.ps1` **실제 적용** — 가짜 설정 폴더 4개(CRLF·한글·`<` 든 settings.json · 키 없음 · 빈 `{}` · `-WhatIf`), 에이전트 4종(CRLF+뒤 공백 high · xhigh · low · BOM 붙은 high) | ✅ 14개 검사 전부 통과 — settings.json 은 **effortLevel 한 곳만** 바뀜(나머지 바이트 동일) · BOM 없음 · CRLF 유지 · low 는 그대로 · 원래 있던 BOM 도 제거. ★종전판은 BOM 을 붙이고(frontmatter 앞) JSON 전체를 다시 써서 서식이 바뀌는 **결함**이 있었다 → 고친 뒤 통과 |
| J `(2026-10-04)` | ★**Opus 5.5 는 사용자 설정의 최상위 `effortLevel` 을 무시한다**(공식 문서 model-config · settings-reference, 독립 검증 3명 일치) → 종전 판은 Opus 5.5 세션에 **효과 0**이었다. `apply-token-saving.ps1` 이 `modelSettings`(opus-5-5 · sonnet-5-5)도 쓰고, `token-audit` 두 판이 `modelSettings` 를 보여 주도록 고침 | ✅ 실제 PC 점검(ps1·sh 같은 결과) + 가짜 설정 3종 — `modelSettings` 없음(CRLF·한글) → 블록만 추가되고 나머지 바이트 동일 · 이미 있음 → 건드리지 않고 경고 · `-WhatIf` → 변경 0. ★원칙 38 「실제로 실리는가」의 실례 · ★같은 날 재수정 — 첫 판은 파일에서 처음 나오는 `effortLevel` 을 바꿔 두 번째 실행·「최상위 없음 + modelSettings 있음」에서 실패했다(독립 검증이 잡음) → 최상위 키를 깊이 1 로만 찾도록 고치고 회귀 시험 12개 통과 |

**단가 출처** — Opus 5·Sonnet 5·Haiku 4.5 는 위 F·H 로 **역산 검증**, Opus 5.5·Sonnet 5.5 는 외부 자료 값($4/$20·$2/$10)이라 공식 요금표로 확인 후 `--price` 로 바꿔 쓴다.

**아직 실기기에서 못 돌린 것** — PowerShell 7(맥·리눅스용) 은 작성자 PC 에 없어 **정적 검토만** 했다(JSON 은 `-AsHashtable` 분기, 경로는 OS 무관 결합). 진짜 맥에서 처음 쓰면 `token-audit.sh` 를 먼저 권한다.

## 꼭 기억할 것 세 가지

1. **설정으로 짜낼 수 있는 것은 금방 바닥난다.** 실질 절약은 습관(위임 자제·증분 편집·조사 전 기억부터)이다
2. **「몇 개를 바꿨나」가 아니라 「그게 실제로 자기 세션에 실리는가」가 절감액을 정한다** — 안 도는 에이전트를 내려 봐야 0, 다른 설정 폴더를 고쳐 봐야 0
3. **단가가 아니라 끝날 때까지 든 총비용**으로 본다 — 싼 모델이 검증을 세 배 돌면 비싸다

## 출처

- 자체 실측 : 2026-07~10 작성자의 실제 개발 프로젝트 세션들 (위임 손익분기·스킬 주입량·세션 파일 비대·effort 조정·기억 색인)
- [Claude Code 공식 모범사례](https://code.claude.com/docs/en/best-practices)
- 「클로드 코드 토큰 계량기 · 108회 실측 원본」(방구석컴퍼니, 2026-09-22) — 계량기 아이디어와 108회 기록. `tools/token-meter.py` 는 독립 구현이며 원본과 토큰 수를 대조 검증했다(시험 G)
- [lazyowen 가이드](https://lazyowen.com/guides) 중 토큰 절약·PDF·pxpipe·Graphify·필수설정 — 장점만 흡수
