#!/usr/bin/env node
// 사용법: node src/cli.mjs <대본.json> -o <결과 폴더> [--png] [--painter svg|api] [--images <그림 폴더>]
import { mkdir, stat, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { loadPlaywright, PLAYWRIGHT_INSTALL_HINT } from "./browser.mjs";
import { LayoutError } from "./layout.mjs";
import { createFolderPainter, createImageApiPainter, createSvgPainter } from "./painters.mjs";
import { PROMPT_LANGS } from "./prompt.mjs";
import { buildEpisode, buildStoryboard, promptsToMarkdown } from "./render.mjs";
import { EpisodeError, loadEpisode, validatePromptLang } from "./script.mjs";

const USAGE = "사용법: node src/cli.mjs <대본.json> -o <결과 폴더> [--png] [--painter svg|api] [--images <그림 폴더>] [--prompt-lang ko|en]";

export function parseArgs(argv) {
  const opts = { input: null, out: null, png: false, painter: "svg", promptLang: "ko", images: null };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "-o" || arg === "--out") opts.out = argv[++i];
    else if (arg === "--png") opts.png = true;
    else if (arg === "--painter") opts.painter = argv[++i];
    else if (arg === "--prompt-lang") opts.promptLang = argv[++i];
    else if (arg === "--images") opts.images = argv[++i];
    else if (arg.startsWith("-")) throw new Error(`알 수 없는 옵션: ${arg}`);
    else if (opts.input === null) opts.input = arg;
    else throw new Error(`입력 파일은 하나만 줄 수 있습니다: ${arg}`);
  }
  if (!opts.input) throw new Error("대본 파일 경로가 필요합니다.");
  if (!opts.out) throw new Error("-o 로 결과 폴더를 정하세요.");
  if (!["svg", "api"].includes(opts.painter)) throw new Error(`--painter 는 svg 또는 api 입니다: ${opts.painter}`);
  if (opts.images !== null) {
    if (!opts.images || opts.images.startsWith("-")) throw new Error("--images 다음에 그림 폴더를 적으세요.");
    if (opts.painter === "api") throw new Error("--images 와 --painter api 는 함께 쓸 수 없습니다.");
  }
  if (!PROMPT_LANGS.includes(opts.promptLang)) throw new Error(`--prompt-lang 은 ${PROMPT_LANGS.join(" 또는 ")} 입니다: ${opts.promptLang}`);
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
    const langErrors = validatePromptLang(episode, opts.promptLang);
    if (langErrors.length > 0) throw new EpisodeError(langErrors);
    let painter;
    if (opts.images) {
      const info = await stat(opts.images).catch(() => null);
      if (!info?.isDirectory()) throw new Error(`그림 폴더가 없습니다: ${opts.images}`);
      painter = createFolderPainter({ dir: opts.images });
    } else {
      painter = opts.painter === "api"
        ? createImageApiPainter({ endpoint: env.IMAGE_API_URL, apiKey: env.IMAGE_API_KEY })
        : createSvgPainter();
    }
    const result = await buildEpisode(episode, painter, { promptLang: opts.promptLang });
    const outDir = resolve(opts.out);
    await mkdir(outDir, { recursive: true });
    const htmlPath = join(outDir, "index.html");
    await writeFile(htmlPath, result.html, "utf8");
    await writeFile(join(outDir, "prompts.md"), promptsToMarkdown(episode, result.prompts), "utf8");
    await writeFile(join(outDir, "storyboard.md"), buildStoryboard(episode, result.prompts), "utf8");
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
