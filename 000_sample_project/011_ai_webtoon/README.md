# 011_ai_webtoon — 대본으로 세로 스크롤 웹툰 만들기

회차 대본(JSON) 하나로 세로 스크롤 웹툰 페이지(`index.html`)를 만드는 교육용 CLI입니다.
그림은 기본적으로 **코드로 그린 캐릭터**(SVG)를 쓰고, 원하면 **이미지 생성 AI**를 연결할 수 있습니다.
어느 쪽이든 대사와 말풍선은 그림 위에 코드로 얹습니다.

> 예제 회차 「금요일 오후 6시의 1원」은 이 저장소를 위해 새로 쓴 오리지널 이야기입니다.
> 8장(`001_hr_payroll`)의 장기요양보험료 중간 절사(과세 대상액 1,000,050원 → 4,590원) 이야기를 이어받았습니다.

## 왜 이렇게 나눴나

| 일 | 맡는 쪽 | 이유 |
|---|---|---|
| 줄거리·콘티·대사 | 사람 + 클로드 | 글 작업은 클로드가 잘하고, 대본 JSON 으로 남기면 고치기 쉽다 |
| 캐릭터 일관성 | 설정표(`characters`) | 코드 그림은 같은 설정표면 항상 같은 얼굴. 이미지 AI 에는 외모 설명(`desc`)을 매 컷 **글자 그대로** 넣는다 |
| 그림 | 코드(SVG) 또는 이미지 AI | 이미지 AI 는 바꿔 끼울 수 있게 어댑터로 분리 |
| 대사·말풍선 | 코드 | 이미지 AI 는 그림 속 한글을 자주 틀리게 그린다. 프롬프트에 「글자·말풍선 넣지 않기」를 항상 붙인다 |

## 기술 스택

- Node.js 22 (외부 의존성 없음)
- 테스트: `node:test` 50개 (브라우저 테스트 2개는 Playwright 가 있을 때만)
- PNG 저장(`--png`)과 브라우저 테스트: Playwright (전역 설치본 사용, 없으면 해당 기능만 안내 후 건너뜀)

## 폴더 구조

```
011_ai_webtoon/
├── episodes/ep01.json   # 예제 회차 대본(컷 6개, 말풍선 8개)
├── src/
│   ├── cli.mjs          # 실행 진입점
│   ├── script.mjs       # 대본 읽기·검증(오류를 경로와 함께 한 번에 모아 알림)
│   ├── text.mjs         # 한글 글자 폭 추정·줄 나누기
│   ├── layout.mjs       # 말풍선 배치(화자 위, 읽는 순서, 겹침 없음)
│   ├── characters.mjs   # 설정표로 캐릭터·배경 그리기
│   ├── prompt.mjs       # 컷별 이미지 AI 프롬프트
│   ├── painters.mjs     # 그림 도구: svg(기본) / api(이미지 AI)
│   ├── render.mjs       # 컷 SVG·회차 HTML 만들기
│   └── browser.mjs      # Playwright 불러오기
└── tests/               # 단위·CLI·브라우저 테스트
```

## 실행 방법

```bash
cd 000_sample_project/011_ai_webtoon
npm run build          # output/ep01/index.html, prompts.md
npm run build:png      # 위 + output/ep01/webtoon.png (Playwright 필요)

# 직접 실행
node src/cli.mjs episodes/ep01.json -o output/ep01 [--png] [--painter svg|api]
```

출력 예시:

```
완료: .../output/ep01/index.html
컷 6개, 말풍선 8개, 경고 0건, webtoon.png 저장
```

| 파일 | 내용 |
|---|---|
| `index.html` | 세로 스크롤 웹툰. 컷마다 장면 설명이 대체 텍스트(`aria-label`)로 붙는다 |
| `prompts.md` | 컷별 이미지 AI 프롬프트. 다른 그림 도구에 붙여 넣어 쓸 수도 있다 |
| `webtoon.png` | `--png` 를 주면 페이지 전체 캡처 |

종료 코드: 정상 0, 대본·배치·파일 오류 1, 잘못된 인자 2.

## 대본 형식 (요약)

