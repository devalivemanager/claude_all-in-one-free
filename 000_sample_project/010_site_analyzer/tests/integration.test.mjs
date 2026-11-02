// 로컬 픽스처 사이트를 실제 브라우저로 분석하는 통합 테스트 (playwright 가 없으면 건너뜀)
import assert from "node:assert/strict";
import { access, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, describe, it } from "node:test";
import { loadPlaywright } from "../src/browser.mjs";
import { analyzeSite, RobotsBlockedError } from "../src/crawler.mjs";
import { startFixtureServer } from "./helpers/fixture-server.mjs";

const playwright = await loadPlaywright();
const skip = playwright ? false : "playwright 가 설치되어 있지 않아 건너뜀";

describe("픽스처 사이트 분석", { skip }, () => {
  let fixture;
  let outDir;
  let report;

  before(async () => {
    fixture = await startFixtureServer();
    outDir = await mkdtemp(path.join(tmpdir(), "site-analyzer-"));
    report = await analyzeSite({ url: fixture.url, outDir, maxPages: 5, delayMs: 300 });
  });
  after(async () => {
    await fixture?.close();
    if (outDir) await rm(outDir, { recursive: true, force: true });
  });

  it("같은 출처 페이지 3개를 BFS 순서로 방문한다", () => {
    assert.deepEqual(
      report.pages.map((p) => new URL(p.url).pathname),
      ["/", "/about.html", "/contact.html"],
    );
  });

  it("robots.txt 로 금지된 /private/ 는 요청조차 하지 않는다", () => {
    assert.ok(!fixture.requests.some((r) => r.path.startsWith("/private")));
    assert.deepEqual(report.skipped, [{ url: `${fixture.url}private/`, reason: "robots.txt Disallow" }]);
  });

  it("모든 요청의 User-Agent 에 도구 이름이 들어 있다", () => {
    assert.ok(fixture.requests.length > 0);
    assert.ok(fixture.requests.every((r) => r.userAgent.includes("SiteAnalyzer")));
  });

  // README: 화면 크기를 바꿔 스크린샷을 찍을 때도 페이지를 다시 불러오지 않는다
  it("스크린샷 3장을 찍어도 페이지마다 문서 요청은 한 번이다", () => {
    const docs = {};
    for (const r of fixture.requests) if (r.path === "/" || r.path.endsWith(".html")) docs[r.path] = (docs[r.path] ?? 0) + 1;
    assert.deepEqual(docs, { "/": 1, "/about.html": 1, "/contact.html": 1 });
  });

  it("페이지 사이에 요청 간격을 둔다", () => {
    const docTimes = fixture.requests.filter((r) => r.path.endsWith(".html") || r.path === "/").map((r) => r.time);
    for (let i = 1; i < docTimes.length; i++) assert.ok(docTimes[i] - docTimes[i - 1] >= 300, "간격이 300ms 이상이어야 한다");
  });

  it("홈 페이지의 구조·접근성 정보를 모은다", () => {
    const home = report.pages[0];
    assert.equal(home.title, "봄날 꽃집 - 홈");
    assert.equal(home.lang, "ko");
    assert.equal(home.description, "분석 도구 테스트용 가상의 꽃집 홈페이지입니다.");
    assert.deepEqual(home.headings, [
      { level: 1, text: "계절을 담은 꽃다발" },
      { level: 2, text: "인기 상품" },
      { level: 2, text: "찾아오시는 길" },
      { level: 3, text: "영업 시간" },
    ]);
    assert.deepEqual(home.landmarks, { header: 1, nav: 1, main: 1, footer: 1 });
    assert.equal(home.counts.images, 2);
    assert.equal(home.counts.imagesMissingAlt, 1);
    assert.equal(home.counts.buttons, 1);
  });

  it("디자인 특징(글꼴·색상·브레이크포인트)을 뽑는다", () => {
    const home = report.pages[0];
    assert.equal(home.fonts[0].font, "Pretendard");
    assert.ok(home.colors.background.some((c) => c.color === "#2f6b4f"));
    assert.ok(home.colors.text.some((c) => c.color === "#333333"));
    assert.deepEqual(home.css.breakpoints, [
      { px: 768, feature: "max" },
      { px: 1024, feature: "min" },
    ]);
    assert.equal(home.css.mediaFeatures.prefersReducedMotion, true);
  });

  it("애니메이션 단서를 찾는다", () => {
    const { animation } = report.pages[0];
    assert.ok(animation.animatedElements >= 1);
    assert.ok(animation.transitionElements >= 1);
    assert.equal(animation.keyframes, 1);
    assert.equal(animation.intersectionObserver, 1);
  });

  it("기술 단서·네트워크·API 호출을 기록한다", () => {
    const home = report.pages[0];
    assert.deepEqual(home.headers, { server: "FixtureServer/1.0", xPoweredBy: "node:http" });
    assert.deepEqual(home.apiCalls, ["GET /api/data"]);
    const types = home.network.byType.map((t) => t.type);
    for (const t of ["document", "stylesheet", "script", "image", "fetch"]) assert.ok(types.includes(t), `${t} 요청이 있어야 한다`);
    assert.ok(home.network.total.bytes > 0);
    assert.ok(home.timing.loadMs >= 0);
  });

  it("폼이 있는 문의 페이지를 구분한다", () => {
    const contact = report.pages.find((p) => p.url.endsWith("/contact.html"));
    assert.equal(contact.counts.forms, 1);
    assert.equal(contact.description, null);
  });

  it("세 가지 화면 크기 스크린샷과 보고서 파일을 만든다", async () => {
    for (const name of ["desktop", "tablet", "mobile"]) {
      await access(path.join(outDir, report.pages[0].screenshots[name]));
    }
    const md = await readFile(path.join(outDir, "report.md"), "utf8");
    assert.match(md, /## 사이트 요약/);
    assert.match(md, /## 다시 만들 때 참고할 점/);
    assert.match(md, /### 1\. 봄날 꽃집 - 홈/);
    assert.match(md, /alt 속성이 없는 이미지 1개/);
    const json = JSON.parse(await readFile(path.join(outDir, "report.json"), "utf8"));
    assert.equal(json.pages.length, 3);
    assert.equal(json.summary.apiCalls[0], "GET /api/data");
  });
});

describe("방문 제한", { skip }, () => {
  it("--max-pages 만큼만 방문한다", async () => {
    const fixture = await startFixtureServer();
    const outDir = await mkdtemp(path.join(tmpdir(), "site-analyzer-"));
    try {
      const report = await analyzeSite({ url: fixture.url, outDir, maxPages: 1, delayMs: 0 });
      assert.equal(report.pages.length, 1);
      assert.ok(!fixture.requests.some((r) => r.path === "/about.html"));
    } finally {
      await fixture.close();
      await rm(outDir, { recursive: true, force: true });
    }
  });
});

describe("robots.txt 금지 경로", () => {
  it("시작 URL 이 금지되어 있으면 페이지를 열지 않고 멈춘다", async () => {
    const fixture = await startFixtureServer();
    const outDir = path.join(tmpdir(), `site-analyzer-blocked-${process.pid}`);
    try {
      await assert.rejects(analyzeSite({ url: `${fixture.url}private/`, outDir, delayMs: 0 }), RobotsBlockedError);
      assert.deepEqual(fixture.requests.map((r) => r.path), ["/robots.txt"]);
      await assert.rejects(access(outDir), "결과 폴더도 만들지 않는다");
    } finally {
      await fixture.close();
    }
  });
});
