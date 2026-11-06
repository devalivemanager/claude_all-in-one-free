// 다른 출처 경계 테스트: 두 개의 로컬 서버(A = 분석 대상, B = 다른 출처)로 확인한다 (playwright 가 없으면 건너뜀)
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import http from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { loadPlaywright } from "../src/browser.mjs";
import { analyzeSite } from "../src/crawler.mjs";

const playwright = await loadPlaywright();
const skip = playwright ? false : "playwright 가 설치되어 있지 않아 건너뜀";
const CLI = fileURLToPath(new URL("../src/cli.mjs", import.meta.url));

/** 요청 경로를 기록하는 작은 서버를 띄운다 */
function serve(handler) {
  const requests = [];
  const server = http.createServer((req, res) => {
    requests.push(req.url);
    handler(req, res);
  });
  return new Promise((resolve) =>
    server.listen(0, "127.0.0.1", () =>
      resolve({ requests, url: `http://127.0.0.1:${server.address().port}`, close: () => new Promise((r) => server.close(r)) }),
    ),
  );
}

describe("다른 출처 경계", { skip }, () => {
  let a;
  let b;
  let outDir;
  let report;

  before(async () => {
    b = await serve((req, res) => {
      if (req.url === "/b.css") {
        res.writeHead(200, { "content-type": "text/css" });
        res.end("@media (min-width: 999px) { body { color: red } }");
        return;
      }
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end("<html><body>B</body></html>");
    });
    a = await serve((req, res) => {
      if (req.url === "/robots.txt") return res.writeHead(404).end();
      if (req.url === "/go") return res.writeHead(302, { location: `${b.url}/landing` }).end();
      if (req.url === "/missing.html") return res.writeHead(404, { "content-type": "text/html" }).end("없음");
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end(`<html lang="ko"><head><title>A</title>
<link rel="stylesheet" href="${b.url}/b.css"><style>@media (max-width: 600px) { p { margin: 0 } }</style></head>
<body><a href="/go">이동</a> <a href="${b.url}/direct">B 직접</a> <a href="/missing.html">없음</a></body></html>`);
    });
    outDir = await mkdtemp(path.join(tmpdir(), "site-analyzer-cross-"));
    report = await analyzeSite({ url: `${a.url}/`, outDir, delayMs: 0 });
  });
  after(async () => {
    await a?.close();
    await b?.close();
    if (outDir) await rm(outDir, { recursive: true, force: true });
  });

  it("다른 출처 스타일시트의 @media 는 브레이크포인트에 넣지 않는다", () => {
    assert.deepEqual(report.pages[0].css.breakpoints, [{ px: 600, feature: "max" }]);
  });

  it("다른 출처 링크는 따라가지 않는다", () => {
    assert.ok(!b.requests.includes("/direct"));
  });

  // 브라우저가 리디렉트를 따라가므로 B 에 요청은 한 번 간다(README 「수집 항목과 한계」). 분석은 하지 않는다.
  it("다른 출처로 리디렉트되면 분석하지 않고 건너뛴 페이지에 이유를 남긴다", () => {
    assert.equal(report.pages.length, 1);
    assert.deepEqual(report.skipped, [
      { url: `${a.url}/go`, reason: `다른 출처로 이동됨(${b.url}/landing)` },
      { url: `${a.url}/missing.html`, reason: "HTTP 404" },
    ]);
  });

  it("분석한 페이지가 없으면 CLI 종료 코드는 1", async () => {
    const out = path.join(outDir, "empty");
    const err = await promisify(execFile)(process.execPath, [CLI, `${a.url}/missing.html`, "--out", out]).catch((e) => e);
    assert.equal(err.code, 1);
    assert.match(err.stdout, /페이지 0개 분석, 1개 건너뜀/);
  });
});
