# 009. 스크롤 영상 히어로 (스크롤 스크러빙)

영상 하나를 프레임 이미지로 쪼갠 뒤, **스크롤 위치에 맞춰 재생·역재생**하는 랜딩 페이지 히어로 섹션 샘플입니다.
애플 제품 페이지처럼 아래로 스크롤하면 영상이 앞으로, 위로 스크롤하면 뒤로 감깁니다.

유튜브 등에서 많이 소개되는 GSAP ScrollTrigger 방식을 **외부 라이브러리 없이** 순수 JavaScript 로 구현했습니다.
런타임 의존성은 0개이며, 영상 처리에는 시스템에 설치된 `ffmpeg` 를 사용합니다.

## 개요

| 구성 | 설명 |
| --- | --- |
| 프레임 추출 | `ffmpeg` 로 영상을 `f_0001.jpg …` 와 `manifest.json` 으로 변환 |
| 데모 영상 | `ffmpeg` 의 lavfi 필터로 "점들이 가운데로 모이는" 저작권 없는 6초 영상 생성 |
| 히어로 | sticky 캔버스 + 스크롤 진행률 → 프레임 번호 → 캔버스에 그리기 |
| 개발 서버 | `node:http` 로 직접 만든 정적 파일 서버 |

## 동작 원리

```
.hero (높이 400vh)
└─ .hero__sticky (position: sticky, 높이 100vh)  ← 스크롤하는 동안 화면에 붙어 있음
   └─ <canvas>                                     ← 여기에 현재 프레임을 그림
```

1. **긴 섹션 + sticky**: 히어로 섹션은 화면 4개 높이(400vh)이고, 안쪽 영역은 `position: sticky` 로 화면에 고정됩니다.
   그래서 화면 3개 분량(400vh - 100vh)을 스크롤하는 동안 히어로가 화면에 머뭅니다.
2. **진행률 계산**: `getBoundingClientRect().top` 으로 섹션이 얼마나 올라갔는지 보고 0~1 의 진행률로 바꿉니다.
   (`progressFromRect`)
3. **프레임 번호 매핑**: 진행률 × (프레임 수 - 1) 을 반올림해 프레임 번호를 얻습니다. (`progressToFrameIndex`)
4. **requestAnimationFrame**: 스크롤 이벤트는 매우 자주 발생하므로, 이벤트에서는 그리기를 "예약"만 하고
   실제 그리기는 rAF 콜백에서 화면 갱신당 한 번만 합니다. 프레임 번호가 바뀌지 않았으면 다시 그리지 않습니다.
5. **cover 그리기**: 화면 비율과 영상 비율이 달라도 CSS `object-fit: cover` 처럼 꽉 채우고 넘치는 부분은 자릅니다.
   (`coverRect`) 캔버스 해상도는 기기 픽셀 비율(최대 2)을 반영합니다.
6. **프리로드**: 시작할 때 모든 프레임 이미지를 미리 받아 두고, 로딩 진행률(`12 / 90`)을 표시합니다.
   영상 디코딩 대신 이미 받아 둔 이미지를 그리기 때문에 역방향 스크롤도 끊김 없이 동작합니다.
7. **접근성**: `prefers-reduced-motion: reduce` 이면 첫 프레임만 받아서 고정하고, 긴 스크롤 구간도 없앱니다.
8. **모바일**: 주소창 높이 변화에 흔들리지 않도록 `100svh` 를 쓰고, 스크롤 거리를 300vh 로 줄였습니다.

> 왜 `<video>` 의 `currentTime` 을 바꾸지 않나요?
> 브라우저는 키프레임 단위로 탐색하기 때문에 `currentTime` 을 빠르게 바꾸면 버벅이거나 역방향이 매우 느립니다.
> 이미지 시퀀스 방식은 용량이 커지는 대신 어느 방향으로든 즉시 원하는 프레임을 그릴 수 있습니다.

## 기술 스택

- 브라우저: HTML, CSS(sticky, svh, media query), 순수 JavaScript(ES Module, Canvas 2D, requestAnimationFrame)
- 도구: Node.js 22 이상, ffmpeg / ffprobe
- 테스트: `node:test`(내장), Playwright(E2E, 선택)