```json
{
  "title": "금요일 오후 6시의 1원", "episode": 1, "width": 720,
  "style": "굵기가 일정한 깔끔한 선, 밝은 파스텔 색감 ...",
  "characters": {
    "hana": { "name": "한나", "desc": "짧은 갈색 단발에 둥근 안경 ...",
              "look": { "hair": "#6b4a3a", "hairStyle": "short", "skin": "#f3d6bd", "shirt": "#4f86c6", "glasses": true } }
  },
  "panels": [
    { "id": "p1", "height": 480, "background": "office", "caption": "금요일 오후 5시 50분",
      "scene": "사무실, 한나가 자리에서 두 팔을 들고 기뻐한다",
      "cast": [{ "who": "hana", "x": 0.5, "expression": "happy" }],
      "lines": [{ "who": "hana", "text": "급여 계산 API, 테스트 48개 전부 통과!" }] }
  ]
}
```

| 항목 | 규칙 |
|---|---|
| `width` | 360~1080 |
| `style` | 그림 분위기. 특정 작가·작품의 **화풍·그림체를 흉내 내라는 지시는 거부**(선·색감·분위기로 적는다) |
| `characters.*.look` | 색은 `#RRGGBB`, `hairStyle` 은 `short`·`long`·`bun`, `glasses` 는 선택 |
| `panels[].height` | 240~1600 |
| `panels[].background` | `office`·`night`·`monitor`·`plain` |
| `panels[].cast[].x` | 0.1~0.9 (가로 위치 비율), `expression` 은 `neutral`·`happy`·`sad`·`surprised`·`tired` |
| `panels[].lines[]` | 말하는 사람은 그 컷의 `cast` 에 있어야 한다. 대사 하나는 60자까지 |

## 말풍선 규칙

- 화자 쪽에 놓고, 대사 순서대로 위에서 아래로 쌓는다. 그래서 겹치지 않는다.
- 모든 말풍선은 그 컷 인물의 머리보다 위에 있어야 한다. 자리가 모자라면 어느 컷인지, 몇 px 가 필요한지 알려 주고 멈춘다.
- 같은 사람이 연달아 말하면 마지막 말풍선에만 꼬리를 단다.
- 글자 폭은 추정값(한글 1, 영숫자 0.55, 공백 0.3 배)이다. 실제 글꼴로 그렸을 때 넘치지 않는지는 브라우저 테스트가 확인한다.

## 이미지 AI 연결 (`--painter api`)

서비스마다 요청 형식이 달라서, 이 샘플은 아래의 단순한 형식만 정해 둡니다. 실제 서비스에 붙일 때는 이 형식으로 바꿔 주는 작은 중계 함수(또는 서버)를 만드세요.

```
요청: POST IMAGE_API_URL
      Authorization: Bearer IMAGE_API_KEY
      { "prompt": "...", "width": 720, "height": 480 }
응답: { "imageBase64": "...", "mimeType": "image/png" }
```

```bash
export IMAGE_API_URL=...   # 키·주소는 환경변수로만. 파일·코드에 쓰지 않는다
export IMAGE_API_KEY=...
node src/cli.mjs episodes/ep01.json -o output/ep01 --painter api
```

- 그림을 받지 못한 컷은 코드 그림으로 대신하고 `경고:` 로 알립니다. 조용히 넘어가지 않습니다.
- 응답에 이미지가 없거나 `image/png`·`image/jpeg`·`image/webp` 가 아니면 실패로 봅니다.

## 테스트

```bash
npm test     # 50개
```

- `script`: 대본 검증(없는 인물, 컷에 없는 화자, 중복 id, 색·표정, 대사 길이 경계 60/61자, 화풍 흉내 거부)
- `text`·`layout`: 줄 나누기, 말풍선이 컷 안·머리 위·겹침 없음·읽는 순서, 연속 대사 꼬리, 넘칠 때 오류
- `characters`·`prompt`: 같은 입력이면 같은 그림, 앞머리를 얼굴보다 나중에 그리기, 외모 설명을 매 컷 그대로, 글자 금지 규칙
- `render`: 대사·제목의 HTML 이스케이프(XSS), 컷 순서, 대체 텍스트, 이미지 API 성공·실패·잘못된 응답
- `cli`: 인자, 종료 코드, 예제 회차 생성
- `browser`(Playwright): 실제 글꼴로 그린 대사가 모두 말풍선 안에 있는지

## 주의

- 특정 작가나 기존 웹툰의 화풍·캐릭터를 흉내 내지 마세요. 대본 검증이 흔한 표현(「화풍」, 「그림체」, "style of")을 막지만 모든 경우를 막지는 못합니다.
- 이미지 AI 로 만든 그림을 판매하려면 그 서비스의 상업 이용 조건을 먼저 확인하세요.
- `output/` 은 다시 만들 수 있는 결과물이라 커밋하지 않습니다.

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
