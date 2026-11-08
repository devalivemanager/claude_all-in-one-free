---
name: unity-pitfalls
description: Use when starting, building, testing, or exporting a Unity (유니티) 6 game project — writing C# scripts, scenes, prefabs or editor builder scripts, wiring the Unity MCP (CoplayDev MCP for Unity), using the Unity CLI, play-mode testing through MCP, or building WebGL/Android. Triggers on "유니티", "Unity", "유니티3D", "C# 스크립트", "프리팹", "UnityMCP", "MCP for Unity", "unity cli", "유니티 함정", "WebGL 빌드".
---

# 유니티 6 함정 모음 (한 장 안내서)

> MCP 시험 프로젝트(2D 플랫포머)와 연습용 러너 게임을 만들며 **실제로 겪은 것**과 영상 학습 정리본을 한 장으로 모았다.
> 각 항목 끝 괄호는 출처다. 「실측」은 작성자 PC에서 직접 확인한 것이고, 영상 정리본은 이 묶음 `999_document/02_게임개발/`에 있다.
> 새 함정이 **두 번** 나오면 여기에 올린다. 고도는 `godot-pitfalls` 스킬.

## 0. 준비물 (작성자가 확인한 판 기준)

- 에디터 : 유니티 6(`6000.0.53f1`) · 허브 3.22.2. 허브 기본 설치 위치는 `C:\Program Files\Unity\Hub\Editor\<버전>\Editor\Unity.exe`
- 빌드 모듈 : 필요한 것만(Android는 SDK·NDK·OpenJDK 포함, WebGL, Windows)
- 공식 CLI : `%USERPROFILE%\AppData\Local\Unity\bin\unity.exe`(1.0.0-beta.12, 허브 툴박스에서 설치). 허브가 `unity serve` 백그라운드 프로세스를 띄운다(에디터 아님)
- 프로젝트 : 게임마다 폴더 하나(`<게임프로젝트폴더>/<이름>/`)
- MCP : **CoplayDev 「MCP for Unity」(MIT)**, 패키지 `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`, 서버 `mcpforunityserver`(uvx), **HTTP 8888**
  - 클로드 코드 등록 : `claude mcp add --transport http --scope user UnityMCP http://127.0.0.1:8888/mcp`
  - ★**8080은 다른 로컬 서버와 자주 겹친다**. 유니티 쪽 기본값이 8080이므로 비어 있는 포트(예 : 8888)로 바꾼다
- 라이선스 : 개인(Personal). 허브 로그인 상태여야 에디터가 뜬다

## 1. 시작할 때

1. **허브 로그인 없이 에디터를 띄우면 라이선스 단계에서 죽는다** — 로그에 「Access token is unavailable」「entitlement … not found」 뒤 `Crash!!!`. 백그라운드(`-batchmode -createProject`)도 같다. 로그인은 사람이 한다(AI가 비밀번호를 대신 입력하지 않는다)(실측)
2. **CLI·에디터 설치는 공식 경로로** — 윈도우 앱 설치 명령(winget)으로 받은 CLI는 샌드박스 앱이라 설치 실패. 순서는 **에디터 먼저, 라이선스 나중**(유니티공식스킬31 영상)
3. **프로젝트를 만들면 바로 `git init` + 첫 커밋** — AI가 장면·프리팹을 고치므로 되돌릴 지점이 먼저다. `.gitignore`에 `Library/ Temp/ Logs/ UserSettings/ obj/ Builds/ *.csproj *.sln`(실측)
4. **MCP 패키지는 `Packages/manifest.json`에 한 줄** 넣고 에디터를 열면 받아진다. 처음 열 때 수 분 걸린다(실측)
5. **입력 방식 확인** — `ProjectSettings.asset`의 `activeInputHandler`(0 기존, 1 새 입력 시스템, 2 둘 다). 기존 `Input.GetKeyDown`은 0·2에서만 동작(실측 : 시험 프로젝트 0, 러너 2)
6. **`PlayerSettings.runInBackground = true`** — 안 켜면 유니티 창이 다른 창에 가려질 때 **플레이 모드가 멈춘다**. MCP 시험에서 frameCount가 그대로면 이것부터 의심(실측, 유니티공식스킬31 영상도 같은 함정)
7. **남의 게임 이름·캐릭터·그림·소리 금지**, 강의 소스 그림은 연습용으로만(연습용 러너 판정)

