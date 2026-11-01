import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { fetchRobots, isAllowed, parseRobots } from "../src/robots.mjs";

const SAMPLE = `
# 주석은 무시
User-agent: *
Disallow: /private/
Allow: /private/public.html
Disallow: /*.json$

User-agent: SiteAnalyzer
User-agent: OtherBot
Disallow: /no-analyzer/
`;

describe("robots.txt 파싱", () => {
  it("User-agent 그룹과 규칙을 나눈다", () => {
    const groups = parseRobots(SAMPLE);
    assert.equal(groups.length, 2);
    assert.deepEqual(groups[0].agents, ["*"]);
    assert.equal(groups[0].rules.length, 3);
    assert.deepEqual(groups[1].agents, ["siteanalyzer", "otherbot"]);
  });
  it("빈 Disallow 는 규칙으로 저장하지 않는다", () => {
    const groups = parseRobots("User-agent: *\nDisallow:\n");
    assert.deepEqual(groups[0].rules, []);
  });
});

describe("허용 여부 판정", () => {
  const groups = parseRobots(SAMPLE);
  it("* 그룹 규칙을 따른다", () => {
    assert.equal(isAllowed(groups, "/", "GenericBot"), true);
    assert.equal(isAllowed(groups, "/private/secret", "GenericBot"), false);
  });
  it("더 길게 일치하는 Allow 가 이긴다", () => {
    assert.equal(isAllowed(groups, "/private/public.html", "GenericBot"), true);
  });
  it("* 와 $ 패턴을 지원한다", () => {
    assert.equal(isAllowed(groups, "/data/list.json", "GenericBot"), false);
    assert.equal(isAllowed(groups, "/data/list.json?x=1", "GenericBot"), true);
  });
  it("도구 이름과 같은 그룹이 있으면 그 그룹만 쓴다(대소문자 무시)", () => {
    assert.equal(isAllowed(groups, "/no-analyzer/a", "SiteAnalyzer"), false);
    assert.equal(isAllowed(groups, "/private/secret", "SiteAnalyzer"), true);
  });
  it("규칙이 없으면 모두 허용", () => {
    assert.equal(isAllowed([], "/anything", "SiteAnalyzer"), true);
  });
});

describe("robots.txt 가져오기", () => {
  const fakeFetch = (status, body = "") => async () => new Response(body, { status });
  it("404 면 제한 없음", async () => {
    const r = await fetchRobots("https://ex.com", "UA", fakeFetch(404));
    assert.equal(r.status, "missing");
    assert.equal(isAllowed(r.groups, "/", "SiteAnalyzer"), true);
  });
  it("5xx 면 안전하게 전부 금지", async () => {
    const r = await fetchRobots("https://ex.com", "UA", fakeFetch(503));
    assert.equal(r.status, "error");
    assert.equal(isAllowed(r.groups, "/", "SiteAnalyzer"), false);
  });
  it("네트워크 오류도 전부 금지", async () => {
    const r = await fetchRobots("https://ex.com", "UA", async () => {
      throw new Error("연결 실패");
    });
    assert.equal(isAllowed(r.groups, "/", "SiteAnalyzer"), false);
  });
  it("User-Agent 헤더에 도구 이름을 담아 요청한다", async () => {
    let sent;
    await fetchRobots("https://ex.com/a/b", "SiteAnalyzer/1.0", async (url, init) => {
      sent = { url, ua: init.headers["user-agent"] };
      return new Response("User-agent: *\nDisallow: /x", { status: 200 });
    });
    assert.deepEqual(sent, { url: "https://ex.com/robots.txt", ua: "SiteAnalyzer/1.0" });
  });
});
