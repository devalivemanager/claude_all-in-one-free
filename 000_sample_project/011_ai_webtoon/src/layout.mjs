// 말풍선 배치: 화자 위쪽에, 읽는 순서대로 위에서 아래로 쌓는다.
// 쌓는 방식이라 말풍선끼리 겹치지 않는다. 인물 머리 위까지 공간이 모자라면 오류로 알린다.
import { textWidth, wrapText } from "./text.mjs";

export const BUBBLE = { fontSize: 22, lineHeight: 30, padX: 18, padY: 14, gap: 14, margin: 16, maxWidthRatio: 0.62 };
export const CAPTION_HEIGHT = 52;

export class LayoutError extends Error {
  constructor(message) {
    super(message);
    this.name = "LayoutError";
  }
}

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

/**
 * @param panel     대본의 컷
 * @param positions 인물 id → { x, headTop } (characters.mjs 의 castPosition)
 * @param width     컷 가로 폭
 */
export function layoutBubbles(panel, positions, width, opts = BUBBLE) {
  const lines = panel.lines ?? [];
  if (lines.length === 0) return [];
  const top = (panel.caption ? CAPTION_HEIGHT : 0) + opts.margin;
  // 말풍선은 이 컷에 나온 인물 중 가장 높은 머리보다 위에 있어야 한다
  const limit = Math.min(...Object.values(positions).map((p) => p.headTop)) - 10;
  const maxTextWidth = width * opts.maxWidthRatio - opts.padX * 2;

  const bubbles = [];
  let y = top;
  for (const line of lines) {
    const rows = wrapText(line.text, maxTextWidth, opts.fontSize);
    const textW = Math.max(...rows.map((row) => textWidth(row, opts.fontSize)));
    const w = Math.ceil(textW + opts.padX * 2);
    const h = rows.length * opts.lineHeight + opts.padY * 2;
    const speaker = positions[line.who];
    const x = clamp(speaker.x - w / 2, opts.margin, width - opts.margin - w);
    // 꼬리는 말풍선 아래 변에서 화자 머리 쪽으로 뻗는다
    const tailBaseX = clamp(speaker.x, x + 24, x + w - 24);
    bubbles.push({
      who: line.who,
      x,
      y,
      w,
      h,
      rows,
      tail: { baseX: tailBaseX, baseY: y + h, tipX: speaker.x, tipY: speaker.headTop - 6 },
    });
    y += h + opts.gap;
  }
  // 같은 사람이 연달아 말하면 마지막 말풍선에만 꼬리를 단다(앞 꼬리가 뒤 말풍선을 가로지르지 않게)
  for (let i = 0; i < bubbles.length - 1; i++) {
    if (bubbles[i].who === bubbles[i + 1].who) bubbles[i].tail = null;
  }
  const bottom = y - opts.gap;
  if (bottom > limit) {
    throw new LayoutError(
      `컷 ${panel.id}: 말풍선이 들어갈 자리가 모자랍니다(필요 ${Math.ceil(bottom)}px, 인물 머리 위 한계 ${Math.floor(limit)}px). 대사를 줄이거나 컷 높이를 늘리세요.`,
    );
  }
  return bubbles;
}
