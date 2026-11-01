// 브라우저에서 모은 원자료를 보고서용 데이터로 정리 (순수 함수)
import { detectMediaFeatures, parseBreakpoints, topColors, topFonts } from "./style-utils.mjs";

/** 응답 헤더와 페이지 마커로 기술 스택 단서를 만든다 */
export function detectTech({ headers = {}, markers = {} }) {
  const tech = [];
  if (headers.server) tech.push({ name: `서버: ${headers.server}`, evidence: "응답 헤더 server" });
  if (headers["x-powered-by"]) {
    tech.push({ name: `백엔드: ${headers["x-powered-by"]}`, evidence: "응답 헤더 x-powered-by" });
  }
  const labels = {
    react: "React",
    next: "Next.js",
    vue: "Vue",
    nuxt: "Nuxt",
    svelte: "Svelte",
    jquery: "jQuery",
    gsap: "GSAP",
  };
  for (const [key, name] of Object.entries(labels)) {
    if (markers[key]) tech.push({ name, evidence: markers[key] });
  }
  if (markers.generator) tech.push({ name: `생성기: ${markers.generator}`, evidence: "meta generator" });
  return tech;
}

/**
 * 네트워크 요청 기록을 종류별 개수·용량으로 묶는다.
 * records: [{ url, type, method, bytes }]
 */
export function summarizeRequests(records) {
  const byType = new Map();
  for (const r of records) {
    const item = byType.get(r.type) ?? { type: r.type, count: 0, bytes: 0 };
    item.count += 1;
    item.bytes += r.bytes > 0 ? r.bytes : 0;
    byType.set(r.type, item);
  }
  const list = [...byType.values()].sort((a, b) => b.bytes - a.bytes || b.count - a.count);
  return {
    total: {
      count: records.length,
      bytes: list.reduce((sum, t) => sum + t.bytes, 0),
    },
    byType: list,
  };
}

/**
 * fetch/xhr 요청을 "메서드 경로" 목록으로 만든다.
 * 쿼리 문자열에는 개인 정보가 들어 있을 수 있어 빼고 경로만 남긴다.
 */
export function listApiCalls(records, pageUrl) {
  const origin = new URL(pageUrl).origin;
  const calls = new Set();
  for (const r of records) {
    if (r.type !== "fetch" && r.type !== "xhr") continue;
    const u = new URL(r.url);
    const where = u.origin === origin ? u.pathname : `${u.origin}${u.pathname}`;
    calls.add(`${r.method} ${where}`);
  }
  return [...calls].sort();
}

/** 페이지 하나의 원자료를 보고서용 구조로 정리한다 */
export function buildPageAnalysis({ url, finalUrl, status, headers, raw, requests, timing, screenshots }) {
  return {
    url,
    finalUrl,
    status,
    title: raw.title,
    description: raw.description,
    lang: raw.lang,
    headings: raw.headings,
    landmarks: raw.landmarks,
    counts: raw.counts,
    fonts: topFonts(raw.fontFamilies),
    colors: {
      background: topColors(raw.backgroundColors),
      text: topColors(raw.textColors),
    },
    css: {
      breakpoints: parseBreakpoints(raw.css.mediaTexts),
      mediaFeatures: detectMediaFeatures(raw.css.mediaTexts),
      stylesheets: raw.css.sheetCount,
      skippedCrossOriginSheets: raw.css.skippedCrossOrigin,
      unreadableSheets: raw.css.unreadable,
    },
    animation: {
      animatedElements: raw.animation.animatedElements,
      transitionElements: raw.animation.transitionElements,
      keyframes: raw.css.keyframes,
      intersectionObserver: raw.animation.intersectionObserver,
      scrollListeners: raw.animation.scrollListeners,
    },
    headers: {
      server: headers.server ?? null,
      xPoweredBy: headers["x-powered-by"] ?? null,
    },
    tech: detectTech({ headers, markers: raw.markers }),
    network: summarizeRequests(requests),
    apiCalls: listApiCalls(requests, finalUrl ?? url),
    timing,
    screenshots,
    links: raw.links,
  };
}
