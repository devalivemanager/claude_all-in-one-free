// 그림 파일 넣기(--images): 사람이 이미지 AI 로 만든 그림을 컷 id 이름으로 폴더에 모아 컷에 깐다
import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, truncate, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { main, parseArgs } from "../src/cli.mjs";
import { createFolderPainter, MAX_IMAGE_BYTES, sniffImageMime } from "../src/painters.mjs";
import { buildEpisode, promptsToMarkdown } from "../src/render.mjs";
import { sampleEpisode } from "./helpers.mjs";

// 형식 판별에 필요한 앞부분만 가진 가짜 이미지(내용 확인은 브라우저 PNG 생성으로 따로 했다)
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3, 4]);
const JPEG = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3, 4]);
const WEBP = Buffer.concat([Buffer.from("RIFF"), Buffer.from([0, 0, 0, 0]), Buffer.from("WEBPVP8 ")]);
const EP01 = new URL("../episodes/ep01.json", import.meta.url).pathname;

function captureLog() {
  const out = [];
  const err = [];
  return { log: (m) => out.push(m), error: (m) => err.push(m), out, err };
}

describe("그림 파일 넣기(--images)", () => {
  let root;
  before(async () => {
    root = await mkdtemp(join(tmpdir(), "webtoon-images-"));
  });
  after(async () => {
    await rm(root, { recursive: true, force: true });
  });
  /** 파일 목록 { 이름: 내용 } 으로 새 폴더를 만든다 */
  async function folder(name, files) {
    const dir = join(root, name);
    await mkdir(dir, { recursive: true });
    for (const [file, body] of Object.entries(files)) await writeFile(join(dir, file), body);
    return dir;
  }

  it("파일 앞부분으로 PNG·JPEG·WebP 를 알아보고, 그 밖은 null", () => {
    assert.equal(sniffImageMime(PNG), "image/png");
    assert.equal(sniffImageMime(JPEG), "image/jpeg");
    assert.equal(sniffImageMime(WEBP), "image/webp");
    assert.equal(sniffImageMime(Buffer.from("<svg></svg>")), null);
    assert.equal(sniffImageMime(Buffer.alloc(0)), null);
  });

  it("컷 id 이름의 파일을 data URI 로 돌려준다. 형식은 확장자가 아니라 내용으로 정한다", async () => {
    const dir = await folder("ok", { "p1.jpg": PNG });
    const href = await createFolderPainter({ dir }).paint({ panel: { id: "p1" } });
    assert.equal(href, `data:image/png;base64,${PNG.toString("base64")}`);
  });

  it("그림이 깔린 컷은 코드 그림 대신 <image> 를 쓰고, 말풍선은 그대로 얹는다", async () => {
    const dir = await folder("render", { "p1.webp": WEBP });
    const { html, warnings } = await buildEpisode(sampleEpisode(), createFolderPainter({ dir }));
    assert.deepEqual(warnings, []);
    assert.match(html, /<image href="data:image\/webp;base64,/);
    assert.match(html, /class="bubble"/);
    assert.match(html, /그림: 그림 파일/);
  });

  it("파일이 없는 컷은 코드 그림으로 대신하고 경고에 컷 id 를 남긴다", async () => {
    const dir = await folder("empty", {});
    const { html, warnings } = await buildEpisode(sampleEpisode(), createFolderPainter({ dir }));
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], /컷 p1: .*그림 파일이 없습니다\(p1\.png\/\.jpg\/\.jpeg\/\.webp\)/);
    assert.doesNotMatch(html, /<image /);
  });

  it("같은 컷 파일이 여러 개, 이미지가 아닌 파일, 너무 큰 파일은 실패로 본다", async () => {
    const painter = (dir) => createFolderPainter({ dir });
    const dup = await folder("dup", { "p1.png": PNG, "p1.webp": WEBP });
    await assert.rejects(painter(dup).paint({ panel: { id: "p1" } }), /여러 개입니다: p1\.png, p1\.webp/);
    const fake = await folder("fake", { "p1.png": "<svg onload=alert(1)></svg>" });
    await assert.rejects(painter(fake).paint({ panel: { id: "p1" } }), /이미지 파일이 아닙니다/);
    const big = await folder("big", { "p1.png": PNG });
    await truncate(join(big, "p1.png"), MAX_IMAGE_BYTES + 1);
    await assert.rejects(painter(big).paint({ panel: { id: "p1" } }), /너무 큽니다/);
    const edge = await folder("edge", { "p1.png": PNG });
    await truncate(join(edge, "p1.png"), MAX_IMAGE_BYTES); // 정확히 10MB 는 통과
    assert.match(await painter(edge).paint({ panel: { id: "p1" } }), /^data:image\/png;base64,/);
  });

  it("파일 이름으로 쓸 수 없는 컷 id 는 폴더 밖을 읽지 않고 실패한다", async () => {
    await folder("outside", { "secret.png": PNG });
    const dir = await folder("inner", {});
    for (const id of ["../outside/secret", "a/b", "p 1", ""]) {
      await assert.rejects(createFolderPainter({ dir }).paint({ panel: { id } }), /파일 이름으로 쓸 수 없습니다/);
    }
  });

  it("prompts.md 에 컷별 크기와 파일 이름을 적는다", () => {
    const md = promptsToMarkdown(sampleEpisode(), [{ id: "p1", prompt: "장면" }]);
    assert.match(md, /^비율 4:3 · 크기 720×520px · 파일 이름 `p1\.png`$/m);
    assert.match(md, /--images <폴더>/);
  });

  it("CLI 인자: --images 는 폴더가 필요하고 --painter api 와 함께 쓸 수 없다", () => {
    assert.equal(parseArgs(["a.json", "-o", "o", "--images", "art"]).images, "art");
    assert.throws(() => parseArgs(["a.json", "-o", "o", "--images"]), /그림 폴더를 적으세요/);
    assert.throws(() => parseArgs(["a.json", "-o", "o", "--images", "--png"]), /그림 폴더를 적으세요/);
    assert.throws(() => parseArgs(["a.json", "-o", "o", "--images", "art", "--painter", "api"]), /함께 쓸 수 없습니다/);
  });

  it("CLI: 예제 회차 6컷 중 5컷만 그림이 있으면 경고 1건으로 끝나고, 폴더가 없으면 종료 코드 1", async () => {
    const files = Object.fromEntries(["p1", "p2", "p3", "p4", "p5"].map((id) => [`${id}.png`, PNG]));
    const dir = await folder("ep01-art", files);
    const out = join(root, "out");
    const io = captureLog();
    assert.equal(await main([EP01, "-o", out, "--images", dir], {}, io), 0);
    const html = await readFile(join(out, "index.html"), "utf8");
    assert.equal((html.match(/<image /g) ?? []).length, 5);
    assert.equal(io.err.length, 1);
    assert.match(io.err[0], /경고: 컷 p6: .*그림 파일이 없습니다/);
    assert.match(io.out.at(-1), /컷 6개, 말풍선 8개, 경고 1건/);

    const io2 = captureLog();
    assert.equal(await main([EP01, "-o", out, "--images", join(root, "no-such")], {}, io2), 1);
    assert.match(io2.err[0], /그림 폴더가 없습니다/);
  });
});
