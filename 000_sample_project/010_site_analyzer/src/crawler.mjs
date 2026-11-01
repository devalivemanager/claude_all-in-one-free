// 사이트 분석 흐름: robots.txt 확인 → BFS 방문 → 페이지별 수집·스크린샷 → 보고서 저장
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { buildPageAnalysis } from "./analysis.mjs";
import { loadPlaywright, PLAYWRIGHT_INSTALL_HINT } from "./browser.mjs";
import { BOT_TOKEN, DEFAULTS, TOOL_NAME, TOOL_VERSION, USER_AGENT, VIEWPORTS } from "./config.mjs";
import { autoScroll, collectInPage, installHints, readTiming } from "./page-scripts.mjs";
import { buildReport, renderMarkdown } from "./report.mjs";
import { fetchRobots, isAllowed } from "./robots.mjs";
import { isInScope, looksLikePage, normalizeUrl, pathWithQuery } from "./url-utils.mjs";

export class RobotsBlockedError extends Error {}
export class PlaywrightMissingError extends Error {}

/** 페이지 하나를 열어 원자료를 모으고 스크린샷 3장을 찍는다 */
async function analyzePage(context, url, index, outDir) {
  const page = await context.newPage();
  const requests = [];
  const pending = [];
  page.on("requestfinished", (req) => {
    pending.push(
      req
        .sizes()
        .then((sizes) => requests.push({ url: req.url(), type: req.resourceType(), method: req.method(), bytes: sizes.responseBodySize }))
        .catch(() => {}),
    );
  });

  try {
    const started = Date.now();
    const response = await page.goto(url, { waitUntil: "load", timeout: 30_000 });
    const measuredMs = Date.now() - started;
    if (!response) return { error: "응답 없음" };
    const headers = response.headers();
    const finalUrl = page.url();
    if (!response.ok()) return { error: `HTTP ${response.status()}` };
    if (!String(headers["content-type"] ?? "").includes("html")) return { error: "HTML 문서가 아님" };
    if (new URL(finalUrl).origin !== new URL(url).origin) return { error: `다른 출처로 이동됨(${finalUrl})` };

    await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});
    await page.evaluate(autoScroll);
    const raw = await page.evaluate(collectInPage);
    const timing = { ...(await page.evaluate(readTiming)), measuredMs };

    // 같은 페이지에서 화면 크기만 바꿔 찍는다(다시 불러오지 않으므로 서버 요청이 늘지 않는다)
    const screenshots = {};
    const prefix = String(index + 1).padStart(2, "0");
    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.waitForTimeout(300);
      const file = `screenshots/${prefix}-${vp.name}.png`;
      await page.screenshot({ path: path.join(outDir, file), fullPage: true, animations: "disabled" });
      screenshots[vp.name] = file;
    }

    await Promise.all(pending);
    return { page: buildPageAnalysis({ url, finalUrl, status: response.status(), headers, raw, requests, timing, screenshots }) };
  } catch (err) {
    return { error: err.message.split("\n")[0] };
  } finally {
    await page.close();
  }
}

/**
 * 사이트를 분석해 outDir 에 report.md, report.json, screenshots/ 를 만든다.
 * 시작 URL 이 robots.txt 에서 금지되어 있으면 RobotsBlockedError 를 던진다.
 */
export async function analyzeSite({
  url,
  outDir = DEFAULTS.outDir,
  maxPages = DEFAULTS.maxPages,
  sameOrigin = false,
  delayMs = DEFAULTS.delayMs,
  log = () => {},
}) {
  const startUrl = normalizeUrl(url);
  if (!startUrl) throw new Error(`올바른 http(s) URL 이 아닙니다: ${url}`);
  const { origin } = new URL(startUrl);

  // 1) robots.txt 확인
  const robots = await fetchRobots(origin, USER_AGENT);
  log(`robots.txt: ${robots.status}${robots.note ? ` (${robots.note})` : ""}`);
  const allowed = (u) => isAllowed(robots.groups, pathWithQuery(u), BOT_TOKEN);
  if (!allowed(startUrl)) {
    throw new RobotsBlockedError(`robots.txt 가 이 경로의 수집을 허용하지 않아 분석하지 않습니다: ${startUrl}`);
  }

  const playwright = await loadPlaywright();
  if (!playwright) throw new PlaywrightMissingError(PLAYWRIGHT_INSTALL_HINT);

  await mkdir(path.join(outDir, "screenshots"), { recursive: true });
  const browser = await playwright.chromium.launch();
  const pages = [];
  const skipped = [];
  try {
    const desktop = VIEWPORTS[0];
    const context = await browser.newContext({
      userAgent: USER_AGENT,
      viewport: { width: desktop.width, height: desktop.height },
    });
    await context.addInitScript(installHints);

    // 2) 너비 우선 탐색(BFS): 가까운 페이지부터 차례로 방문
    const queue = [startUrl];
    const seen = new Set([startUrl]);
    let visits = 0;
    while (queue.length > 0 && pages.length < maxPages) {
      const target = queue.shift();
      if (visits > 0) await sleep(delayMs); // 페이지 사이 간격
      visits += 1;
      log(`[${pages.length + 1}/${maxPages}] ${target}`);

      const result = await analyzePage(context, target, pages.length, outDir);
      if (result.error) {
        skipped.push({ url: target, reason: result.error });
        continue;
      }
      pages.push(result.page);

      for (const link of result.page.links) {
        const next = normalizeUrl(link);
        if (!next || seen.has(next)) continue;
        if (!isInScope(next, startUrl, { sameOrigin }) || !looksLikePage(next)) continue;
        seen.add(next);
        if (allowed(next)) queue.push(next);
        else skipped.push({ url: next, reason: "robots.txt Disallow" });
      }
    }
  } finally {
    await browser.close();
  }

  // 3) 보고서 저장
  const report = buildReport({
    tool: { name: TOOL_NAME, version: TOOL_VERSION, userAgent: USER_AGENT },
    startUrl,
    analyzedAt: new Date().toISOString(),
    options: { maxPages, sameOrigin, delayMs },
    robots: { url: robots.url, status: robots.status, note: robots.note ?? null },
    pages,
    skipped,
  });
  await writeFile(path.join(outDir, "report.json"), JSON.stringify(report, null, 2) + "\n");
  await writeFile(path.join(outDir, "report.md"), renderMarkdown(report));
  return report;
}
