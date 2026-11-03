// 컷을 SVG 로, 회차 전체를 세로 스크롤 HTML 로 만든다.
// 대사·제목 등 사람이 쓴 글자는 모두 이스케이프한다(대본에 <script> 가 들어 있어도 글자로만 보이게).
import { castPosition, drawBackground, drawCharacter } from "./characters.mjs";
import { BUBBLE, CAPTION_HEIGHT, layoutBubbles } from "./layout.mjs";
import { buildPanelPrompt } from "./prompt.mjs";
import { DEFAULT_GAP } from "./script.mjs";

/** 컷 다음 여백(px). 연출용 「여백 띠」: 긴장·시간 경과는 넓게, 빠른 대화는 좁게 */
export const gapAfter = (panel) => panel.gap_after ?? DEFAULT_GAP;

/** 페이지의 전체 세로 길이(컷 높이 + 컷 사이 여백). 마지막 컷 뒤 여백은 세지 않는다 */
export function scrollLength(episode) {
  return episode.panels.reduce((sum, p, i) => sum + p.height + (i < episode.panels.length - 1 ? gapAfter(p) : 0), 0);
}

export const FONT_FAMILY = "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', 'WenQuanYi Zen Hei', sans-serif";

export function escapeXml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

const f = (n) => Math.round(n * 10) / 10;

function drawBubble(b, opts = BUBBLE) {
  const box = `<rect x="${f(b.x)}" y="${f(b.y)}" width="${f(b.w)}" height="${f(b.h)}" rx="18" fill="#fff" stroke="#222" stroke-width="2"/>`;
  const text = b.rows
    .map((row, i) => `<text x="${f(b.x + b.w / 2)}" y="${f(b.y + opts.padY + opts.lineHeight * i + opts.fontSize * 0.95)}" text-anchor="middle" font-size="${opts.fontSize}">${escapeXml(row)}</text>`)
    .join("");
  const open = `<g class="bubble" data-who="${escapeXml(b.who)}" data-box="${f(b.x)},${f(b.y)},${f(b.w)},${f(b.h)}">`;
  if (!b.tail) return `${open}${box}${text}</g>`;
  const tail = `<path d="M${f(b.tail.baseX - 12)} ${f(b.tail.baseY - 2)} L${f(b.tail.tipX)} ${f(b.tail.tipY)} L${f(b.tail.baseX + 12)} ${f(b.tail.baseY - 2)} Z" fill="#fff" stroke="#222" stroke-width="2" stroke-linejoin="round"/>`;
  // 꼬리와 상자의 이음매를 흰색으로 덮어 한 몸처럼 보이게 한다
  const seam = `<rect x="${f(b.tail.baseX - 10)}" y="${f(b.tail.baseY - 4)}" width="20" height="4" fill="#fff"/>`;
  return `${open}${tail}${box}${seam}${text}</g>`;
}

function drawCaption(caption, width) {
  return `<g class="caption"><rect width="${width}" height="${CAPTION_HEIGHT - 8}" fill="#222" opacity="0.85"/><text x="16" y="30" font-size="20" fill="#fff">${escapeXml(caption)}</text></g>`;
}

/** 컷 하나를 SVG 문자열로. imageHref 가 있으면 그림 대신 그 이미지를 깐다. */
export function renderPanelSvg(episode, panel, imageHref = null) {
  const width = episode.width;
  const cast = panel.cast ?? [];
  const positions = Object.fromEntries(cast.map((c) => [c.who, castPosition(c, panel.height, width)]));
  const bubbles = layoutBubbles(panel, positions, width);
  const art = imageHref
    ? `<image href="${escapeXml(imageHref)}" width="${width}" height="${panel.height}" preserveAspectRatio="xMidYMid slice"/>`
    : drawBackground(panel.background, width, panel.height) + cast.map((c) => drawCharacter(episode.characters[c.who], c, panel.height, width)).join("");
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${panel.height}" width="${width}" height="${panel.height}" role="img" aria-label="${escapeXml(panel.scene)}" font-family="${FONT_FAMILY}">`,
    art,
    panel.caption ? drawCaption(panel.caption, width) : "",
    bubbles.map((b) => drawBubble(b)).join(""),
    "</svg>",
  ].join("");
}

/**
 * 회차 전체를 만든다.
 * 그림 도구가 실패하면 그 컷만 코드 그림으로 대신하고 warnings 에 남긴다(조용히 넘어가지 않는다).
 */
