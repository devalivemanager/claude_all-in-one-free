// 보고서 단위 테스트용 페이지 분석 데이터. overrides 로 일부만 바꿔 쓴다.
export function samplePage(overrides = {}) {
  return {
    url: "https://ex.com/",
    finalUrl: "https://ex.com/",
    status: 200,
    title: "예시 | 홈",
    description: "예시 사이트",
    lang: "ko",
    headings: [
      { level: 1, text: "환영합니다" },
      { level: 2, text: "소개" },
    ],
    landmarks: { header: 1, nav: 1, main: 1, footer: 1 },
    counts: { links: 4, buttons: 1, forms: 0, images: 2, imagesMissingAlt: 0 },
    fonts: [{ font: "Pretendard", count: 10 }],
    colors: {
      background: [{ color: "#ffffff", count: 5 }],
      text: [{ color: "#222222", count: 9 }],
    },
    css: {
      breakpoints: [{ px: 768, feature: "max" }],
      mediaFeatures: { prefersColorScheme: false, prefersReducedMotion: false, print: false },
      stylesheets: 1,
      skippedCrossOriginSheets: 0,
      unreadableSheets: 0,
    },
    animation: { animatedElements: 0, transitionElements: 0, keyframes: 0, intersectionObserver: 0, scrollListeners: 0 },
    headers: { server: null, xPoweredBy: null },
    tech: [],
    network: { total: { count: 2, bytes: 3000 }, byType: [{ type: "document", count: 2, bytes: 3000 }] },
    apiCalls: [],
    timing: { domContentLoadedMs: 50, loadMs: 100, measuredMs: 120 },
    screenshots: { desktop: "screenshots/01-desktop.png", tablet: "screenshots/01-tablet.png", mobile: "screenshots/01-mobile.png" },
    links: [],
    ...overrides,
  };
}

export function sampleReportBase(pages) {
  return {
    tool: { name: "SiteAnalyzer", version: "1.0.0", userAgent: "SiteAnalyzer/1.0.0" },
    startUrl: "https://ex.com/",
    analyzedAt: "2026-01-01T00:00:00.000Z",
    options: { maxPages: 5, sameOrigin: false, delayMs: 1000 },
    robots: { url: "https://ex.com/robots.txt", status: "found", note: null },
    pages,
    skipped: [{ url: "https://ex.com/private/", reason: "robots.txt Disallow" }],
  };
}
