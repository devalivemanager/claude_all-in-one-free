import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { colorToHex, detectMediaFeatures, firstFontFamily, parseBreakpoints, topColors, topFonts, topValues } from "../src/style-utils.mjs";

describe("색상 집계", () => {
  it("rgb/rgba 를 #hex 로 바꾸고 투명은 뺀다", () => {
    assert.equal(colorToHex("rgb(47, 107, 79)"), "#2f6b4f");
    assert.equal(colorToHex("rgba(0, 0, 0, 0)"), null);
    assert.equal(colorToHex("transparent"), null);
    assert.equal(colorToHex("rgba(255, 0, 0, 0.5)"), "#ff000080");
    assert.equal(colorToHex("rgb(255 0 0 / 50%)"), "#ff000080");
    assert.equal(colorToHex("oklch(0.7 0.1 200)"), "oklch(0.7 0.1 200)");
  });
  it("빈도순 상위만 남긴다", () => {
    const result = topColors(["rgb(0, 0, 0)", "rgb(255, 255, 255)", "rgb(0, 0, 0)", "rgba(0, 0, 0, 0)"], 1);
    assert.deepEqual(result, [{ color: "#000000", count: 2 }]);
  });
  it("동률이면 값 순서로 정렬해 결과가 항상 같다", () => {
    assert.deepEqual(topValues(["b", "a"]), [
      { value: "a", count: 1 },
      { value: "b", count: 1 },
    ]);
  });
});

describe("폰트 집계", () => {
  it("첫 번째 글꼴 이름만 쓴다", () => {
    assert.equal(firstFontFamily('"Noto Sans KR", sans-serif'), "Noto Sans KR");
    assert.deepEqual(topFonts(['"A", serif', "A", "B"]), [
      { font: "A", count: 2 },
      { font: "B", count: 1 },
    ]);
  });
});

describe("브레이크포인트 파싱", () => {
  it("min/max-width 와 em 단위를 처리한다", () => {
    assert.deepEqual(parseBreakpoints(["(max-width: 768px)", "screen and (min-width: 64em)", "(max-width:768px)"]), [
      { px: 768, feature: "max" },
      { px: 1024, feature: "min" },
    ]);
  });
  it("범위 문법을 처리한다", () => {
    // 480px < width 와 width >= 30rem(=480px) 은 같은 브레이크포인트로 합쳐진다
    assert.deepEqual(parseBreakpoints(["(width <= 600px)", "(480px < width)", "(width >= 30rem)"]), [
      { px: 480, feature: "min" },
      { px: 600, feature: "max" },
    ]);
  });
  it("높이·장치 너비 조건은 무시한다", () => {
    assert.deepEqual(parseBreakpoints(["(max-height: 500px)", "(min-device-width: 320px)", "print"]), []);
  });
  it("사용자 환경 대응 단서를 찾는다", () => {
    assert.deepEqual(detectMediaFeatures(["(prefers-reduced-motion: reduce)", "print"]), {
      prefersColorScheme: false,
      prefersReducedMotion: true,
      print: true,
    });
  });
});
