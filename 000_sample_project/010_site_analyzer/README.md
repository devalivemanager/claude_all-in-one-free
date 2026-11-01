# 010_site_analyzer — 웹사이트 구조·디자인 분석 보고서 만들기

"웹사이트를 통째로 복제한다"는 영상에서 아이디어를 얻었지만, 이 도구는 **복제하지 않습니다.**
문구·이미지·로고를 내려받는 대신 웹사이트의 **구조, 기술 스택 단서, 디자인 특징**을 살펴보고
한글 보고서(`report.md`)와 데이터(`report.json`)로 정리합니다.
내 사이트를 점검하거나, 허락받은 사이트가 어떻게 만들어졌는지 공부할 때 씁니다.

## 동작 흐름

```
URL ──▶ robots.txt 확인 ──(금지 경로면 즉시 종료)
          │
          ▼
   Playwright(Chromium)로 같은 출처 페이지를 너비 우선(BFS)으로 최대 N개 방문
   (요청마다 User-Agent 에 SiteAnalyzer 표시, 페이지 사이 1초 간격)
          │
          ▼
   페이지별 수집: 제목 구조·랜드마크·요소 개수·alt 누락·글꼴·색상·@media 브레이크포인트
                 ·애니메이션 단서·기술 스택 단서·네트워크 요청·API 호출·로드 시간
   + 데스크톱(1280)·태블릿(768)·모바일(390) 전체 화면 스크린샷
          │
          ▼
   output/report.md  (사이트 요약 + "다시 만들 때 참고할 점" 체크리스트 + 페이지별 섹션)
   output/report.json
```

## 윤리·법적 주의

- **내 사이트나 운영자에게 허락받은 사이트에만 사용하세요.** 이용약관이 자동 수집을 금지하는 사이트에는 쓰지 마세요.
- robots.txt 를 항상 따릅니다. 무시하는 옵션은 일부러 만들지 않았습니다.
  - 시작 URL 이 금지되어 있으면 페이지를 하나도 열지 않고 종료합니다(종료 코드 2).
  - 따라가던 링크가 금지 경로면 요청하지 않고 "건너뛴 페이지"에 기록합니다.
  - robots.txt 가 없으면(4xx) 제한 없음으로, 서버 오류(5xx)·연결 실패면 안전하게 "전부 금지"로 봅니다.
- 요청마다 User-Agent 에 `SiteAnalyzer/1.0.0 (educational site research tool; no content copying)` 을 밝힙니다.
- 페이지 사이에 기본 1초(최소 0.5초) 간격을 두고, 최대 50페이지까지만 방문합니다. 화면 크기를 바꿔 스크린샷을 찍을 때도 페이지를 다시 불러오지 않습니다.
- 다른 출처(도메인·포트·프로토콜이 다른 곳)의 페이지는 방문하지 않고, 다른 출처 스타일시트도 읽지 않습니다.
- 스크린샷은 분석 자료일 뿐입니다. 결과물(`output/`)은 다른 사람의 저작물을 담고 있으므로 커밋·배포하지 마세요(`.gitignore` 에 포함).
- 보고서의 색상·글꼴·레이아웃은 "어떻게 설계되었는지" 배우기 위한 참고 자료입니다. 새로 만들 때는 자기 브랜드와 콘텐츠로 만드세요.
- 로그인이 필요한 페이지, 개인 정보가 보이는 페이지는 분석하지 마세요. API 호출 목록에서는 쿼리 문자열(토큰 등이 들어 있을 수 있음)을 빼고 경로만 남깁니다.

## 기술 스택

