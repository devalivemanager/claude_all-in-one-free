import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { charWidth, textWidth, wrapText } from "../src/text.mjs";

describe("글자 폭", () => {
  it("한글은 글자 크기만큼, 영문·숫자는 0.55배, 공백은 0.3배", () => {
    assert.equal(charWidth("한", 20), 20);
    assert.equal(charWidth("A", 20), 11);
    assert.equal(charWidth("7", 20), 11);
    assert.equal(charWidth(" ", 20), 6);
    assert.equal(textWidth("한 A", 20), 37);
  });
});

describe("줄 나누기", () => {
  it("폭 안에 들어가면 한 줄", () => {
    assert.deepEqual(wrapText("안녕하세요", 200, 20), ["안녕하세요"]);
  });

  it("띄어쓰기 단위로 나누고 모든 줄이 폭을 넘지 않는다", () => {
    const rows = wrapText("건강보험료를 먼저 원 단위로 자른 다음에 곱해야 해요.", 180, 20);
    assert.ok(rows.length > 1);
    for (const row of rows) assert.ok(textWidth(row, 20) <= 180, `'${row}' 가 폭을 넘음`);
    assert.equal(rows.join(" "), "건강보험료를 먼저 원 단위로 자른 다음에 곱해야 해요.");
  });

  it("한 단어가 한 줄보다 길면 글자 단위로 자른다", () => {
    const rows = wrapText("가나다라마바사아자차", 60, 20);
    assert.deepEqual(rows, ["가나다", "라마바", "사아자", "차"]);
  });

  it("폭이 글자 하나보다 좁으면 오류", () => {
    assert.throws(() => wrapText("가", 10, 20), RangeError);
  });
});
