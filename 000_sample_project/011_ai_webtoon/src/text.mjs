// 말풍선 글자 폭 계산과 줄 나누기.
// 브라우저 없이도 배치를 정해야 하므로 글자 종류별 대략적인 폭으로 계산한다.
// 한글·한자 등 전각 글자는 글자 크기만큼, 영문·숫자는 0.55배, 공백은 0.3배로 본다.

const FULL_WIDTH_RANGES = [
  [0x1100, 0x115f], // 한글 자모
  [0x2e80, 0xa4cf], // 한자·일본어·기호
  [0xac00, 0xd7a3], // 한글 음절
  [0xf900, 0xfaff],
  [0xfe30, 0xfe4f],
  [0xff00, 0xff60], // 전각 영숫자
  [0xffe0, 0xffe6],
];

/** 글자 하나의 폭(px) */
export function charWidth(ch, fontSize) {
  if (ch === " ") return fontSize * 0.3;
  const code = ch.codePointAt(0);
  const full = FULL_WIDTH_RANGES.some(([from, to]) => code >= from && code <= to);
  return full ? fontSize : fontSize * 0.55;
}

/** 문자열 전체 폭(px) */
export function textWidth(text, fontSize) {
  let width = 0;
  for (const ch of text) width += charWidth(ch, fontSize);
  return width;
}

/**
 * maxWidth 안에 들어가도록 줄을 나눈다.
 * 띄어쓰기 단위로 나누고, 한 단어가 한 줄보다 길면 글자 단위로 자른다.
 */
export function wrapText(text, maxWidth, fontSize) {
  if (maxWidth < fontSize) throw new RangeError("maxWidth 는 글자 하나보다 넓어야 합니다.");
  const words = text.trim().split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (textWidth(candidate, fontSize) <= maxWidth) {
      current = candidate;
      continue;
    }
    if (current) lines.push(current);
    current = "";
    if (textWidth(word, fontSize) <= maxWidth) {
      current = word;
      continue;
    }
    // 한 단어가 너무 길면 글자 단위로 자른다
    let piece = "";
    for (const ch of word) {
      if (piece && textWidth(piece + ch, fontSize) > maxWidth) {
        lines.push(piece);
        piece = ch;
      } else {
        piece += ch;
      }
    }
    current = piece;
  }
  if (current) lines.push(current);
  return lines;
}
