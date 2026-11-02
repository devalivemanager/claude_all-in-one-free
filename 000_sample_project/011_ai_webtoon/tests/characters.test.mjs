import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { drawBackground, drawCharacter } from "../src/characters.mjs";
import { sampleEpisode } from "./helpers.mjs";

const ep = sampleEpisode();
const cast = { who: "a", x: 0.3, expression: "happy" };

describe("캐릭터 그리기", () => {
  it("같은 설정표·같은 입력이면 항상 같은 그림(캐릭터 일관성)", () => {
    assert.equal(drawCharacter(ep.characters.a, cast, 520, 720), drawCharacter(ep.characters.a, cast, 520, 720));
  });

  it("설정표의 머리·피부·옷 색을 그대로 쓴다", () => {
    const svg = drawCharacter(ep.characters.a, cast, 520, 720);
    for (const color of Object.values(ep.characters.a.look).filter((v) => String(v).startsWith("#"))) {
      assert.ok(svg.includes(color), `${color} 없음`);
    }
  });

  it("앞머리는 얼굴(머리 원)보다 나중에 그린다 — 먼저 그리면 얼굴에 가려 안 보인다", () => {
    const svg = drawCharacter(ep.characters.a, cast, 520, 720);
    const headAt = svg.indexOf(`<circle cx="216" `);
    const hairAt = svg.indexOf('class="hair"');
    assert.ok(headAt >= 0 && hairAt > headAt, "앞머리가 얼굴 뒤에 있음");
  });

  it("표정마다 얼굴이 다르다", () => {
    const faces = new Set(["neutral", "happy", "sad", "surprised", "tired"].map((expression) => drawCharacter(ep.characters.a, { ...cast, expression }, 520, 720)));
    assert.equal(faces.size, 5);
  });

  it("긴 머리는 옆머리를 얼굴 뒤에 그린다", () => {
    const svg = drawCharacter(ep.characters.b, { who: "b", x: 0.7, expression: "neutral" }, 520, 720);
    const sideHairAt = svg.indexOf(`<rect`, svg.indexOf(`fill="${ep.characters.b.look.skin}"`) + 1);
    assert.ok(svg.indexOf(`fill="${ep.characters.b.look.hair}"`) < svg.indexOf(`<circle cx="504"`));
    assert.ok(sideHairAt > 0);
  });

  it("배경 종류마다 다른 그림이 나온다", () => {
    const kinds = new Set(["office", "night", "monitor", "plain"].map((k) => drawBackground(k, 720, 480)));
    assert.equal(kinds.size, 4);
  });
});