- Node.js 22, ES 모듈(JavaScript `.mjs`)
- [Playwright](https://playwright.dev/) (Chromium): 페이지 열기, 계산된 스타일 읽기, 네트워크 기록, 스크린샷
- `node:test` — 단위 테스트 + 로컬 픽스처 사이트를 쓰는 통합 테스트 (외부 네트워크 불필요)
- 외부 npm 의존성 없음 (playwright 는 아래 설치 안내 참고)

## 폴더 구조

```
010_site_analyzer/
├── src/
│   ├── cli.mjs           # 진입점: 인자 처리, 결과 안내, 종료 코드
│   ├── args.mjs          # 명령행 인자 해석·검증
│   ├── config.mjs        # 도구 이름, User-Agent, 화면 크기, 기본값
│   ├── crawler.mjs       # robots 확인 → BFS 방문 → 페이지 분석 → 보고서 저장
│   ├── page-scripts.mjs  # 브라우저 안에서 실행되는 수집 함수
│   ├── robots.mjs        # robots.txt 파싱·허용 판정·가져오기
│   ├── url-utils.mjs     # URL 정규화, 같은 출처·방문 범위 판정
│   ├── style-utils.mjs   # 색상·글꼴 집계, @media 브레이크포인트 파싱
│   ├── analysis.mjs      # 기술 스택 단서, 네트워크 요약, API 목록
│   ├── report.mjs        # 사이트 요약, 체크리스트, Markdown 렌더링
│   └── browser.mjs       # playwright 불러오기(없으면 안내)
├── tests/
│   ├── *.test.mjs        # 단위·통합·CLI 테스트
│   ├── helpers/          # 픽스처 서버, 테스트용 샘플 데이터
│   └── fixtures/site/    # 한글 테스트용 정적 사이트(꽃집, 3페이지 + 금지된 /private/)
├── package.json
└── package-lock.json
```

## 설치

이 저장소의 실습 환경에는 playwright 와 Chromium 이 이미 전역으로 설치되어 있어 따로 설치할 것이 없습니다.
(브라우저 버전이 어긋나지 않도록 `package.json` 에는 playwright 를 넣지 않았습니다.)

다른 환경에서는 이 폴더에서 한 번만 설치하세요.

```bash
cd 000_sample_project/010_site_analyzer
npm i playwright && npx playwright install chromium
```

playwright 를 찾지 못하면 CLI 는 위 안내를 출력하고 종료(종료 코드 3)하며, 브라우저가 필요한 테스트는 건너뜁니다.

## 사용법

```bash
node src/cli.mjs <URL> [--out output] [--max-pages 5] [--same-origin] [--delay 1000]
```

| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `--out` | 결과 폴더 | `output` |
| `--max-pages` | 최대 방문 페이지 수(1~50) | `5` |
| `--same-origin` | 방문 범위를 **같은 출처 전체**로 넓힙니다. 없으면 시작 URL 의 경로 아래만 방문합니다(예: `/docs/` 에서 시작하면 `/docs/...` 만). 다른 출처는 어느 경우에도 방문하지 않습니다. | 꺼짐 |
| `--delay` | 페이지 사이 간격(ms, 500 이상) | `1000` |

종료 코드: `0` 성공, `1` 오류(분석한 페이지 없음 포함), `2` robots.txt 금지, `3` playwright 없음.

### 직접 해 보기 (로컬 테스트 사이트)

```bash
# 터미널 1: 테스트용 꽃집 사이트 띄우기
npm run fixture            # http://127.0.0.1:4173/

# 터미널 2: 분석
node src/cli.mjs http://127.0.0.1:4173/
node src/cli.mjs http://127.0.0.1:4173/private/   # robots.txt 금지 → 분석하지 않고 종료
```

결과는 `output/` 에 생깁니다.

```
output/
├── report.md
├── report.json
└── screenshots/
    ├── 01-desktop.png   # 1280px
    ├── 01-tablet.png    # 768px
    └── 01-mobile.png    # 390px
```

`report.md` 를 Claude 에게 주고 "이 구조를 참고해 내 꽃집 사이트 레이아웃을 새로 설계해 줘"처럼 활용할 수 있습니다.

## 출력 예시

로컬 테스트 사이트를 분석한 `report.md` 일부입니다.

```markdown
## 사이트 요약

| 항목 | 내용 |
| --- | --- |
| 분석한 페이지 | 3개 (건너뜀 1개) |
| 기술 스택 단서 | 서버: FixtureServer/1.0, 백엔드: node:http |
| 주요 글꼴 | Pretendard(29), Arial(2) |
| 주요 배경색 | `#ffffff`(4), `#2f6b4f`(3), `#fffaf3`(3), `#e4572e`(1), `#efefef`(1) |
| 브레이크포인트 | max-width 768px, min-width 1024px |
| 애니메이션 | animation 1 · transition 11 · @keyframes 페이지당 최대 1 · IntersectionObserver 있음 · 스크롤 리스너 없음 |
| 이미지 alt 누락 | 1개 |
| API 호출 | GET /api/data |

## 다시 만들 때 참고할 점

- [ ] 반응형: 브레이크포인트 768px, 1024px 를 기준으로 레이아웃이 바뀐다. 모바일·태블릿·데스크톱 스크린샷을 나란히 보고 무엇이 바뀌는지 정리한다.
- [ ] 움직임: 애니메이션 요소 1개, 트랜지션 요소 11개, @keyframes 페이지당 최대 1개. prefers-reduced-motion 에는 대응하고 있다. 움직임을 줄이는 설정을 존중한다.
- [ ] 스크롤 효과: IntersectionObserver 를 사용한다. 화면에 들어올 때 나타나는 효과는 이 API 로 직접 구현해 본다.
- [ ] 접근성: alt 속성이 없는 이미지 1개. 의미 있는 이미지는 설명을, 장식 이미지는 alt="" 를 넣는다.
- [ ] 저작권: 문구·이미지·로고·아이콘은 복제하지 말고 직접 만들거나 라이선스가 있는 자료를 쓴다. 이 보고서는 구조를 공부하는 참고 자료다.

## 건너뛴 페이지

| URL | 이유 |
| --- | --- |
| http://127.0.0.1:4173/private/ | robots.txt Disallow |

## 페이지별 분석

### 1. 봄날 꽃집 - 홈

#### 제목 구조

- H1 계절을 담은 꽃다발
  - H2 인기 상품
  - H2 찾아오시는 길
    - H3 영업 시간
```

## 수집 항목과 한계

| 항목 | 방법 | 한계 |
| --- | --- | --- |
| 제목·설명·언어 | `title`, `meta[name=description]`, `<html lang>` | — |
| 제목 구조·랜드마크 | h1~h3, header/nav/main/footer(+ARIA role) | 페이지당 제목 60개까지 |
| 요소 개수·alt 누락 | 링크·버튼·폼·이미지 수, `alt` 속성이 아예 없는 `img` | `alt=""`(장식 이미지)는 정상으로 봄 |
| 글꼴·색상 | 요소별 계산된 스타일의 **빈도**(면적이 아님) | 요소 4,000개까지. 버튼·입력칸의 브라우저 기본 글꼴(Arial 등)도 집계됨 |
| 브레이크포인트 | 같은 출처 스타일시트의 `@media` 너비 조건 | 다른 출처 CSS(CDN)는 건너뜀, JS 로 바꾸는 레이아웃은 알 수 없음 |
| 애니메이션 | 계산된 `animation`/`transition`, `@keyframes`, IntersectionObserver 생성·scroll 리스너 등록 횟수 | 페이지 스크립트보다 먼저 실행되는 초기화 스크립트로 셉니다. 페이지를 한 번 아래로 스크롤해 지연 로딩을 깨웁니다 |
| 기술 스택 | 응답 헤더 `server`/`x-powered-by`, React·Next·Vue·Nuxt·Svelte·jQuery·GSAP 전역 변수·DOM 마커 | **단서**일 뿐 확정이 아닙니다. 빌드 방식에 따라 놓칠 수 있습니다 |
| 네트워크·API | Playwright 요청 기록(종류별 개수·응답 본문 크기), fetch/xhr 경로 | 같은 브라우저 안에서 캐시된 요청은 다음 페이지에서 빠질 수 있음 |
| 로드 시간 | Navigation Timing 의 DOMContentLoaded·load | 내 컴퓨터·네트워크 기준 값 |

## 테스트 방법

```bash
npm test
```

- 외부 사이트에 접속하지 않습니다. `tests/helpers/fixture-server.mjs` 가 `node:http` 로 `tests/fixtures/site/` 를 띄우고, 그 사이트를 실제 브라우저로 분석해 검증합니다.
- 단위 테스트: robots 파싱·판정, URL 정규화·같은 출처 판정, 색상·글꼴 집계, 브레이크포인트 파싱, 기술 단서·네트워크 요약, 보고서 렌더링, 인자 검증
- 통합 테스트: BFS 방문 순서, `/private/` 를 요청조차 하지 않는지, 모든 요청의 User-Agent, 요청 간격, alt 누락 1개, 브레이크포인트, 애니메이션·IntersectionObserver, `GET /api/data`, 스크린샷 3장과 보고서 파일
- CLI 테스트: `--help`, 잘못된 인자, robots 금지 시 종료 코드 2
- playwright 가 없으면 브라우저가 필요한 테스트는 건너뜁니다.

---

Copyright (c) 2026 devalivemanager · [MIT 라이선스](../../LICENSE)
