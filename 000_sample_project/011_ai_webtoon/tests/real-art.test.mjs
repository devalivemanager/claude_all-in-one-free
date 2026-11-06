// 실제 그림으로 넘어가기 위한 프롬프트: 흔한 비율, 말풍선 자리, 캐릭터 기준 그림 (docs/실제그림_따라하기.md)
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { castPosition } from "../src/characters.mjs";
import { layoutBubbles } from "../src/layout.mjs";
import { buildCharacterSheetPrompt, buildPanelPrompt, headroomPercent, nearestRatio } from "../src/prompt.mjs";
import { promptsToMarkdown } from "../src/render.mjs";

const ep01 = JSON.parse(await readFile(new URL("../episodes/ep01.json", import.meta.url), "utf8"));

describe("실제 그림용 프롬프트", () => {
  it("픽셀 크기를 가장 가까운 흔한 비율로 바꾼다", () => {
    const cases = [[720, 480, "3:2"], [720, 520, "4:3"], [720, 400, "16:9"], [720, 600, "5:4"], [720, 560, "5:4"] /* 1.286: 5:4(1.25) 가 4:3(1.333) 보다 가깝다 */, [720, 720, "1:1"], [400, 720, "9:16"], [720, 1080, "2:3"], [720, 1200, "9:16"] /* 0.6: 9:16(0.5625) 이 2:3(0.667) 보다 가깝다 */];
    for (const [w, h, want] of cases) assert.equal(nearestRatio(w, h), want, `${w}x${h}`);
  });

  it("대사가 있는 컷에만 말풍선 자리를 비워 두라고 한다(한국어·영어)", () => {
    const talk = ep01.panels.find((p) => p.id === "p1");
    const silent = ep01.panels.find((p) => p.id === "p3");
    assert.match(buildPanelPrompt(ep01, talk), /말풍선 자리: 그림 위쪽 49% 는 단순한 배경으로 비워 둔다/);
    assert.match(buildPanelPrompt(ep01, talk, "en"), /Keep the top 49% of the image as plain, simple background for speech bubbles/);
    assert.doesNotMatch(buildPanelPrompt(ep01, silent), /말풍선 자리/);
    assert.match(buildPanelPrompt(ep01, talk, "en"), /aspect ratio 3:2 \(720x480\)/);
  });

  // 프롬프트가 비워 두라는 범위가 실제 말풍선이 놓이는 범위를 덮어야 그림이 가려지지 않는다
  it("예제 회차의 모든 말풍선은 프롬프트가 비워 두라고 한 위쪽 범위 안에 있다", () => {
    for (const panel of ep01.panels.filter((p) => (p.lines ?? []).length > 0)) {
      const positions = Object.fromEntries(panel.cast.map((c) => [c.who, castPosition(c, panel.height, ep01.width)]));
      const bottom = Math.max(...layoutBubbles(panel, positions, ep01.width).map((b) => b.y + b.h));
      assert.ok(bottom <= (headroomPercent(ep01, panel) / 100) * panel.height, `${panel.id}: 말풍선 아래끝 ${Math.round(bottom)}px`);
    }
  });

  it("캐릭터 기준 그림 프롬프트: 외모 설명 그대로, 흰 배경 전신, 글자 금지", () => {
    const ko = buildCharacterSheetPrompt(ep01, "hana");
    assert.ok(ko.includes(ep01.characters.hana.desc));
    assert.match(ko, /전신, 정면으로 서 있음, 무표정, 흰 단색 배경, 한 사람만/);
    assert.match(ko, /글자, 숫자, 말풍선을 넣지 않는다/);
    const en = buildCharacterSheetPrompt(ep01, "hana", "en");
    assert.ok(en.includes(ep01.characters.hana.desc_en));
    assert.match(en, /full body, standing, front view/);
  });

  it("prompts.md 는 캐릭터 기준 그림(인물 수만큼) → 컷 그림 순서다", () => {
    const md = promptsToMarkdown(ep01, ep01.panels.map((p) => ({ id: p.id, prompt: buildPanelPrompt(ep01, p, "en") })), "en");
    const sheets = md.match(/파일 이름 `ref_\w+\.png`/g) ?? [];
    assert.equal(sheets.length, Object.keys(ep01.characters).length);
    assert.ok(md.indexOf("## 1) 캐릭터 기준 그림") < md.indexOf("## 2) 컷 그림"));
    assert.match(md, /^비율 16:9 · 크기 720×400px · 파일 이름 `p3\.png`$/m);
    assert.ok(md.includes(ep01.characters.hana.desc_en));
  });
});
