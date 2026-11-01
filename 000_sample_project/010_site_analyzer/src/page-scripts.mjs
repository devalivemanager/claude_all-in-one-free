// 브라우저 안에서 실행되는 함수들.
// Playwright 가 함수 소스를 브라우저로 보내 실행하므로, 바깥 변수나 import 를 쓰면 안 된다.

/**
 * 페이지 스크립트보다 먼저 실행되어 애니메이션 관련 API 사용을 센다.
 * 원래 동작은 그대로 두고 호출 횟수만 기록한다.
 */
export function installHints() {
  const hints = { intersectionObserver: 0, scrollListeners: 0 };
  Object.defineProperty(window, "__siteAnalyzerHints", { value: hints });

  const OriginalIO = window.IntersectionObserver;
  if (OriginalIO) {
    window.IntersectionObserver = class extends OriginalIO {
      constructor(...args) {
        super(...args);
        hints.intersectionObserver += 1;
      }
    };
  }

  const originalAdd = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, ...rest) {
    if (type === "scroll" || type === "wheel") hints.scrollListeners += 1;
    return originalAdd.call(this, type, ...rest);
  };
}

/** 사람이 보는 것처럼 아래로 천천히 스크롤해서 지연 로딩·스크롤 애니메이션을 깨운다 */
export async function autoScroll() {
  const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
  for (let i = 0; i < 30 && window.scrollY + window.innerHeight < document.body.scrollHeight; i++) {
    window.scrollBy(0, step);
    await new Promise((r) => setTimeout(r, 100));
  }
  window.scrollTo(0, 0);
}

