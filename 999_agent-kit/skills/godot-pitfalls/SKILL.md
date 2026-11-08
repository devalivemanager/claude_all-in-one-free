---
name: godot-pitfalls
description: Use when starting, building, testing, or exporting a Godot (고도) 4 game project — writing GDScript or .tscn, wiring the Godot MCP, running headless tests, capturing screenshots, adding UI/translation/sound, or exporting to web/itch.io. Triggers on "고도", "Godot", "GDScript", ".tscn", "godot-mcp", "고도 게임", "고도 함정", "웹 내보내기", "itch.io".
---

# 고도 4 함정 모음 (한 장 안내서)

> 작성자가 실제 제작에서 겪고 확인한 고도 함정을 한 장으로 모은 것이다.
> 각 항목 끝 괄호는 출처(작성자가 만든 샘플 게임 「별무리 사격」·슈팅 시제품, MCP 실측)다.
> 새 함정이 **두 번** 나오면 여기에 올린다.

## 0. 준비물 (작성자가 확인한 판 기준)

- 고도 : `Godot_v4.7.2-stable_win64_console.exe`(로그가 터미널에 나오는 쪽)를 명령용으로 쓴다. 창 실행은 `..._win64.exe`. 아래 `<console.exe>`는 이 파일의 전체 경로다
- 프로젝트 : 게임마다 폴더 하나(`<게임프로젝트폴더>/<이름>/`)
- MCP : `Coding-Solo/godot-mcp@0.1.1`을 **프로젝트마다** `.mcp.json`으로 등록(서버 이름 `godot`). 그 폴더에서 처음 `claude`를 열 때 사람이 승인한다
- 웹 내보내기 템플릿 : `%APPDATA%\Godot\export_templates\4.7.2.stable\`(웹용만 넣어도 된다)

## 1. 시작할 때

1. **프로젝트 폴더에 `CLAUDE.md` + 네 칸**(과제·지켜야 할 선·확인 방법·끝나는 조건)을 먼저 쓴다(별무리 사격 제작 기록)
2. **화면 문장은 첫날부터 번역 표** — `i18n/strings.csv`(keys,ko,en) + `tr("KEY").format({...})`. 서식 문장도 표에 둔다(별무리 사격)
   - CSV는 가져오기(import) 뒤에야 `.translation`이 생긴다. 첫 가져오기 때 「열 수 없음」 에러는 정상이고, 두 번째부터 사라지면 된다
3. **씬을 다시 불러도 남아야 할 값(점수·최고 점수·목숨)은 자동 로드(싱글톤)** 에 둔다(별무리 사격 `GameState`)
4. **그림은 `_draw()`나 GDScript `Image`로 직접 그려도 된다** — 작은 기체·아이콘·타일은 돈·저작권 걱정이 없다(별무리 사격)
5. **남의 게임 이름·캐릭터·소리 금지** — 장르·플레이 방식만 따른다(갤러그 → 「별무리 사격」)

## 2. 만들 때

- **충돌은 층(layer)과 마스크(mask)로 「누가 누구를 감지하나」를 정한다** — 예 : 1 기체, 2 적, 4 플레이어 총알(mask 2), 8 적 총알(mask 1)(별무리 사격)
- **사라질 물체(공·총알)에 효과음을 맡기지 않는다** — 물체가 지워지면 소리도 끊긴다. 자동 로드나 오래 사는 노드에서 재생(별무리 사격 `Sfx`)
- **한 프레임에 두 번 맞는 문제** — 총알에 `spent` 표시, 적은 `is_queued_for_deletion()` 확인(별무리 사격)
- **`queue_free()`한 노드는 그 프레임 끝까지 자식으로 남는다** — 「남은 적 수 == 0」 판정은 다음 프레임에 맞는다(별무리 사격)
- **숨긴 노드를 자기 `_process`가 다시 보이게 만드는 경우** — 상태 값(예 : `alive`)도 함께 끈다(별무리 사격 타이틀 버그)
- **정수 나눗셈 경고** — `stage / 2` 대신 `int(stage / 2.0)`(별무리 사격, MCP가 잡음)
- 설계 교훈(범위·검사·라이선스)은 이 스킬이 아니라 `game-dev-planning` 스킬이 맡는다. 새 게임 기획 전에 읽는다
- ★**월드 노드에 배율(scale)을 걸면 `global_position`은 뷰포트 픽셀이다** — 게임 단위 좌표와 섞으면 탄이 화면 밖에서 생기거나(보스가 쏘지 않는 것처럼 보임) 봇 조준이 틀어진다. 게임 단위가 필요하면 `컨테이너.to_local(n.global_position)`. 물체를 0.5배로 그리면 발사 위치·폭발 범위 같은 오프셋에도 배율을 곱한다(슈팅 시제품 HD 렌더, 두 곳 이상에서 같은 버그)
- ★**글자를 고정 픽셀 간격으로 놓으면 언어·숫자에 따라 겹친다** — `FONT.get_string_size()`로 실제 폭을 재서 차례로 놓는다. 영어는 한국어보다 1.5~2배 길다(슈팅 시제품 무기 목록 「SPREABACK」, 「SPEED 3」과 폭탄 아이콘)
- ★**픽셀 아트를 소수 배율(1.5배 등)로 키우면 픽셀 굵기가 1칸·2칸으로 섞여 뭉개져 보인다** — PC 창은 `content_scale_stretch = INTEGER` + 화면에 맞는 가장 큰 정수 배율. 색수차·필름 입자·낮은 블룸 문턱도 「뿌연」 느낌의 원인(슈팅 시제품 1.5배 창·화면 셰이더)
- ★**배경과 기체·적·탄이 같은 색 계열이면 위장복이 된다** — 어두운 주변광(CanvasModulate) 임무에서는 플레이어·적·아이템에만 주변광을 일부 상쇄(`self_modulate`)하고, 적 탄에는 어두운 테두리와 흰 심을 둔다(슈팅 시제품 주황 협곡·남색 임무)
- ★**메뉴 터치는 「같은 화면에서 누르고 같은 항목 위에서 뗐을 때」만 결정한다** — 누를 때 바로 결정하면 클릭 하나가 화면을 연달아 넘긴다(웹판에서 타이틀→임무 1까지 한 번에 넘어감). 「화면 바뀐 뒤 0.25초 무시」 같은 시간 장치는 숨은 브라우저처럼 프레임이 느리면 소용없다(슈팅 시제품 웹판 실측)
- ★**`_draw()` 안에서 처음 `load()`한 그림은 하얀 네모로 그려지고 다음 프레임에도 그대로다**(호환성 렌더러) — 그림은 `preload` 상수나 `_ready()`에서 미리 불러 둔다. 시험 : 미리 불러온 그림 (163,179,212) vs 그리는 중 불러온 그림 (255,255,255)(슈팅 시제품 실측)
- **셰이더에서 `TEXTURE`·`SCREEN_TEXTURE` 같은 내장 텍스처를 함수 인자(sampler2D)로 넘기지 않는다** — 호환성 렌더러에서 「custom_samplers has tex_builtin」 오류. 색을 읽어 vec3로 넘긴다(슈팅 시제품)

## 3. 검사할 때(자동·시각·사용 세 종류를 섞는다)

| 검사 | 명령 | 볼 것 |
|---|---|---|
| 가져오기 | `<console.exe> --headless --path . --import` | 스크립트 클래스 등록·에러 |
| 자동·사용 | `<console.exe> --headless --path . --fixed-fps 60 --quit-after <프레임> -- --autoplay` | 게임 안 봇이 남기는 `[TEST]` 로그(고정 fps면 3분 분량이 몇 초에 끝난다) |
| 시각 | `<console.exe> --path . --write-movie shots/play.avi --fixed-fps 30 --quit-after 1500 -- --autoplay` 뒤 `ffmpeg -ss <초> -i shots/play.avi -frames:v 1 shots/x.png` | 캡처를 직접 열어 「눈으로 볼 곳 3개」를 예/아니오로 |
| 시각(창 크기를 바꾸는 게임) | 게임 안 저장 훅(예: `-- --shots=초,…` → `get_viewport().get_texture().get_image().save_png()` 후 종료) | ★`--write-movie`는 **시작할 때의 창 크기로 고정**돼, 실행 중 창 크기를 바꾸면 녹화가 잘린다(슈팅 시제품 PC판 2회). 캡처 폴더에는 `.gdignore`를 둬 고도가 사진을 가져오지 않게 |
| MCP | `run_project` → `get_debug_output` → `stop_project` | `errors` 칸(경고까지 잡아 준다) |

- **봇을 게임 안에 넣어 둔다** — `OS.get_cmdline_user_args()`로 `--autoplay`를 받고, 사망 경로 시험용 `--nododge`도 둔다. 사람이 못 하는 반복 확인을 봇이 한다
- **MCP `run_project`는 창을 띄운다** — 그 사이 사용자가 치는 키(스페이스·엔터)가 게임에 들어간다. 창 실행 전에 알리거나 헤드리스로 돌린다(실제로 있었음)
- **`add_node`로 넘긴 위치 같은 세부 속성은 무시될 수 있다** — 씬 세부는 `.tscn`을 직접 고친다. MCP는 실행·출력 회수용(MCP 실측)
- **헤드리스 + 효과음이면 종료 때 「ObjectDB 누수 / resources still in use」 경고가 난다** — 가짜 오디오 장치가 재생 객체를 놓지 않아서다. 실제 오디오(창 모드)로 같은 실행을 하면 사라진다. 효과음 노드의 `_exit_tree`에서 `stop()`해 두고, 남는 경고는 창 모드로 대조해 판정한다(별무리 사격)
- **봇 명중률로 난이도를 판단하지 않는다** — 손맛·난이도는 사람이 해 본다

## 4. 웹으로 낼 때

1. 템플릿은 공식 릴리스의 `export_templates.tpz`에서 웹용(`web_*.zip`, `version.txt`)만 위 폴더에 둔다. SHA512를 확인한다. 받은 원본 `.tpz`를 보관해 두면 윈도우·리눅스·안드로이드용도 거기서 꺼내 같은 폴더에 더할 수 있다(다시 받을 필요 없음)
2. `export_presets.cfg`에 Web 프리셋, 내보내기 : `<console.exe> --headless --path . --export-release "Web" build/web/index.html`
3. **스레드 끄기(`variant/thread_support=false`)** 면 SharedArrayBuffer 없이도 돈다(별무리 사격 웹판)
4. 로컬 확인은 `file://`로 열면 안 된다. 작은 웹 서버로 띄운다(이미 쓰는 포트는 피한다. 8080은 다른 로컬 서버가 쓰는 경우가 많다. 프로젝트별 포트는 그 프로젝트의 `.claude/launch.json` 한 곳에 정해 둔다)
   - ★**웹판에는 시스템 글꼴이 없어서 한글이 네모 상자로 나온다** — PC 실행에서는 멀쩡해서 놓치기 쉽다. Noto Sans KR(OFL)을 `fonts/`에 넣고 `[gui] theme/custom_font`로 지정한다. 용량은 **쓰는 글자만 남긴 부분집합**(fonttools `subset`, 번역 표 글자 + ASCII)으로 줄인다. 별무리 사격 기준 74KB. 번역 표에 새 글자가 들어가면 부분집합을 다시 만든다(별무리 사격)
   - ★**내장 브라우저 창이 숨겨져 있으면 프레임이 초당 1~2번으로 떨어진다** — 게임이 느린 것처럼 보여도 게임 문제가 아니다. 브라우저 도구의 「hidden」 표시와 `requestAnimationFrame` 횟수로 확인한 뒤 판정한다. 속도·손맛 확인은 창을 보이게 하거나 사람이 한다. 이때 **짧게 누른 키(누름·뗌이 한 프레임 안)는 `is_action_just_pressed`에서 빠진다** — 키를 0.3초 이상 누르고 있게 보내거나(JS keydown → 대기 → keyup) 화면 버튼으로 시험한다(슈팅 시제품 웹판 Shift 교대)
   - 새 글꼴·번역 CSV는 **첫 가져오기 때 「No loader found / 열 수 없음」 에러가 나는 것이 정상**이다. 두 번째 가져오기에서 사라지면 된다

## 4-1. 스팀으로 낼 때

- 엔진 쪽 걸림돌은 없다 : MIT라 로열티 없음(라이선스 문구만 동봉), 윈도우·리눅스(스팀덱)·맥 내보내기 기본, 업적·순위표는 GodotSteam(MIT)
- 게임기(스위치·PS·엑스박스)만 포팅 업체가 필요하다
- 가입·등록비(게임당 100달러)·세금·신원 확인은 사람이 한다

## 5. 하지 않는 것

- 유료 MCP(Godot MCP Pro)·개인 배포 파일 전역 설치(GoPeak)·통계 기본 켜짐(godot-ai) — 보류 판정(2026-10-09 MCP 실측, 각 공식 저장소 확인)
- 클로드 데스크톱 채팅 앱 전역 설정에 고도 MCP 넣기 — 프로젝트 범위로만
- 지금 작업하는 게임 밖의 다른 프로젝트 폴더에 쓰기
