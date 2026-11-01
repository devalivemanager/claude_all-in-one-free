// 도구 전체에서 쓰는 상수 모음

export const TOOL_NAME = "SiteAnalyzer";
export const TOOL_VERSION = "1.0.0";

// robots.txt 의 User-agent 와 비교할 때 쓰는 이름(제품 토큰)
export const BOT_TOKEN = TOOL_NAME;

// 요청마다 도구 이름을 밝혀서, 사이트 운영자가 로그에서 이 도구를 알아볼 수 있게 한다
export const USER_AGENT = `${TOOL_NAME}/${TOOL_VERSION} (educational site research tool; no content copying)`;

// 스크린샷을 찍을 화면 크기
export const VIEWPORTS = [
  { name: "desktop", label: "데스크톱", width: 1280, height: 800 },
  { name: "tablet", label: "태블릿", width: 768, height: 1024 },
  { name: "mobile", label: "모바일", width: 390, height: 844 },
];

export const DEFAULTS = {
  outDir: "output",
  maxPages: 5,
  delayMs: 1000,
};

// CLI 에서 허용하는 최소 요청 간격(ms). 서버에 부담을 주지 않기 위한 하한선
export const MIN_DELAY_MS = 500;
export const MAX_PAGES_LIMIT = 50;
