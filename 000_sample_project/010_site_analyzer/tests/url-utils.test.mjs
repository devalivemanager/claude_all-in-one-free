import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { isInScope, isSameOrigin, looksLikePage, normalizeUrl, pathWithQuery, scopePrefix } from "../src/url-utils.mjs";

describe("URL 정규화", () => {
  it("상대 경로를 풀고 #해시를 지운다", () => {
    assert.equal(normalizeUrl("about.html#story", "https://ex.com/a/"), "https://ex.com/a/about.html");
  });
  it("http/https 가 아니면 null", () => {
    assert.equal(normalizeUrl("mailto:a@ex.com"), null);
    assert.equal(normalizeUrl("javascript:void(0)"), null);
    assert.equal(normalizeUrl("이상한 값"), null);
  });
  it("기본 포트는 생략된다", () => {
    assert.equal(normalizeUrl("https://ex.com:443/x"), "https://ex.com/x");
  });
});

describe("같은 출처·범위 판정", () => {
  it("프로토콜·호스트·포트가 모두 같아야 같은 출처", () => {
    assert.equal(isSameOrigin("https://ex.com/a", "https://ex.com/b?x=1"), true);
    assert.equal(isSameOrigin("https://ex.com/", "http://ex.com/"), false);
    assert.equal(isSameOrigin("https://ex.com/", "https://www.ex.com/"), false);
    assert.equal(isSameOrigin("https://ex.com/", "https://ex.com:8443/"), false);
  });
  it("기본 범위는 시작 URL 의 디렉터리 아래", () => {
    assert.equal(scopePrefix("https://ex.com/docs/intro.html"), "/docs/");
    assert.equal(isInScope("https://ex.com/docs/a", "https://ex.com/docs/"), true);
    assert.equal(isInScope("https://ex.com/blog/a", "https://ex.com/docs/"), false);
  });
  it("--same-origin 이면 같은 출처 전체, 다른 출처는 항상 제외", () => {
    assert.equal(isInScope("https://ex.com/blog/a", "https://ex.com/docs/", { sameOrigin: true }), true);
    assert.equal(isInScope("https://other.com/docs/a", "https://ex.com/docs/", { sameOrigin: true }), false);
  });
  it("이미지·PDF 같은 파일은 페이지로 보지 않는다", () => {
    assert.equal(looksLikePage("https://ex.com/a.pdf"), false);
    assert.equal(looksLikePage("https://ex.com/logo.PNG"), false);
    assert.equal(looksLikePage("https://ex.com/about"), true);
    assert.equal(looksLikePage("https://ex.com/about.html"), true);
  });
  it("robots 비교용 경로에는 쿼리가 포함된다", () => {
    assert.equal(pathWithQuery("https://ex.com/s?q=1#x"), "/s?q=1");
  });
});
