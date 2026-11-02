#!/usr/bin/env node
// 사용법: node src/cli.mjs <대본.json> -o <결과 폴더> [--png] [--painter svg|api]
import { mkdir, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { loadPlaywright, PLAYWRIGHT_INSTALL_HINT } from "./browser.mjs";
import { LayoutError } from "./layout.mjs";
import { createImageApiPainter, createSvgPainter } from "./painters.mjs";
import { buildEpisode, promptsToMarkdown } from "./render.mjs";
import { EpisodeError, loadEpisode } from "./script.mjs";

const USAGE = "사용법: node src/cli.mjs <대본.json> -o <결과 폴더> [--png] [--painter svg|api]";

export function parseArgs(argv) {
  const opts = { input: null, out: null, png: false, painter: "svg" };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "-o" || arg === "--out") opts.out = argv[++i];
    else if (arg === "--png") opts.png = true;
    else if (arg === "--painter") opts.painter = argv[++i];
    else if (arg.startsWith("-")) throw new Error(`알 수 없는 옵션: ${arg}`);
    else if (opts.input === null) opts.input = arg;
    else throw new Error(`입력 파일은 하나만 줄 수 있습니다: ${arg}`);
  }
  if (!opts.input) throw new Error("대본 파일 경로가 필요합니다.");
  if (!opts.out) throw new Error("-o 로 결과 폴더를 정하세요.");
  if (!["svg", "api"].includes(opts.painter)) throw new Error(`--painter 는 svg 또는 api 입니다: ${opts.painter}`);
  return opts;
}

async function screenshot(htmlPath, pngPath, width) {
  const playwright = await loadPlaywright();
  if (!playwright) throw new Error(PLAYWRIGHT_INSTALL_HINT);
  const browser = await playwright.chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width, height: 800 } });
    await page.goto(pathToFileURL(htmlPath).href);
    await page.screenshot({ path: pngPath, fullPage: true });
  } finally {
    await browser.close();
  }
}

/** 종료 코드: 0 정상, 1 대본·배치·파일 오류, 2 잘못된 인자 */
export async function main(argv, env = process.env, log = console) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (error) {
    log.error(`오류: ${error.message}\n${USAGE}`);
    return 2;
  }
  try {
    const episode = await loadEpisode(opts.input);
    const painter = opts.painter === "api"
      ? createImageApiPainter({ endpoint: env.IMAGE_API_URL, apiKey: env.IMAGE_API_KEY })
      : createSvgPainter();
    const result = await buildEpisode(episode, painter);
    const outDir = resolve(opts.out);
    await mkdir(outDir, { recursive: true });
    const htmlPath = join(outDir, "index.html");
    await writeFile(htmlPath, result.html, "utf8");
    await writeFile(join(outDir, "prompts.md"), promptsToMarkdown(episode, result.prompts), "utf8");
    if (opts.png) await screenshot(htmlPath, join(outDir, "webtoon.png"), episode.width);
    for (const w of result.warnings) log.error(`경고: ${w}`);
    log.log(`완료: ${htmlPath}`);
    log.log(`컷 ${result.panelCount}개, 말풍선 ${result.bubbleCount}개, 경고 ${result.warnings.length}건${opts.png ? ", webtoon.png 저장" : ""}`);
    return 0;
  } catch (error) {
    if (error instanceof EpisodeError || error instanceof LayoutError) log.error(error.message);
    else log.error(`오류: ${error.message}`);
    return 1;
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  process.exitCode = await main(process.argv.slice(2));
}
