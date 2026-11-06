// 설정표(색·머리 모양)로 캐릭터를 코드로 그린다.
// 같은 설정표에서 같은 그림이 나오므로 컷마다 얼굴이 달라지지 않는다(캐릭터 일관성).

/** 소수 첫째 자리까지만 써서 같은 입력이면 항상 같은 SVG 가 나오게 한다 */
const f = (n) => Math.round(n * 10) / 10;

/** 컷 높이에 비례한 인물 크기. 기준은 높이 480px 컷 */
export function figureGeometry(panelHeight) {
  const s = panelHeight / 480;
  return { s, headR: 46 * s, bodyH: 150 * s, bodyW: 120 * s };
}

/** 인물의 화면 위치: 가운데 x, 머리 중심 y, 머리 꼭대기 y(머리카락 포함) */
export function castPosition(castEntry, panelHeight, width) {
  const g = figureGeometry(panelHeight);
  const x = castEntry.x * width;
  const headCy = panelHeight - g.bodyH - g.headR * 0.9;
  const headTop = headCy - g.headR * 1.15;
  return { x, headCy, headTop };
}

function drawEyes(cx, cy, r, expression) {
  const dx = r * 0.38;
  const ey = cy - r * 0.05;
  const stroke = `stroke="#222" stroke-width="${f(r * 0.07)}" stroke-linecap="round" fill="none"`;
  switch (expression) {
    case "happy": // 웃는 눈 ^ ^
      return [-1, 1].map((d) => `<path d="M${f(cx + d * dx - r * 0.12)} ${f(ey + r * 0.04)} Q${f(cx + d * dx)} ${f(ey - r * 0.12)} ${f(cx + d * dx + r * 0.12)} ${f(ey + r * 0.04)}" ${stroke}/>`).join("");
    case "sad": // 처진 눈썹 + 작은 눈
      return [-1, 1].map((d) => `<circle cx="${f(cx + d * dx)}" cy="${f(ey + r * 0.04)}" r="${f(r * 0.06)}" fill="#222"/><path d="M${f(cx + d * dx - d * r * 0.14)} ${f(ey - r * 0.22)} L${f(cx + d * dx + d * r * 0.12)} ${f(ey - r * 0.14)}" ${stroke}/>`).join("");
    case "surprised": // 동그란 큰 눈
      return [-1, 1].map((d) => `<circle cx="${f(cx + d * dx)}" cy="${f(ey)}" r="${f(r * 0.13)}" fill="#fff" stroke="#222" stroke-width="${f(r * 0.05)}"/><circle cx="${f(cx + d * dx)}" cy="${f(ey)}" r="${f(r * 0.05)}" fill="#222"/>`).join("");
    case "tired": // 반쯤 감은 눈
      return [-1, 1].map((d) => `<path d="M${f(cx + d * dx - r * 0.12)} ${f(ey)} L${f(cx + d * dx + r * 0.12)} ${f(ey)}" ${stroke}/>`).join("");
    default:
      return [-1, 1].map((d) => `<circle cx="${f(cx + d * dx)}" cy="${f(ey)}" r="${f(r * 0.07)}" fill="#222"/>`).join("");
  }
}

function drawMouth(cx, cy, r, expression) {
  const my = cy + r * 0.42;
  const stroke = `stroke="#222" stroke-width="${f(r * 0.06)}" stroke-linecap="round" fill="none"`;
  switch (expression) {
    case "happy":
      return `<path d="M${f(cx - r * 0.25)} ${f(my - r * 0.05)} Q${f(cx)} ${f(my + r * 0.22)} ${f(cx + r * 0.25)} ${f(my - r * 0.05)}" ${stroke}/>`;
    case "sad":
      return `<path d="M${f(cx - r * 0.2)} ${f(my + r * 0.08)} Q${f(cx)} ${f(my - r * 0.12)} ${f(cx + r * 0.2)} ${f(my + r * 0.08)}" ${stroke}/>`;
    case "surprised":
      return `<ellipse cx="${f(cx)}" cy="${f(my)}" rx="${f(r * 0.1)}" ry="${f(r * 0.14)}" fill="#222"/>`;
    case "tired":
      return `<path d="M${f(cx - r * 0.2)} ${f(my)} Q${f(cx - r * 0.1)} ${f(my - r * 0.06)} ${f(cx)} ${f(my)} Q${f(cx + r * 0.1)} ${f(my + r * 0.06)} ${f(cx + r * 0.2)} ${f(my)}" ${stroke}/>`;
    default:
      return `<path d="M${f(cx - r * 0.18)} ${f(my)} L${f(cx + r * 0.18)} ${f(my)}" ${stroke}/>`;
  }
}

