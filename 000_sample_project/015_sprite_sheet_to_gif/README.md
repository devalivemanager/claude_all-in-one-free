# 015_sprite_sheet_to_gif — 스프라이트 시트 → 무한 루프 GIF 변환기(클로드 코드 단독 실행형)

> 🥒 **DevAlive × Pickle**: 클로드 코드(Claude Code) 무인 스프라이트 GIF 파이프라인

클로드 코드 터미널에서 「도트 캐릭터 걷는 모션 6프레임 GIF 만들어줘」 한 마디면 끝까지 만들어 주는 도구다.
클로드 코드가 **프레임을 직접 설계**(외부 API 없는 PIL 절차적 픽셀 아트)하고, 이 패키지가 슬라이싱·조립·최적화를 해 **1초 안에 최적화된 무한 루프 GIF**를 내고, 필요하면 **이미지 생성 API 로 뽑은 스프라이트 시트**도 같은 관로로 받아 돌린다.

도트를 넘어 **SVG 기반 벡터 모션 엔진**(`--mode vector`)도 탑재됐다. 베지어 곡선과 삼각함수로 프레임을 「식」으로 적어 수학적으로 생성하고, 고해상도로 래스터화한 뒤 줄여(수퍼샘플링) **아무리 확대해도 선이 깨지지 않는 칼선 루프 GIF**를 내며, 이것도 외부 API·무거운 툴(Cairo 등) 없이 순수 파이썬 + Pillow 로 돈다.

> 설계 원칙 :
> - **움짤 만들기가 외부 화면에 의존하지 않는다.** 이 도구는 클로드 코드만으로 프레임 생성→GIF 조립까지 끝낸다. 이미지 생성 API 는 `sources.py` 의 갈아 끼울 자리로만 존재한다(키는 환경변수, 네트워크 부분은 주입식이라 시험이 네트워크 없이 돈다).
> - **프레임은 결정론적으로 찍힌다.** 같은 인자면 언제나 같은 그림이므로 재현·검수·비교가 공짜다.
> - **GIF 는 항상 무한 루프(loop=0)이고 프레임 수를 코드로 검증한다.** 「완료했습니다」를 믿지 않고 검증 장치로 막는 것이 이 저장소의 규칙이다.

## 기술 스택

- Python 3.10 이상, **Pillow 한 가지**(`pip install pillow`)
- 테스트: `unittest`(원하는 경우 `pytest` 로도 돈다)

## 폴더 구조

```
015_sprite_sheet_to_gif/
├── sprite_to_gif/
│   ├── __init__.py        # 공개 API 모음
│   ├── converter.py       # 시트 슬라이싱·GIF 조립(속도·트리밍·팔레트 최적화)
│   ├── generator.py       # 절차적 도트 프레임 생성(walk·wave·pulse·bounce)
│   ├── vector_generator.py # SVG 벡터 모션 엔진(베지어 프리셋 4종, 루프 이음새 수학 보장)
│   ├── sources.py         # 프레임 공급원: 절차 생성(기본) + 이미지 생성 API 연결부
│   └── cli.py             # 한 줄 배치 러너(python -m sprite_to_gif.cli …)
├── tests/                 # 시험(네트워크·외부 도구 없이 돈다)
└── (실행하면 생김, 커밋하지 않음) output/, assets/gif/
```

## 실행 방법

```bash
cd 000_sample_project/015_sprite_sheet_to_gif
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 또는 시스템 pip

# 클로드 코드가 "걷는 모션 GIF 만들어줘"를 받았을 때 도는 한 줄(외부 연결 0)
python -m sprite_to_gif.cli generate --motion walk --fps 3 \
    --save-sheet output/walk_sheet.png --output output/walk.gif

# 챗GPT 등에서 받아 온 3x2 스프라이트 시트를 GIF 로 (수동 다운로드 시트 포함)
python -m sprite_to_gif.cli convert --input assets/sheets/bamjigi_sheet.png \
    --fps 3 --speed 0.5 --output output/bamjigi_slow.gif

# 폴더의 시트 전부 일괄 변환(실패는 모아 보고하고 계속 진행)
python -m sprite_to_gif.cli batch --input-dir assets/sheets --output-dir assets/gif

# 🔻 벡터 모션: 밤지기 흑등 랜턴 — 흔들림·불꽃 일렁임·빛 번짐 칼선 루프
python -m sprite_to_gif.cli --mode vector --preset lantern --size 256 --output lantern_loop.gif

# 벡터: SF 조준선(회전 눈금 + 맥동 링) / 에너지 파동 / 회전 엠블럼
python -m sprite_to_gif.cli --mode vector --preset crosshair   --size 256 --output crosshair_loop.gif
python -m sprite_to_gif.cli --mode vector --preset pulse_ring  --size 256 --output pulse_loop.gif
python -m sprite_to_gif.cli --mode vector --preset spin_emblem --size 256 --output emblem_loop.gif
```

