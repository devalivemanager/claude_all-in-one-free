import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseCliArgs } from "../src/args.mjs";

describe("명령행 인자", () => {
  it("기본값을 채운다", () => {
    assert.deepEqual(parseCliArgs(["https://ex.com"]), {
      help: false,
      url: "https://ex.com",
      outDir: "output",
      maxPages: 5,
      sameOrigin: false,
      delayMs: 1000,
    });
  });
  it("옵션을 읽는다", () => {
    const o = parseCliArgs(["http://localhost:3000/", "--out", "out2", "--max-pages", "3", "--same-origin", "--delay", "1500"]);
    assert.equal(o.outDir, "out2");
    assert.equal(o.maxPages, 3);
    assert.equal(o.sameOrigin, true);
    assert.equal(o.delayMs, 1500);
  });
  it("--help", () => {
    assert.deepEqual(parseCliArgs(["--help"]), { help: true });
  });
  it("잘못된 입력은 한글 오류를 낸다", () => {
    assert.throws(() => parseCliArgs([]), /URL 을 하나/);
    assert.throws(() => parseCliArgs(["ex.com"]), /http:\/\//);
    assert.throws(() => parseCliArgs(["https://ex.com", "--max-pages", "0"]), /max-pages/);
    assert.throws(() => parseCliArgs(["https://ex.com", "--max-pages", "51"]), /max-pages/); // 최대 50페이지
    assert.equal(parseCliArgs(["https://ex.com", "--max-pages", "50"]).maxPages, 50);
    assert.throws(() => parseCliArgs(["https://ex.com", "--delay", "100"]), /500ms 이상/);
    assert.throws(() => parseCliArgs(["https://ex.com", "--ignore-robots"]), /ignore-robots/);
  });
});