/** 얼굴 뒤에 그릴 머리카락(긴 옆머리, 올림머리) */
function drawBackHair(cx, cy, r, look) {
  if (look.hairStyle === "long") {
    return [-1, 1].map((d) => `<rect x="${f(cx + d * r * 0.98 - r * 0.2)}" y="${f(cy - r * 0.2)}" width="${f(r * 0.4)}" height="${f(r * 1.5)}" rx="${f(r * 0.18)}" fill="${look.hair}"/>`).join("");
  }
  if (look.hairStyle === "bun") return `<circle cx="${f(cx)}" cy="${f(cy - r * 1.05)}" r="${f(r * 0.32)}" fill="${look.hair}"/>`;
  return "";
}

/** 얼굴 위에 덮는 앞머리. 얼굴보다 나중에 그려야 보인다 */
function drawFrontHair(cx, cy, r, look) {
  return `<path class="hair" d="M${f(cx - r * 1.04)} ${f(cy)} A${f(r * 1.04)} ${f(r * 1.04)} 0 0 1 ${f(cx + r * 1.04)} ${f(cy)} L${f(cx + r * 0.92)} ${f(cy - r * 0.32)} Q${f(cx)} ${f(cy - r * 0.62)} ${f(cx - r * 0.92)} ${f(cy - r * 0.32)} Z" fill="${look.hair}"/>`;
}

/** 인물 한 명을 SVG 조각으로 그린다 */
export function drawCharacter(character, castEntry, panelHeight, width) {
  const g = figureGeometry(panelHeight);
  const { x, headCy } = castPosition(castEntry, panelHeight, width);
  const r = g.headR;
  const look = character.look;
  const body = `<rect x="${f(x - g.bodyW / 2)}" y="${f(panelHeight - g.bodyH)}" width="${f(g.bodyW)}" height="${f(g.bodyH + 20)}" rx="${f(40 * g.s)}" fill="${look.shirt}"/>`;
  const neck = `<rect x="${f(x - r * 0.22)}" y="${f(headCy + r * 0.8)}" width="${f(r * 0.44)}" height="${f(r * 0.4)}" fill="${look.skin}"/>`;
  const head = `<circle cx="${f(x)}" cy="${f(headCy)}" r="${f(r)}" fill="${look.skin}"/>`;
  const glasses = look.glasses
    ? [-1, 1].map((d) => `<circle cx="${f(x + d * r * 0.38)}" cy="${f(headCy - r * 0.05)}" r="${f(r * 0.24)}" fill="none" stroke="#333" stroke-width="${f(r * 0.05)}"/>`).join("")
    : "";
  return `<g class="character" data-who="${castEntry.who}">${body}${neck}${drawBackHair(x, headCy, r, look)}${head}${drawFrontHair(x, headCy, r, look)}${drawEyes(x, headCy, r, castEntry.expression)}${drawMouth(x, headCy, r, castEntry.expression)}${glasses}</g>`;
}

/** 배경 */
export function drawBackground(kind, width, height) {
  switch (kind) {
    case "office":
      return `<rect width="${width}" height="${height}" fill="#eef3f7"/><rect y="${f(height * 0.72)}" width="${width}" height="${f(height * 0.28)}" fill="#c9d6df"/><rect x="${f(width * 0.06)}" y="${f(height * 0.12)}" width="${f(width * 0.22)}" height="${f(height * 0.2)}" rx="6" fill="#ffffff" stroke="#b8c7d3"/>`;
    case "night":
      return `<rect width="${width}" height="${height}" fill="#1f2a44"/><rect x="${f(width * 0.62)}" y="${f(height * 0.1)}" width="${f(width * 0.3)}" height="${f(height * 0.26)}" fill="#2d3c5e" stroke="#4a5d86"/><circle cx="${f(width * 0.82)}" cy="${f(height * 0.18)}" r="${f(height * 0.04)}" fill="#f5e6a8"/><rect y="${f(height * 0.74)}" width="${width}" height="${f(height * 0.26)}" fill="#18213a"/>`;
    case "monitor": {
      const rows = [0.3, 0.4, 0.5, 0.6].map((t, i) => `<rect x="${f(width * 0.16)}" y="${f(height * t)}" width="${f(width * (0.5 - i * 0.08))}" height="${f(height * 0.035)}" rx="3" fill="${i === 2 ? "#e06c75" : "#7fb3d5"}"/>`).join("");
      return `<rect width="${width}" height="${height}" fill="#2b2b2b"/><rect x="${f(width * 0.1)}" y="${f(height * 0.18)}" width="${f(width * 0.8)}" height="${f(height * 0.6)}" rx="10" fill="#1e1e1e" stroke="#555"/>${rows}`;
    }
    default:
      return `<rect width="${width}" height="${height}" fill="#ffffff"/>`;
  }
}
