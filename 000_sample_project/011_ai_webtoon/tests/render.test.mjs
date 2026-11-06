import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createImageApiPainter, createSvgPainter } from "../src/painters.mjs";
import { buildEpisode, escapeXml, renderPanelSvg } from "../src/render.mjs";
import { sampleEpisode } from "./helpers.mjs";

describe("렌더링", () => {
  it("대사·제목·장면 설명의 HTML 특수문자를 이스케이프한다", async () => {
    const ep = sampleEpisode({ title: "<b>제목</b>" });
    ep.panels[0].lines = [{ who: "a", text: "<script>alert(1)</script>" }];
    ep.panels[0].scene = 'x" onload="alert(1)';
    const { html } = await buildEpisode(ep, createSvgPainter());
    assert.ok(!html.includes("<script>alert"));
    assert.ok(html.includes("&lt;script&gt;"));
    assert.ok(!html.includes("<b>제목"));
    assert.ok(!html.includes('" onload="'));
  });

  it("컷을 대본 순서대로 넣고, 장면 설명을 대체 텍스트(aria-label)로 단다", async () => {
    const ep = sampleEpisode();
    ep.panels.push({ ...ep.panels[0], id: "p2", scene: "두 번째 장면" });
    const { html, panelCount, bubbleCount } = await buildEpisode(ep, createSvgPainter());
    assert.ok(html.indexOf('id="p1"') < html.indexOf('id="p2"'));
    assert.ok(html.includes('aria-label="두 번째 장면"'));
    assert.equal(panelCount, 2);
    assert.equal(bubbleCount, 2);
  });

  it("그림 도구가 준 이미지가 있으면 코드 그림 대신 이미지를 깐다", () => {
    const ep = sampleEpisode();
    const svg = renderPanelSvg(ep, ep.panels[0], "data:image/png;base64,AAAA");
    assert.ok(svg.includes('<image href="data:image/png;base64,AAAA"'));
    assert.ok(!svg.includes('class="character"'));
    assert.ok(svg.includes('class="bubble"'), "말풍선은 이미지 위에도 코드로 얹는다");
  });

  it("escapeXml 은 & < > \" ' 를 모두 바꾼다", () => {
    assert.equal(escapeXml(`&<>"'`), "&amp;&lt;&gt;&quot;&#39;");
  });
});

describe("이미지 API 그림 도구", () => {
  const okFetch = (body, status = 200) => async (url, init) => {
    okFetch.last = { url, init };
    return { ok: status < 400, status, json: async () => body };
  };

  it("키나 주소가 없으면 만들 때 바로 알린다", () => {
    assert.throws(() => createImageApiPainter({ endpoint: "https://img.example" }), /IMAGE_API_KEY/);
    assert.throws(() => createImageApiPainter({ apiKey: "k" }), /IMAGE_API_URL/);
  });

  it("프롬프트·크기를 보내고 data URL 로 돌려준다", async () => {
    const fetchImpl = okFetch({ imageBase64: "QUJD", mimeType: "image/png" });
    const painter = createImageApiPainter({ endpoint: "https://img.example", apiKey: "k", fetchImpl });
    const href = await painter.paint({ prompt: "장면", width: 720, height: 480 });
    assert.equal(href, "data:image/png;base64,QUJD");
    assert.deepEqual(JSON.parse(okFetch.last.init.body), { prompt: "장면", width: 720, height: 480 });
    assert.equal(okFetch.last.init.headers.authorization, "Bearer k");
  });

  it("실패한 컷은 코드 그림으로 대신하고 경고를 남긴다(조용히 넘어가지 않는다)", async () => {
    const painter = createImageApiPainter({ endpoint: "https://img.example", apiKey: "k", fetchImpl: okFetch({}, 503) });
    const { html, warnings } = await buildEpisode(sampleEpisode(), painter);
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], /컷 p1: .*503/);
    assert.ok(html.includes('class="character"'));
  });

  it("응답에 이미지가 없거나 형식이 이상하면 실패로 본다", async () => {
    for (const body of [{}, { imageBase64: "" }, { imageBase64: "QUJD", mimeType: "text/html" }]) {
      const painter = createImageApiPainter({ endpoint: "https://img.example", apiKey: "k", fetchImpl: okFetch(body) });
      await assert.rejects(painter.paint({ prompt: "p", width: 1, height: 1 }));
    }
  });
});