- `generate` 의 모션: `walk`(걷기)·`wave`(손 흔들기)·`pulse`(등불 빛 반짝임)·`bounce`(공 튀기기)
- `--mode vector` 의 프리셋 4종:
  - `lantern` — 밤지기 흑등: 바람에 부드럽게 흔들리는 랜턴 바디 + 일렁이는 불꽃 베지어 패스 + 빛 번짐 오라
  - `crosshair` — 로블록스/SF 조준선: 360도 부드럽게 회전하는 정밀 눈금선 + 중심부 맥동(Pulse) 링
  - `pulse_ring` — 에너지 게이지/비콘: 동심원 형태로 부드럽게 퍼져 나가는 벡터 파동
  - `spin_emblem` — 데브얼라이브/문양: 회전하는 기하학적 엠블럼 심볼
- 벡터 프리셋의 기본 프레임 수는 `lantern`·`crosshair` 12, `pulse_ring` 8, `spin_emblem` 6 장이고 `--frames` 로 바꿀 수 있다(3x2 시트용 6프레임 포함). 모든 움직임이 phase 의 주기함수라 **첫 프레임과 끝 프레임이 수학적으로 이어지는 완벽한 무한 루프**다(시험이 phase 1.0 = phase 0.0 을 코드로 검증한다).
- `--speed 0.25~2.0` 은 재생 속도 배수(0.5 = 두 배 느리게), `--colors` 는 팔레트 색 수(용량 다이어트)
- `--save-sheet` 로 시트 PNG 를 함께 남기면 원본 보존·검수·재변환(속도만 바꿔 재생성)이 공짜가 된다
- 이미지 생성 API 로 시트를 뽑으려면 `sprite_to_gif.sources.frames_from_api` 를 쓴다 — `OPENAI_API_KEY` 환경변수가 필요하고, 프롬프트에는 가이드 부록의 ⌊고정 문구 6조각⌋을 그대로 쓴다

## 시험 방법

```bash
python3 -m unittest discover -s tests -t .          # 폴더 안에서
# 또는
python3 -m pytest -q
```

시험은 슬라이싱 순서(왼쪽→오른쪽·위→아래)·트리밍 보정·속도 계산(0.25~2배·최소값 눌러 주기)·6프레임 GIF 생성·무한 루프(loop=0)·투명 배경 보존·모션 4종의 결정론과 프레임 구별성(중복 프레임 병합 방지)·시트 왕복·CLI 세 가지 명령에 더해, 벡터 엔진의 프리셋 4종 생성·6/8/12프레임 루프·phase 이음새(1.0 = 0.0)·GIF 저장·CLI 벡터 모드·투명 배경 깜빡임 재발 방지(모든 프리셋 GIF 를 프레임마다 RGBA 로 풀어 모서리와 원본 투명 자리가 모든 프레임에서 투명인지, 프레임들이 같은 투명색 번호를 쓰는지)까지 본다. 시험은 모두 53개다.

## 10대 운영 수칙 중 이 패키지가 직접 지키는 것

1. **시트 원본은 읽기만 하고, 산출물은 `--output` 경로로만 나온다.** `--save-sheet` 로 원본 보존을 습관화한다.
2. **비밀값 없음.** API 키는 환경변수에서만 읽고 코드·산출물에 남지 않는다. 키 없이도 절차 생성으로 전부 돈다.
3. **검증은 사람 눈이 아니라 코드로.** GIF 저장 뒤 프레임 수·loop=0 확인이 시험에 박혀 있다.
4. **투명 GIF 는 disposal=2 로 잔상을 막고, 팔레트 양자화로 용량을 깎는다.**
   투명색은 모든 프레임이 같은 팔레트 번호(255)를 쓴다. 프레임마다 번호가 달라지면 저장기가 첫 프레임 번호만 써서 투명 자리가 검은 사각형으로 깜빡였다(2026-11-06 `lantern` 실측 결함, 고침).

## 클로드 코드와 이어 붙이기

1. 「도트 캐릭터 걷는 모션 6프레임 GIF 만들어줘」 → 클로드 코드가 위 CLI 한 줄로 만들어 준다.
2. 캐릭터가 마음에 들면 `PixelSpec` 의 색·크기를 바꿔 파생물을 찍어 내고(재생성 비용 0원), 시트는 게임 에셋 후보로 남긴다.
3. 이미지 생성 AI 로 그린 시트는 `convert` 로 받아 들여 같은 후처리(속도·용량 최적화)를 태운다.

가이드 전문(PROMPT-0/1/2, 10대 수칙, 챗GPT 프롬프트 부록)은 발송 문서 `documents/devalive_claude_code_chatgpt_gif_pipeline_guide.md` 를 본다.

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
