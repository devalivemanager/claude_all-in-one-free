import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { EpisodeError, loadEpisode, validateEpisode } from "../src/script.mjs";
import { sampleEpisode } from "./helpers.mjs";

const hasError = (errors, text) => errors.some((e) => e.includes(text));

describe("대본 검증", () => {
  it("올바른 대본은 오류가 없다", () => {
    assert.deepEqual(validateEpisode(sampleEpisode()), []);
  });

  it("예제 회차(episodes/ep01.json)도 통과한다", async () => {
    const ep = await loadEpisode(new URL("../episodes/ep01.json", import.meta.url).pathname);
    assert.equal(ep.panels.length, 6);
  });

  it("등장인물 목록에 없는 인물은 경로와 함께 알린다", () => {
    const ep = sampleEpisode();
    ep.panels[0].cast[1].who = "zzz";
    assert.ok(hasError(validateEpisode(ep), "panels[0].cast[1].who"));
  });

  it("컷에 나오지 않는 사람의 대사는 막는다", () => {
    const ep = sampleEpisode();
    ep.panels[0].cast = [{ who: "b", x: 0.5, expression: "neutral" }];
    assert.ok(hasError(validateEpisode(ep), "panels[0].lines[0].who"));
  });

  it("컷 id 중복, 잘못된 색, 머리 모양, 표정을 모두 한 번에 모아 알린다", () => {
    const ep = sampleEpisode();
    ep.characters.a.look.hair = "brown";
    ep.characters.b.look.hairStyle = "mohawk";
    ep.panels.push({ ...ep.panels[0], cast: [{ who: "a", x: 0.5, expression: "angry" }] });
    const errors = validateEpisode(ep);
    assert.ok(hasError(errors, "characters.a.look.hair"));
    assert.ok(hasError(errors, "characters.b.look.hairStyle"));
    assert.ok(hasError(errors, "panels[1].id"));
    assert.ok(hasError(errors, "panels[1].cast[0].expression"));
    assert.ok(errors.length >= 4);
  });

  it("대사 60자 초과와 빈 대사를 막는다", () => {
    const ep = sampleEpisode();
    ep.panels[0].lines = [{ who: "a", text: "가".repeat(61) }, { who: "a", text: "  " }];
    const errors = validateEpisode(ep);
    assert.ok(hasError(errors, "lines[0].text"));
    assert.ok(hasError(errors, "lines[1].text"));
  });

  it("60자 대사는 통과한다(경계)", () => {
    const ep = sampleEpisode();
    ep.panels[0].lines = [{ who: "a", text: "가".repeat(60) }];
    assert.equal(validateEpisode(ep).filter((e) => e.includes("lines")).length, 0);
  });

  for (const style of ["유명 작가 화풍으로", "그 웹툰 그림체", "in the style of someone"]) {
    it(`특정 화풍 흉내 지시를 거부한다: '${style}'`, () => {
      assert.ok(hasError(validateEpisode(sampleEpisode({ style })), "style"));
    });
  }

  it("가로 폭·컷 높이 범위를 지킨다", () => {
    const ep = sampleEpisode({ width: 300 });
    ep.panels[0].height = 100;
    const errors = validateEpisode(ep);
    assert.ok(hasError(errors, "width"));
    assert.ok(hasError(errors, "panels[0].height"));
  });
});

describe("대본 읽기", () => {
  it("JSON 형식 오류와 없는 파일을 EpisodeError 로 알린다", async () => {
    const dir = await mkdtemp(join(tmpdir(), "webtoon-"));
    const bad = join(dir, "bad.json");
    await writeFile(bad, "{ 제목: ");
    await assert.rejects(loadEpisode(bad), (e) => e instanceof EpisodeError && e.message.includes("JSON 형식 오류"));
    await assert.rejects(loadEpisode(join(dir, "none.json")), (e) => e instanceof EpisodeError && e.message.includes("찾을 수 없습니다"));
  });
});
