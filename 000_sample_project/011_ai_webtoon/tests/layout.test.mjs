import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { castPosition } from "../src/characters.mjs";
import { CAPTION_HEIGHT, LayoutError, layoutBubbles } from "../src/layout.mjs";

const W = 720;
function positionsFor(panel) {
  return Object.fromEntries(panel.cast.map((c) => [c.who, castPosition(c, panel.height, W)]));
}
const overlaps = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

const panel = {
  id: "p",
  height: 600,
  cast: [
    { who: "a", x: 0.3, expression: "neutral" },
    { who: "b", x: 0.72, expression: "neutral" },
  ],
  lines: [
    { who: "a", text: "건강보험료를 먼저 원 단위로 자른 다음에 곱해야 해요." },
    { who: "a", text: "테스트가 그 중간 단계를 안 보고 있었던 거죠." },
    { who: "b", text: "손으로 다시 계산해 볼게요." },
  ],
};

describe("말풍선 배치", () => {
  const bubbles = layoutBubbles(panel, positionsFor(panel), W);

  it("모든 말풍선이 컷 안에 있다", () => {
    for (const b of bubbles) {
      assert.ok(b.x >= 0 && b.x + b.w <= W, `${b.who} 가로 벗어남`);
      assert.ok(b.y >= 0 && b.y + b.h <= panel.height, `${b.who} 세로 벗어남`);
    }
  });

  it("말풍선끼리 겹치지 않고 읽는 순서대로 위에서 아래로 놓인다", () => {
    for (let i = 0; i < bubbles.length - 1; i++) {
      assert.ok(!overlaps(bubbles[i], bubbles[i + 1]));
      assert.ok(bubbles[i].y < bubbles[i + 1].y);
    }
  });

  it("말풍선은 화자 머리보다 위에 있고, 꼬리 끝은 화자를 가리킨다", () => {
    const pos = positionsFor(panel);
    for (const b of bubbles) {
      assert.ok(b.y + b.h < pos[b.who].headTop, "머리를 가림");
      if (b.tail) {
        assert.equal(b.tail.tipX, pos[b.who].x);
        assert.ok(b.tail.tipY < pos[b.who].headTop);
      }
    }
  });

  it("같은 사람이 연달아 말하면 마지막 말풍선에만 꼬리가 있다", () => {
    assert.equal(bubbles[0].tail, null);
    assert.notEqual(bubbles[1].tail, null);
    assert.notEqual(bubbles[2].tail, null);
  });

  it("자막(caption)이 있으면 그 아래부터 쌓는다", () => {
    const withCaption = layoutBubbles({ ...panel, caption: "오후 7시", lines: panel.lines.slice(2) }, positionsFor(panel), W);
    assert.ok(withCaption[0].y >= CAPTION_HEIGHT);
  });

  it("대사가 넘치면 어느 컷인지와 필요한 높이를 알려 준다", () => {
    const crowded = { ...panel, id: "p9", height: 300, lines: panel.lines };
    assert.throws(() => layoutBubbles(crowded, positionsFor(crowded), W), (e) => e instanceof LayoutError && e.message.includes("컷 p9"));
  });

  it("대사가 없으면 빈 배열", () => {
    assert.deepEqual(layoutBubbles({ ...panel, lines: [] }, positionsFor(panel), W), []);
  });
});