## 2. MCP 연결·운영 (CoplayDev)

- **설정 마법사의 「Configure」를 누르면 클로드 코드 등록이 8080·프로젝트 범위(`UnityMCP`, local)로 덮인다** — 다른 AI 앱 10곳 설정 파일에도 등록한다. 누른 뒤엔 `claude mcp list`로 확인하고 8888·사용자 범위로 되돌린다(실측)
- **포트·자동 시작은 EditorPrefs로 넣는다**(PC 전체 공용, 프로젝트마다 다시 안 해도 됨) : `MCPForUnity.UseHttpTransport=true`, `MCPForUnity.HttpTransportScope="local"`, `MCPForUnity.HttpUrl="http://localhost:8888"`, `MCPForUnity.AutoStartOnLoad=true`, `MCPForUnity.SetupCompleted=true`, `MCPForUnity.TelemetryDisabled=true`. 화면 클릭 대신 `[InitializeOnLoad]` 일회용 스크립트로 넣고 지운다(실측, 키 이름은 패키지 `Editor/Constants/EditorPrefKeys.cs`)
- **에디터를 두 개(두 프로젝트) 동시에 열지 않는다** — 둘 다 8888을 쓴다
- **세션 시작 뒤에 MCP를 등록하면 그 세션엔 도구가 안 보인다** — 새 세션을 열거나, HTTP로 직접 부른다(`tools/umcp.py`, 아래 5절)
- 에디터가 꺼져 있으면 `UnityMCP`는 연결 실패로 나온다. 정상이다
- 도구 49개(장면·게임 오브젝트·컴포넌트·스크립트·머티리얼·빌드·테스트·`execute_code`·`execute_menu_item`·`read_console`·`manage_camera` 스크린샷 등)
- **`refresh_unity` 직후 첫 호출은 「not ready」로 실패하기 쉽다** — 8초 간격으로 몇 번 재시도(실측)
- **오래 걸리는 메뉴(빌드)는 MCP 호출이 시간 초과**된다 — 결과를 파일(`Builds/build_result.txt`)에 쓰게 하고 그 파일을 기다린다(실측)
- 유니티 공식 「실시간 에디터 연결」은 구독이 필요하다고 한다. 이 스킬은 무료 CoplayDev 기준이다(유니티공식스킬31 영상)

## 3. 만들 때 (C#·장면)