export async function buildEpisode(episode, painter, { promptLang = "ko" } = {}) {
  const warnings = [];
  const prompts = [];
  const panels = [];
  for (const panel of episode.panels) {
    const prompt = buildPanelPrompt(episode, panel, promptLang);
    prompts.push({ id: panel.id, prompt });
    let image = null;
    try {
      image = await painter.paint({ prompt, width: episode.width, height: panel.height, panel });
    } catch (error) {
      warnings.push(`컷 ${panel.id}: 그림을 받지 못해 코드 그림으로 대신했습니다 - ${error.message}`);
    }
    panels.push({ id: panel.id, svg: renderPanelSvg(episode, panel, image), bubbles: (panel.lines ?? []).length, gap: gapAfter(panel) });
  }
  const title = `${episode.title} ${episode.episode}화`;
  const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeXml(title)}</title>
<style>
  body { margin: 0; background: #f2f2f2; font-family: ${FONT_FAMILY}; }
  header, main, footer { max-width: ${episode.width}px; margin: 0 auto; }
  header { padding: 24px 16px 8px; }
  h1 { margin: 0; font-size: 22px; }
  figure { margin: 0; background: #fff; }
  figure svg { display: block; width: 100%; height: auto; }
  footer { padding: 16px; color: #777; font-size: 13px; }
</style>
</head>
<body>
<header><h1>${escapeXml(title)}</h1></header>
<main>
${panels.map((p, i) => `<figure id="${escapeXml(p.id)}"${i < panels.length - 1 ? ` style="margin-bottom:${p.gap}px"` : ""}>${p.svg}</figure>`).join("\n")}
</main>
<footer>컷 ${panels.length}개 · 그림: ${PAINTER_LABELS[painter.name] ?? painter.name}</footer>
</body>
</html>
`;
  return { html, warnings, prompts, panelCount: panels.length, bubbleCount: panels.reduce((s, p) => s + p.bubbles, 0) };
}

const PAINTER_LABELS = { svg: "코드 그림", api: "이미지 AI", files: "그림 파일" };

/** 컷별 프롬프트를 사람이 읽기 좋은 마크다운으로. 컷마다 그림 크기와 --images 용 파일 이름을 함께 적는다 */
export function promptsToMarkdown(episode, prompts) {
  const heights = Object.fromEntries(episode.panels.map((p) => [p.id, p.height]));
  return [
    `# ${episode.title} ${episode.episode}화 — 컷별 이미지 프롬프트`,
    "",
    "받은 그림은 컷 id 이름(예: p1.png)으로 한 폴더에 모아 `--images <폴더>` 로 넣는다. 크기가 다르면 가운데를 기준으로 잘라 맞춘다.",
    "",
    ...prompts.flatMap((p) => [`## ${p.id}`, "", `크기 ${episode.width}×${heights[p.id]}px · 파일 이름 \`${p.id}.png\``, "", "```", p.prompt, "```", ""]),
  ].join("\n");
}

/** 마크다운 표 칸 안에서 표를 깨는 문자(| 와 줄바꿈)를 바꾼다 */
function cell(text) {
  return String(text ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>");
}

/**
 * 사람이 검토하기 좋은 콘티 표.
 * 컷 번호 / 연출(배경·자막·높이) / 등장·표정 / 대사 / 이미지 프롬프트
 */
export function buildStoryboard(episode, prompts) {
  const promptOf = Object.fromEntries(prompts.map((p) => [p.id, p.prompt]));
  const rows = episode.panels.map((panel, i) => {
    const last = i === episode.panels.length - 1;
    const direction = [`배경 ${panel.background}`, `높이 ${panel.height}px`, last ? "마지막 컷" : `다음 여백 ${gapAfter(panel)}px`, panel.caption ? `자막 「${panel.caption}」` : null].filter(Boolean).join(", ");
    const cast = (panel.cast ?? []).map((c) => `${episode.characters[c.who].name}(${c.expression})`).join(", ") || "-";
    const lines = (panel.lines ?? []).map((l) => `${episode.characters[l.who].name}: ${l.text}`).join("\n") || "-";
    return `| ${i + 1} (${cell(panel.id)}) | ${cell(direction)}<br>${cell(panel.scene)} | ${cell(cast)} | ${cell(lines)} | ${cell(promptOf[panel.id])} |`;
  });
  return [
    `# ${episode.title} ${episode.episode}화 — 콘티`,
    "",
    `컷 ${episode.panels.length}개, 전체 세로 길이 ${scrollLength(episode)}px(컷 높이 + 컷 사이 여백)`,
    "",
    "| 컷 | 연출 | 등장·표정 | 대사 | 이미지 프롬프트 |",
    "|---|---|---|---|---|",
    ...rows,
    "",
  ].join("\n");
}
