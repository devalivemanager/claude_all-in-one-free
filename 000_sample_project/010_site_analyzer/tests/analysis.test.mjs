import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { detectTech, listApiCalls, summarizeRequests } from "../src/analysis.mjs";

describe("기술 스택 단서", () => {
  it("응답 헤더와 마커를 근거와 함께 나열한다", () => {
    const tech = detectTech({
      headers: { server: "nginx", "x-powered-by": "Express" },
      markers: { react: "전역 window.React", next: "#__next 요소", vue: null, gsap: "전역 window.gsap" },
    });
    assert.deepEqual(
      tech.map((t) => t.name),
      ["서버: nginx", "백엔드: Express", "React", "Next.js", "GSAP"],
    );
    assert.equal(tech[2].evidence, "전역 window.React");
  });
  it("단서가 없으면 빈 목록", () => {
    assert.deepEqual(detectTech({}), []);
  });
});

describe("네트워크 요청 요약", () => {
  const records = [
    { url: "https://ex.com/", type: "document", method: "GET", bytes: 1000 },
    { url: "https://ex.com/a.png", type: "image", method: "GET", bytes: 5000 },
    { url: "https://ex.com/b.png", type: "image", method: "GET", bytes: 3000 },
    { url: "https://ex.com/api/items?page=2&token=secret", type: "fetch", method: "GET", bytes: 200 },
    { url: "https://ex.com/api/items", type: "xhr", method: "POST", bytes: -1 },
    { url: "https://api.other.com/v1/me", type: "fetch", method: "GET", bytes: 0 },
  ];
  it("종류별 개수·용량을 용량 큰 순으로 묶는다(음수 용량은 0)", () => {
    const s = summarizeRequests(records);
    assert.deepEqual(s.total, { count: 6, bytes: 9200 });
    assert.deepEqual(s.byType[0], { type: "image", count: 2, bytes: 8000 });
    assert.deepEqual(s.byType.find((t) => t.type === "xhr"), { type: "xhr", count: 1, bytes: 0 });
  });
  it("API 호출은 쿼리를 빼고 메서드+경로로, 다른 출처는 출처를 붙인다", () => {
    assert.deepEqual(listApiCalls(records, "https://ex.com/"), [
      "GET /api/items",
      "GET https://api.other.com/v1/me",
      "POST /api/items",
    ]);
  });
});