- ★**장면 구성은 에디터 메뉴 스크립트(빌더)로** — `Assets/Editor/<게임>Setup.cs`에 `[MenuItem("Tools/<게임>/Setup")]`. MCP `execute_menu_item`으로 실행. **여러 번 돌려도 같은 결과**(있으면 지우고 다시 만들기)가 되게 쓴다. 클릭 수십 번보다 확실하고 다시 만들 수 있다(실측)
- ★**`TextureImporter`를 Sprite로 바꿀 때 `spriteImportMode = Single`을 같이 지정** — 안 하면 `LoadAssetAtPath<Sprite>`가 null → 그림 안 보이고 **충돌 상자 크기 0 → 바닥을 뚫고 낙하**. 스프라이트가 null이면 예외를 던져 바로 드러나게(실측)
- **충돌 상자 크기는 스프라이트에 기대지 말고 명시**(`BoxCollider2D.size = Vector2.one` 등)(실측)
- ★**유니티 객체에 `??`·`?.`를 쓰지 않는다** — 파괴됐거나 없는 컴포넌트는 「가짜 null」이라 `??`가 null로 안 본다. `if (x == null)`로 비교(실측 러너 빌더)
- ★**높이·바닥 좌표를 어림하지 말고 잰다** — 콜라이더에 오프셋이 있으면 눈대중(-4.0)과 실제(-4.41)가 다르다. `Physics2D.SyncTransforms()` 뒤 `collider.bounds`로 잰다. 플레이 중엔 애니메이션 프레임마다 그림 발끝이 달라지니 여러 번 재 본다(실측 러너 「적이 떠 있다」)
- ★**벽 달라붙기** — 방향키를 누른 채 벽에 닿으면 마찰이 중력을 버틴다. ① 플레이어에 마찰 0 `PhysicsMaterial2D` + `frictionCombine = Minimum`(평균이면 0.2가 남는다) ② 누르는 방향 옆면에 **접촉** 중이면 좌우 속도 0. `Rigidbody2D.Cast`는 이미 붙은 벽을 방향과 무관하게 잡아 반대 키로도 못 떨어진다 → `GetContacts`의 법선으로 판정(실측 시험 프로젝트)
- **떨어지면 시작 위치로 되살리기**(y가 한계 아래면)를 처음부터 넣는다(실측)
- **화면 UI(하트 등)를 고정 월드 좌표에 두면 화면 비율이 다를 때 잘린다** — 카메라 뷰포트 모서리 기준(`ViewportToWorldPoint`)으로 붙인다. 16:9·1.6:1(브라우저)·19.5:9(폰)에서 계산으로 확인(실측 러너 WebGL)
- ★**화면 가장자리 근처에 서는 물체(플레이어 등)의 x 좌표도 같다** — 16:9 기준 고정 x(-7.1)면 브라우저 1.6:1에서 캐릭터 꼬리·몸이 잘렸다. `Start`에서 화면 왼쪽 끝 + 여백으로 놓는다. 에디터 16:9에서는 안 보이고 웹 빌드에서만 드러났다(실측 다른 러너 WebGL, 하트와 같은 종류로 두 번째)
- **입력은 한 곳(`GameInput`)으로 모은다** — 스페이스·마우스 클릭·화면 탭(터치는 마우스 클릭으로도 들어옴). **시작을 누른 그 프레임에 같은 입력으로 점프하지 않게** 시작 프레임을 기록해 막는다. 사망 직후 0.5~1초 입력 무시(실측)
- **스크립트 파일 이름 = 클래스 이름** — 다르면 컴포넌트로 못 붙는다. 고칠 땐 `git mv`로 `.cs`와 `.cs.meta`를 **같이** 옮겨 GUID를 유지(장면 참조 유지)(실측 `BackgroudScroll`)
- **직렬화 필드 이름을 바꾸면 인스펙터 연결이 끊긴다** — `[FormerlySerializedAs("옛이름")]`(실측)
- **애니메이터 파라미터 이름은 컨트롤러에 실제로 있는 이름**(대소문자 포함)으로(실측 `state`)
- **점수 글자는 기본 `Text`로도 충분** — TMP는 Essentials 임포트가 필요하다. 기본 글꼴은 `Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf")`(실측)
- **텍스처 Quad 스크롤 속도는 「월드 속도 × 타일링 / 폭」**으로 UV에 넣어야 바닥과 물체 속도가 맞는다(실측)
- **에디터에서 채운 값이 플레이 때 비는 경우**(색·참조) — 런타임 생성 오브젝트는 코드에서 다시 채운다(유니티공식스킬31 영상)
- **엔진을 옮길 때 앞 방향(축)이 반대**일 수 있다 — 검사는 값이 정상이라 못 잡고 화면으로만 보인다(고도→유니티 전환 영상)

## 4. 시험할 때 (MCP)

