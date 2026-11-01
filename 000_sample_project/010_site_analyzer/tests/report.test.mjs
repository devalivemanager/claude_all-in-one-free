import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildChecklist, buildReport, buildSiteSummary, formatBytes, renderMarkdown } from "../src/report.mjs";
import { samplePage, sampleReportBase } from "./helpers/sample-page.mjs";

describe("사이트 요약", () => {
  const pages = [
    samplePage(),
    samplePage({
      url: "https://ex.com/about",
      headings: [{ level: 2, text: "h1 없음" }],
      lang: null,
      landmarks: { header: 1, nav: 1, main: 0, footer: 1 },
      counts: { links: 1, buttons: 0, forms: 1, images: 3, imagesMissingAlt: 2 },
      css: { ...samplePage().css, breakpoints: [{ px: 1024, feature: "min" }, { px: 768, feature: "max" }] },
      apiCalls: ["GET /api/items"],
      timing: { domContentLoadedMs: 80, loadMs: 300, measuredMs: 320 },
    }),
  ];
  const summary = buildSiteSummary(pages);

  it("브레이크포인트·API 는 중복 없이 합친다", () => {
    assert.deepEqual(summary.breakpoints, [
      { px: 768, feature: "max" },
      { px: 1024, feature: "min" },
    ]);
    assert.deepEqual(summary.apiCalls, ["GET /api/items"]);
  });
  it("색상·글꼴 빈도는 페이지를 합산한다", () => {
    assert.deepEqual(summary.fonts, [{ font: "Pretendard", count: 20 }]);
    assert.deepEqual(summary.colors.text, [{ color: "#222222", count: 18 }]);
  });
  it("접근성 문제가 있는 페이지를 모은다", () => {
    assert.equal(summary.accessibility.imagesMissingAlt, 2);
    assert.deepEqual(summary.accessibility.pagesWithoutH1, ["https://ex.com/about"]);
    assert.deepEqual(summary.accessibility.pagesWithoutMain, ["https://ex.com/about"]);
    assert.deepEqual(summary.accessibility.pagesWithoutLang, ["https://ex.com/about"]);
  });
  it("평균 load 시간과 요청 합계를 계산한다", () => {
    assert.equal(summary.averageLoadMs, 200);
    assert.deepEqual({ count: summary.network.count, bytes: summary.network.bytes }, { count: 4, bytes: 6000 });
  });
  it("체크리스트에 발견한 문제와 저작권 주의가 들어간다", () => {
    const list = buildChecklist(summary).join("\n");
    assert.match(list, /768px, 1024px/);
    assert.match(list, /alt 속성이 없는 이미지 2개/);
    assert.match(list, /main 랜드마크가 없는 페이지가 있다\(\/about\)/);
    assert.match(list, /GET \/api\/items/);
    assert.match(list, /복제하지 말고/);
  });
  it("페이지가 하나도 없어도 깨지지 않는다", () => {
    const empty = buildSiteSummary([]);
    assert.equal(empty.pageCount, 0);
    assert.equal(empty.averageLoadMs, null);
    assert.match(buildChecklist(empty).join("\n"), /브레이크포인트를 찾지 못했다/);
  });
});

describe("Markdown 보고서", () => {
  const report = buildReport(sampleReportBase([samplePage({ title: "A | B" })]));
  const md = renderMarkdown(report);

  it("한글 섹션이 순서대로 들어간다", () => {
    const order = ["# 웹사이트 분석 보고서", "## 사이트 요약", "## 다시 만들 때 참고할 점", "## 건너뛴 페이지", "## 페이지별 분석"];
    const positions = order.map((h) => md.indexOf(h));
    assert.ok(positions.every((p) => p >= 0), "모든 섹션이 있어야 한다");
    assert.deepEqual([...positions].sort((a, b) => a - b), positions);
  });
  it("체크리스트는 체크박스 형식이다", () => {
    assert.match(md, /^- \[ \] 반응형:/m);
  });
  it("제목 구조를 들여쓰기로 보여 주고 스크린샷을 링크한다", () => {
    assert.match(md, /^- H1 환영합니다$/m);
    assert.match(md, /^ {2}- H2 소개$/m);
    assert.match(md, /\[모바일 390px\]\(screenshots\/01-mobile\.png\)/);
  });
  it("표 안의 | 문자는 이스케이프한다", () => {
    assert.match(md, /robots\.txt Disallow \|/);
    assert.doesNotMatch(md, /\| A \| B \|/);
  });
  it("용량을 읽기 쉽게 표시한다", () => {
    assert.equal(formatBytes(0), "0 B");
    assert.equal(formatBytes(512), "512 B");
    assert.equal(formatBytes(1536), "1.5 KB");
    assert.equal(formatBytes(3 * 1024 * 1024), "3.00 MB");
  });
});
