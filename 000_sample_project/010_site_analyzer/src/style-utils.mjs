// 색상·폰트·브레이크포인트 집계 (순수 함수)

/** 값 목록에서 많이 나온 순서대로 상위 limit 개를 센다 */
export function topValues(values, limit = 5) {
  const counts = new Map();
  for (const v of values) {
    if (v == null || v === "") continue;
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))
    .slice(0, limit)
    .map(([value, count]) => ({ value, count }));
}

const hex2 = (n) => Math.round(Number(n)).toString(16).padStart(2, "0");

/**
 * 계산된 CSS 색상 문자열을 #rrggbb 로 바꾼다.
 * - 완전히 투명하면 null (배경이 없는 것과 같으므로 집계에서 뺀다)
 * - 반투명은 #rrggbb + 알파 2자리
 * - rgb() 가 아닌 형식(oklch 등)은 소문자 원문 그대로 둔다
 */
export function colorToHex(value) {
  if (!value) return null;
  const text = String(value).trim().toLowerCase();
  if (text === "transparent") return null;
  const m = text.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$/);
  if (!m) return text;
  let alpha = m[4] === undefined ? 1 : parseFloat(m[4]);
  if (m[4]?.endsWith("%")) alpha /= 100;
  if (alpha === 0) return null;
  const hex = `#${hex2(m[1])}${hex2(m[2])}${hex2(m[3])}`;
  return alpha < 1 ? hex + hex2(alpha * 255) : hex;
}

/** 색상 목록을 정규화해 빈도 상위 limit 개를 돌려준다 */
export function topColors(values, limit = 6) {
  return topValues(values.map(colorToHex), limit).map(({ value, count }) => ({ color: value, count }));
}

/** font-family 값에서 첫 번째(실제로 우선 적용되는) 글꼴 이름만 뽑는다 */
export function firstFontFamily(value) {
  if (!value) return null;
  const first = String(value).split(",")[0].trim().replace(/^["']|["']$/g, "");
  return first || null;
}

/** 폰트 패밀리 빈도 상위 */
export function topFonts(values, limit = 5) {
  return topValues(values.map(firstFontFamily), limit).map(({ value, count }) => ({ font: value, count }));
}

const toPx = (num, unit) => {
  const n = parseFloat(num);
  return Math.round(unit === "px" ? n : n * 16); // em·rem 은 기본 글자 크기 16px 로 환산
};

/**
 * @media 조건 문자열들에서 너비 브레이크포인트를 뽑는다.
 * 지원: (max-width: 768px), (min-width: 48em), (width <= 768px), (600px < width)
 * 반환: [{ px: 768, feature: "max" }] (px 오름차순, 중복 제거)
 */
export function parseBreakpoints(mediaTexts) {
  const found = new Map();
  const add = (px, feature) => found.set(`${px}-${feature}`, { px, feature });
  for (const text of mediaTexts) {
    const t = String(text).toLowerCase();
    for (const m of t.matchAll(/(min|max)-width\s*:\s*([\d.]+)(px|em|rem)/g)) add(toPx(m[2], m[3]), m[1]);
    // 범위 문법: width <= 768px → 최대 너비, width >= 768px → 최소 너비
    for (const m of t.matchAll(/(?<![\w-])width\s*(<=|>=|<|>)\s*([\d.]+)(px|em|rem)/g)) {
      add(toPx(m[2], m[3]), m[1].startsWith("<") ? "max" : "min");
    }
    // 값이 앞에 오는 범위 문법: 600px <= width → 최소 너비
    for (const m of t.matchAll(/([\d.]+)(px|em|rem)\s*(<=|>=|<|>)\s*width(?![\w-])/g)) {
      add(toPx(m[1], m[2]), m[3].startsWith("<") ? "min" : "max");
    }
  }
  return [...found.values()].sort((a, b) => a.px - b.px || a.feature.localeCompare(b.feature));
}

/** @media 조건에서 사용자 환경 대응 단서(다크 모드, 동작 줄이기, 인쇄)를 찾는다 */
export function detectMediaFeatures(mediaTexts) {
  const all = mediaTexts.join(" ").toLowerCase();
  return {
    prefersColorScheme: all.includes("prefers-color-scheme"),
    prefersReducedMotion: all.includes("prefers-reduced-motion"),
    print: /(^|[\s,(])print\b/.test(all),
  };
}