## 폴더 구조

```
009_scroll_video_hero/
├── public/
│   ├── index.html          # 히어로 + 가상의 회사 소개 섹션
│   ├── style.css           # sticky 레이아웃, 로딩 표시, 모바일·움직임 줄이기 대응
│   ├── hero.js             # 프리로드, 스크롤 → rAF → 캔버스 그리기
│   ├── scrub.js            # 순수 계산 함수 (진행률, 프레임 번호, cover 사각형)
│   └── frames/             # (생성됨) f_0001.jpg … + manifest.json
├── scripts/
│   ├── extract-frames.mjs  # 영상 → 프레임 이미지 + manifest.json
│   └── make-demo-video.mjs # ffmpeg 로 데모 영상 생성
├── test/
│   ├── scrub.test.mjs          # 순수 함수 단위 테스트
│   ├── extract-frames.test.mjs # 실제 ffmpeg 추출 + manifest 검증
│   ├── server.test.mjs         # 정적 서버 테스트
│   ├── e2e.test.mjs            # Playwright 브라우저 테스트
│   └── helpers.mjs             # 테스트용 짧은 영상 만들기
├── server.mjs              # 의존성 없는 정적 파일 서버
└── package.json
```

## 사용법

먼저 ffmpeg 가 필요합니다. (`ffmpeg -version` 으로 확인)

```bash
# macOS: brew install ffmpeg / Ubuntu: sudo apt install ffmpeg / Windows: winget install ffmpeg

# 1) 데모 영상(demo.mp4)을 만들고 프레임을 추출 (20초 정도 걸림)
npm run demo

# 2) 개발 서버 실행 후 http://localhost:3000 접속
npm start
# 포트 변경: PORT=8080 npm start
```

### 내 영상으로 바꾸기

```bash
node scripts/extract-frames.mjs my-video.mp4 --fps 15 --width 1280
# 또는: npm run extract -- my-video.mp4 --fps 12 --width 960
```

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--fps` | 15 | 초당 몇 장을 뽑을지. 높을수록 부드럽지만 이미지 수와 용량이 늘어남 |
| `--width` | 1280 | 프레임 너비(짝수). 높이는 비율에 맞춰 자동 계산 |
| `--out` | `public/frames` | 출력 폴더 |

결과로 `public/frames/f_0001.jpg …` 와 `manifest.json`(`{ count, width, height, fps }`)이 만들어지며,
다시 실행하면 이전 프레임은 지우고 새로 만듭니다.

> 팁: 10초 영상을 15fps 로 뽑으면 150장입니다. 모바일 데이터 사용량을 생각해 3~8초, 960~1280px 정도를 권장합니다.

## 테스트 방법

```bash
npm test
```

| 파일 | 내용 |
| --- | --- |
| `scrub.test.mjs` | 진행률 계산, 프레임 번호 매핑(경계값, 단조 증가), 파일 이름, cover 사각형 |
| `extract-frames.test.mjs` | 인자 해석, ffmpeg 가 없을 때 안내, 실제 영상으로 추출해 manifest·파일 수 검증 |
| `server.test.mjs` | index.html·MIME 타입, 404, `../` 경로 차단 |
| `e2e.test.mjs` | 브라우저에서 스크롤 0 → 중간 → 끝 → 다시 위로 이동하며 그려진 프레임 번호가 증가·감소하는지, 콘솔 에러 0, 움직임 줄이기, 모바일 화면 |

E2E 테스트는 `public` 을 임시 폴더로 복사하고 테스트용 프레임을 만들어 쓰므로 `public/frames` 를 건드리지 않습니다.

### Playwright 설치 (E2E 테스트용, 선택)

Playwright 는 `package.json` 에 넣지 않았습니다. 설치되어 있지 않으면 E2E 테스트는 자동으로 건너뜁니다(skip).
실행하려면 다음과 같이 설치하세요.

```bash
npm i -D playwright && npx playwright install chromium
```

ffmpeg 가 없으면 추출 테스트와 E2E 테스트도 건너뜁니다.

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