- **플레이 모드 시험은 `execute_code`로 상태를 읽는다** — 예 : `"y="+p.transform.position.y+" f="+Time.frameCount`. **frameCount가 안 늘면 시험 무효**(창 가림)
- **사람 입력은 흉내 낼 수 없다** → 시험용 훅을 둔다(`GameInput.Simulate()`. **바로 다음 프레임 한 번만** 유효하게 한다. 쌓아 두면 처리 안 된 누름이 나중에 터져 결과가 오염된다)(실측)
- **충돌 규칙 시험은 스포너를 끄고** 프리팹을 플레이어 위치에 하나씩 만들어 본다 — 자연 생성 적이 섞이면 「한 번에 하트 2개」 같은 가짜 버그가 보인다(실측)
- **사용자가 직접 플레이 중이면 자동 시험이 오염된다** — 시험 전에 「1~2분 손대지 말아 주세요」(실측)
- **스크린샷은 `manage_camera` `action=screenshot`** → `Assets/Screenshots/*.png`. 직접 열어 「볼 곳」을 예/아니오로 판정
- 원인 모르는 버그는 **고치기 전에 값부터 잰다**(스프라이트 null·콜라이더 크기·바닥 좌표가 모두 그렇게 잡혔다)

## 5. 도구 (이 폴더의 `tools/`)

세션에 `UnityMCP` 도구가 안 보일 때(세션을 연 뒤에 MCP를 등록한 경우 등) 유니티 MCP 서버를 HTTP로 직접 부르는 작은 도구 두 개다. 에디터가 켜져 있고 서버가 `http://127.0.0.1:8888/mcp`에서 돌아야 한다. 다른 포트를 쓰면 `umcp.py` 맨 위 `U = ...` 주소를 바꾼다. Python 3 표준 라이브러리만 쓴다.

- `python tools/umcp.py <도구이름> '<json 인자>'` — 예 : `python tools/umcp.py read_console '{"action":"get","types":["error"],"count":10}'`
- `. ./tools/kx.sh` 후 `kx '<C# 코드>'` — `execute_code` 결과만 출력한다(bash 필요, Windows는 Git Bash). 예 : `kx 'return UnityEngine.Time.frameCount.ToString();'`
- 자주 쓰는 도구 : `refresh_unity`(재컴파일, 직후 첫 호출은 재시도), `execute_menu_item`, `manage_editor`(play/stop), `manage_camera`(screenshot), `read_console`
- Windows 콘솔이 cp949라 한글·특수문자 출력은 `PYTHONIOENCODING=utf-8`
- 연결이 안 되면 먼저 에디터가 켜져 있는지, 포트가 맞는지 본다. 에디터가 꺼져 있으면 연결 실패가 정상이다
- 유니티 공식 스킬 31개를 한국어로 정리한 표는 이 폴더의 `유니티공식스킬_치트시트.md`에 있다

## 6. 빌드

- **WebGL** : 첫 빌드 약 20분(실측 57MB). 로컬 파이썬 서버로 열려면 압축 끔(`WebGLCompressionFormat.Disabled`). 로컬 확인 포트는 8080·8888 피해서
- **Android** : 첫 빌드 약 20분, APK 31.9MB(arm64). **빌드 보고서 `totalSize`(686MB)는 중간 산출물 합계라 APK 크기가 아니다** — 파일 크기를 직접 잰다. 시험용은 `buildAppBundle=false`(apk), 스토어용은 aab
- 「빌드 성공」 표시만으로 완료가 아니다. **실행해 봐야 한다**(유니티공식스킬31 영상 : 빌드 성공 후 실행 즉시 종료 미해결)
- 빌드 결과(`Builds/`)는 깃에 넣지 않는다

## 7. 비용·라이선스

- 유니티 개인용 무료 조건 : 연 매출+투자 합계 약 2억 9천만 원 미만(유니티공식스킬31 영상, 공식 약관으로 재확인할 것 `[확인 못 함]`)
- 무료 3D 에셋(KayKit·Quaternius 등)은 라이선스 원문을 받아 `LICENSES.md`에 기록(영상은 「조건 없이」라고만 함)
- 엔진 고르기(작성자 판단) : **작은 2D 모바일 게임은 고도가 가볍다**, 유니티는 3D·연출·광고 SDK가 필요할 때. 같은 작은 2D 게임을 두 엔진으로 하루씩 만들어 비교한 뒤 정한다(`999_document/02_게임개발/게임개발_핵심정리.md`)
