import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main, parseArgs } from "../src/cli.mjs";
import { sampleEpisode } from "./helpers.mjs";

function captureLog() {
  const out = [];
  const err = [];
  return { log: (m) => out.push(m), error: (m) => err.push(m), out, err };
}
const EP01 = new URL("../episodes/ep01.json", import.meta.url).pathname;

describe("CLI", () => {
  it("인자 해석", () => {
    assert.deepEqual(parseArgs(["a.json", "-o", "out", "--png"]), { input: "a.json", out: "out", png: true, painter: "svg", promptLang: "ko" });
    assert.throws(() => parseArgs(["a.json"]), /-o/);
    assert.throws(() => parseArgs(["a.json", "-o", "x", "--painter", "dall"]), /svg 또는 api/);
  });

  it("잘못된 인자는 종료 코드 2", async () => {
    const io = captureLog();
    assert.equal(await main(["--zzz"], {}, io), 2);
    assert.match(io.err[0], /사용법/);
  });

  it("예제 회차로 index.html 과 prompts.md 를 만든다", async () => {
    const out = await mkdtemp(join(tmpdir(), "webtoon-"));
    const io = captureLog();
    assert.equal(await main([EP01, "-o", out], {}, io), 0);
    const html = await readFile(join(out, "index.html"), "utf8");
    const prompts = await readFile(join(out, "prompts.md"), "utf8");
    assert.equal((html.match(/<figure /g) ?? []).length, 6);
    assert.equal((prompts.match(/^## p\d/gm) ?? []).length, 6);
    assert.match(io.out.at(-1), /컷 6개, 말풍선 8개, 경고 0건/);
  });

  it("대본 오류는 종료 코드 1 과 오류 목록", async () => {
    const dir = await mkdtemp(join(tmpdir(), "webtoon-"));
    const bad = join(dir, "bad.json");
    await writeFile(bad, JSON.stringify(sampleEpisode({ style: "누구 화풍으로" })));
    const io = captureLog();
    assert.equal(await main([bad, "-o", join(dir, "out")], {}, io), 1);
    assert.match(io.err[0], /style/);
  });

  it("--painter api 인데 키가 없으면 종료 코드 1", async () => {
    const io = captureLog();
    assert.equal(await main([EP01, "-o", join(tmpdir(), "x"), "--painter", "api"], {}, io), 1);
    assert.match(io.err[0], /IMAGE_API/);
  });
});
