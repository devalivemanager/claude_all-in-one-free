import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { buildPanelPrompt, NO_TEXT_RULE } from "../src/prompt.mjs";
import { sampleEpisode } from "./helpers.mjs";

describe("컷별 이미지 프롬프트", () => {
  const ep = sampleEpisode();
  ep.panels.push({ id: "p2", height: 480, background: "night", scene: "밤 사무실", cast: [{ who: "a", x: 0.5, expression: "tired" }], lines: [] });

  it("모든 컷에 설정표의 외모 설명을 글자 그대로 넣는다(캐릭터 일관성)", () => {
    for (const panel of ep.panels) {
      const prompt = buildPanelPrompt(ep, panel);
      for (const c of panel.cast) assert.ok(prompt.includes(ep.characters[c.who].desc), `${panel.id} 에 ${c.who} 설명 없음`);
    }
  });

  it("그림에 글자·말풍선을 넣지 말라는 규칙을 항상 붙인다", () => {
    for (const panel of ep.panels) assert.ok(buildPanelPrompt(ep, panel).includes(NO_TEXT_RULE));
  });

  it("대사는 프롬프트에 넣지 않는다(대사는 코드로 얹음)", () => {
    assert.ok(!buildPanelPrompt(ep, ep.panels[0]).includes("안녕하세요"));
  });

  it("위치와 표정을 한국어로 적는다", () => {
    const prompt = buildPanelPrompt(ep, ep.panels[0]);
    assert.match(prompt, /위치: 왼쪽 \/ 표정: 웃는 얼굴/);
    assert.match(prompt, /위치: 오른쪽 \/ 표정: 무표정/);
  });

  it("인물이 없는 컷은 '등장인물: 없음'", () => {
    assert.match(buildPanelPrompt(ep, { ...ep.panels[0], cast: [] }), /등장인물: 없음/);
  });
});
