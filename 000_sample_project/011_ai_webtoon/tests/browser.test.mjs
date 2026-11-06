// 실제 브라우저로 그려서 확인한다. 글자 폭은 추정값이라, 진짜 글꼴로 그렸을 때 말풍선을 넘지 않는지 본다.
import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { loadPlaywright } from "../src/browser.mjs";
import { main } from "../src/cli.mjs";

const playwright = await loadPlaywright();
const skip = playwright ? false : "playwright 가 설치되어 있지 않아 건너뜀";
const EP01 = new URL("../episodes/ep01.json", import.meta.url).pathname;

describe("브라우저 렌더링", { skip }, () => {
  let browser;
  let page;
  const errors = [];
  before(async () => {
    const out = await mkdtemp(join(tmpdir(), "webtoon-"));
    await main([EP01, "-o", out], {}, { log() {}, error() {} });
    browser = await playwright.chromium.launch();
    page = await browser.newPage({ viewport: { width: 720, height: 900 } });
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(pathToFileURL(join(out, "index.html")).href);
  });
  after(async () => browser?.close());

  it("컷 6개가 화면에 나오고 페이지 오류가 없다", async () => {
    assert.equal(await page.locator("figure svg").count(), 6);
    assert.deepEqual(errors, []);
  });

  it("실제 글꼴로 그린 대사 글자가 모두 말풍선 상자 안에 있다", async () => {
    const results = await page.$$eval("g.bubble", (groups) =>
      groups.map((g) => {
        const [x, y, w, h] = g.dataset.box.split(",").map(Number);
        return [...g.querySelectorAll("text")].map((t) => {
          const b = t.getBBox();
          return { text: t.textContent, inside: b.x >= x && b.x + b.width <= x + w && b.y >= y && b.y + b.height <= y + h, b, box: { x, y, w, h } };
        });
      }).flat(),
    );
    assert.equal(results.length > 0, true);
    const outside = results.filter((r) => !r.inside);
    assert.deepEqual(outside, [], "말풍선을 넘은 글자");
  });
});