/** 페이지 구조·스타일·기술 단서 원자료를 모은다 */
export function collectInPage() {
  const MAX_ELEMENTS = 4000; // 아주 큰 페이지에서 너무 오래 걸리지 않도록 제한
  const clean = (s, n = 80) => (s || "").replace(/\s+/g, " ").trim().slice(0, n);
  const count = (selector) => document.querySelectorAll(selector).length;
  const skipTags = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "META", "LINK", "BR"]);

  // 1) 요소별 계산된 스타일
  const elements = [document.documentElement, document.body, ...document.body.querySelectorAll("*")].slice(0, MAX_ELEMENTS);
  const fontFamilies = [];
  const textColors = [];
  const backgroundColors = [];
  let animatedElements = 0;
  let transitionElements = 0;
  let vueScoped = false;
  let svelteClass = false;

  for (const el of elements) {
    if (skipTags.has(el.tagName)) continue;
    const cs = getComputedStyle(el);
    const hasText = [...el.childNodes].some((n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
    if (hasText) {
      fontFamilies.push(cs.fontFamily);
      textColors.push(cs.color);
    }
    backgroundColors.push(cs.backgroundColor);
    if (cs.animationName && cs.animationName !== "none") animatedElements += 1;
    if (cs.transitionDuration.split(",").some((d) => parseFloat(d) > 0)) transitionElements += 1;
    if (!vueScoped && [...el.attributes].some((a) => a.name.startsWith("data-v-"))) vueScoped = true;
    if (!svelteClass && /\bsvelte-[a-z0-9]+/.test(el.getAttribute("class") || "")) svelteClass = true;
  }

  // 2) 스타일시트 규칙: @media 조건과 @keyframes 개수
  const mediaTexts = [];
  let keyframes = 0;
  let sheetCount = 0;
  let skippedCrossOrigin = 0;
  let unreadable = 0;
  const walk = (rules) => {
    for (const rule of rules) {
      if (rule instanceof CSSMediaRule) mediaTexts.push(rule.conditionText || rule.media.mediaText);
      if (rule instanceof CSSKeyframesRule) keyframes += 1;
      if (rule.cssRules) walk(rule.cssRules);
    }
  };
  for (const sheet of document.styleSheets) {
    sheetCount += 1;
    // 다른 출처의 스타일시트는 읽지 않고 건너뛴다
    if (sheet.href && new URL(sheet.href).origin !== location.origin) {
      skippedCrossOrigin += 1;
      continue;
    }
    if (sheet.media && sheet.media.mediaText) mediaTexts.push(sheet.media.mediaText);
    try {
      walk(sheet.cssRules);
    } catch {
      unreadable += 1;
    }
  }

  // 3) 프레임워크·라이브러리 마커 (찾은 근거를 문자열로 남긴다)
  const scriptSrcs = [...document.scripts].map((s) => s.src).filter(Boolean);
  const scriptHas = (part) => scriptSrcs.some((src) => src.includes(part));
  const reactRoot = [...document.querySelectorAll("body, body > *, #root, #app, #__next")].some((el) =>
    Object.keys(el).some((k) => k.startsWith("__react")),
  );
  const pick = (pairs) => (pairs.find(([ok]) => ok) || [false, ""])[1] || null;
  const markers = {
    react: pick([
      [reactRoot, "DOM 요소의 __react* 속성"],
      [!!window.React, "전역 window.React"],
      [!!document.querySelector("[data-reactroot]"), "data-reactroot 속성"],
    ]),
    next: pick([
      [!!window.__NEXT_DATA__, "전역 __NEXT_DATA__"],
      [!!document.getElementById("__next"), "#__next 요소"],
      [scriptHas("/_next/"), "/_next/ 스크립트"],
    ]),
    vue: pick([
      [!!window.Vue, "전역 window.Vue"],
      [!!document.querySelector("[data-v-app]"), "data-v-app 속성"],
      [vueScoped, "data-v-* 스코프 속성"],
    ]),
    nuxt: pick([
      [!!window.__NUXT__, "전역 __NUXT__"],
      [!!document.getElementById("__nuxt"), "#__nuxt 요소"],
      [scriptHas("/_nuxt/"), "/_nuxt/ 스크립트"],
    ]),
    svelte: pick([[svelteClass, "svelte-* 클래스"]]),
    jquery: pick([[!!window.jQuery, "전역 window.jQuery"]]),
    gsap: pick([
      [!!window.gsap, "전역 window.gsap"],
      [!!window.TweenMax, "전역 window.TweenMax"],
    ]),
    generator: document.querySelector('meta[name="generator"]')?.content || null,
  };

  const hints = window.__siteAnalyzerHints || { intersectionObserver: 0, scrollListeners: 0 };

  return {
    title: clean(document.title, 120),
    description: clean(document.querySelector('meta[name="description"]')?.content, 200) || null,
    lang: document.documentElement.lang || null,
    headings: [...document.querySelectorAll("h1, h2, h3")]
      .slice(0, 60)
      .map((h) => ({ level: Number(h.tagName[1]), text: clean(h.textContent) })),
    landmarks: {
      header: count('header, [role="banner"]'),
      nav: count('nav, [role="navigation"]'),
      main: count('main, [role="main"]'),
      footer: count('footer, [role="contentinfo"]'),
    },
    counts: {
      links: count("a[href]"),
      buttons: count('button, input[type="button"], input[type="submit"], input[type="reset"], [role="button"]'),
      forms: count("form"),
      images: count("img"),
      imagesMissingAlt: count("img:not([alt])"),
    },
    fontFamilies,
    textColors,
    backgroundColors,
    css: { mediaTexts, keyframes, sheetCount, skippedCrossOrigin, unreadable },
    animation: {
      animatedElements,
      transitionElements,
      intersectionObserver: hints.intersectionObserver,
      scrollListeners: hints.scrollListeners + (window.onscroll ? 1 : 0),
    },
    markers,
    links: [...new Set([...document.querySelectorAll("a[href]")].map((a) => a.href))],
  };
}

/** 내비게이션 타이밍(ms) */
export function readTiming() {
  const nav = performance.getEntriesByType("navigation")[0];
  if (!nav) return { domContentLoadedMs: null, loadMs: null };
  return {
    domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
    loadMs: Math.round(nav.loadEventEnd - nav.startTime),
  };
}
