// 이번에 더한 기능: 영어 프롬프트(--prompt-lang en), 콘티 표(storyboard.md), 기획 스킬(webtoon-planner)
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main, parseArgs } from "../src/cli.mjs";
import { buildPanelPrompt, NO_TEXT_RULE_EN } from "../src/prompt.mjs";
import { buildStoryboard } from "../src/render.mjs";
import { validatePromptLang } from "../src/script.mjs";
import { sampleEpisode } from "./helpers.mjs";

const EP01 = new URL("../episodes/ep01.json", import.meta.url).pathname;
const quiet = () => {
  const out = [];
  const err = [];
  return { log: (m) => out.push(m), error: (m) => err.push(m), out, err };
};
const HANGUL = /[가-힣]/;

function englishEpisode() {
  const ep = sampleEpisode({ style_en: "clean lines, bright colors" });
  ep.characters.a.desc_en = "short brown hair, blue shirt";
  ep.characters.b.desc_en = "long black hair, pink shirt";
  ep.panels[0].scene_en = "two people talking in an office";
  return ep;
}

describe("영어 프롬프트", () => {
  it("영어 외모 설명을 글자 그대로 넣고, 글자 금지 규칙을 영어로 붙인다", () => {
    const ep = englishEpisode();
    const prompt = buildPanelPrompt(ep, ep.panels[0], "en");
    assert.ok(prompt.includes("short brown hair, blue shirt"));
    assert.ok(prompt.includes("long black hair, pink shirt"));
    assert.ok(prompt.includes(NO_TEXT_RULE_EN));
    assert.match(prompt, /position: left \/ expression: smiling/);
  });

  it("영어 이름(name_en)이 있으면 영어 프롬프트에 한글이 하나도 없다", () => {
    const ep = englishEpisode();
    ep.characters.a.name_en = "Ga";
    ep.characters.b.name_en = "Na";
    const prompt = buildPanelPrompt(ep, ep.panels[0], "en");
    assert.ok(!HANGUL.test(prompt), prompt);
  });

  it("영어 이름이 없으면 한국어 이름을 그대로 쓴다(선택 항목)", () => {
    const ep = englishEpisode();
    assert.match(buildPanelPrompt(ep, ep.panels[0], "en"), /- 가: short brown hair/);
  });

  it("기본(ko)은 예전과 같은 한국어 프롬프트", () => {
    const ep = englishEpisode();
    assert.match(buildPanelPrompt(ep, ep.panels[0]), /그림 분위기: 깔끔한 선/);
  });

  it("영어 필드가 빠지면 어디가 빠졌는지 모두 알린다(ko 일 때는 검사하지 않음)", () => {
    const ep = sampleEpisode();
    const errors = validatePromptLang(ep, "en");
    assert.ok(errors.some((e) => e.startsWith("style_en")));
    assert.ok(errors.some((e) => e.startsWith("characters.a.desc_en")));
    assert.ok(errors.some((e) => e.startsWith("panels[0].scene_en")));
    assert.deepEqual(validatePromptLang(ep, "ko"), []);
  });

  it("영어 화풍 설명에도 흉내 지시를 막는다", () => {
    const ep = englishEpisode();
    ep.style_en = "in the style of a famous artist";
    assert.ok(validatePromptLang(ep, "en").some((e) => e.startsWith("style_en")));
  });
});

describe("콘티 표", () => {
  it("컷마다 한 줄이고, 연출·등장·대사·프롬프트가 들어간다", () => {
    const ep = sampleEpisode();
    ep.panels[0].caption = "오후 7시";
    const md = buildStoryboard(ep, [{ id: "p1", prompt: "프롬프트 내용" }]);
    const rows = md.split("\n").filter((l) => l.startsWith("| 1 "));
    assert.equal(rows.length, 1);
    assert.match(rows[0], /배경 office, 높이 520px, 자막 「오후 7시」/);
    assert.match(rows[0], /가\(happy\), 나\(neutral\)/);
    assert.match(rows[0], /가: 안녕하세요/);
    assert.match(rows[0], /프롬프트 내용/);
  });

  it("대사의 | 와 프롬프트의 줄바꿈이 표를 깨지 않는다", () => {
    const ep = sampleEpisode();
    ep.panels[0].lines = [{ who: "a", text: "A | B" }];
    const md = buildStoryboard(ep, [{ id: "p1", prompt: "첫 줄\n둘째 줄" }]);
    const row = md.split("\n").find((l) => l.startsWith("| 1 "));
    assert.ok(row.includes("A \\| B"));
    assert.ok(row.includes("첫 줄<br>둘째 줄"));
    assert.equal(row.split(/(?<!\\)\|/).length, 7, "칸 수가 5개여야 함");
  });
});

describe("CLI 옵션", () => {
  it("--prompt-lang 을 읽고, 모르는 언어는 종료 코드 2", async () => {
    assert.equal(parseArgs(["a.json", "-o", "x", "--prompt-lang", "en"]).promptLang, "en");
    const io = quiet();
    assert.equal(await main([EP01, "-o", join(tmpdir(), "x"), "--prompt-lang", "jp"], {}, io), 2);
    assert.match(io.err[0], /ko 또는 en/);
  });

  it("예제 회차를 영어 프롬프트로 만들면 prompts.md·storyboard.md 에 영어 설명이 들어간다", async () => {
    const out = await mkdtemp(join(tmpdir(), "webtoon-"));
    assert.equal(await main([EP01, "-o", out, "--prompt-lang", "en"], {}, quiet()), 0);
    const prompts = await readFile(join(out, "prompts.md"), "utf8");
    const board = await readFile(join(out, "storyboard.md"), "utf8");
    assert.match(prompts, /junior developer, short brown bob hair, round glasses, blue shirt/);
    assert.match(prompts, /No text, no letters/);
    assert.equal(board.split("\n").filter((l) => /^\| \d+ /.test(l)).length, 6);
  });

  it("영어 필드가 없는 대본에 --prompt-lang en 을 주면 종료 코드 1 과 빠진 곳 목록", async () => {
    const dir = await mkdtemp(join(tmpdir(), "webtoon-"));
    const file = join(dir, "ko-only.json");
    await writeFile(file, JSON.stringify(sampleEpisode()));
    const io = quiet();
    assert.equal(await main([file, "-o", join(dir, "out"), "--prompt-lang", "en"], {}, io), 1);
    assert.match(io.err[0], /style_en/);
  });
});

describe("기획 스킬", () => {
  it("webtoon-planner 스킬에 이름·설명·검증 명령·점검표가 있다", async () => {
    const text = await readFile(new URL("../.claude/skills/webtoon-planner/SKILL.md", import.meta.url), "utf8");
    assert.ok(text.startsWith("---\nname: webtoon-planner\ndescription: "));
    assert.ok(text.includes("node src/cli.mjs episodes/epNN.json -o output/epNN --prompt-lang en"));
    assert.ok(text.includes("끝내기 전 점검"));
  });
});
