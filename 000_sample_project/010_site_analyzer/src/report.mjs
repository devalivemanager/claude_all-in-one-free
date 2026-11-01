// 사이트 요약, "다시 만들 때 참고할 점" 체크리스트, Markdown 보고서 만들기 (순수 함수)
import { VIEWPORTS } from "./config.mjs";

/** 바이트를 읽기 쉬운 단위로 */
export function formatBytes(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

/** [{key, count}] 형태 목록 여러 개를 합쳐 다시 순위를 매긴다 */
function mergeCounts(lists, key, limit) {
  const map = new Map();
  for (const item of lists.flat()) map.set(item[key], (map.get(item[key]) ?? 0) + item.count);
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([value, count]) => ({ [key]: value, count }));
}

const unique = (values) => [...new Set(values)];

/** 페이지별 분석을 모아 사이트 전체 요약을 만든다 */
export function buildSiteSummary(pages) {
  const sum = (fn) => pages.reduce((total, p) => total + fn(p), 0);
  const breakpoints = new Map();
  for (const bp of pages.flatMap((p) => p.css.breakpoints)) breakpoints.set(`${bp.px}-${bp.feature}`, bp);

  const byType = new Map();
  for (const t of pages.flatMap((p) => p.network.byType)) {
    const item = byType.get(t.type) ?? { type: t.type, count: 0, bytes: 0 };
    item.count += t.count;
    item.bytes += t.bytes;
    byType.set(t.type, item);
  }
  const loads = pages.map((p) => p.timing.loadMs).filter((v) => typeof v === "number" && v > 0);

  return {
    pageCount: pages.length,
    tech: unique(pages.flatMap((p) => p.tech.map((t) => t.name))),
    fonts: mergeCounts(pages.map((p) => p.fonts), "font", 5),
    colors: {
      background: mergeCounts(pages.map((p) => p.colors.background), "color", 6),
      text: mergeCounts(pages.map((p) => p.colors.text), "color", 6),
    },
    breakpoints: [...breakpoints.values()].sort((a, b) => a.px - b.px || a.feature.localeCompare(b.feature)),
    mediaFeatures: {
      prefersColorScheme: pages.some((p) => p.css.mediaFeatures.prefersColorScheme),
      prefersReducedMotion: pages.some((p) => p.css.mediaFeatures.prefersReducedMotion),
      print: pages.some((p) => p.css.mediaFeatures.print),
    },
    animation: {
      animatedElements: sum((p) => p.animation.animatedElements),
      transitionElements: sum((p) => p.animation.transitionElements),
      // 같은 스타일시트를 여러 페이지가 공유하므로 합계 대신 최댓값을 쓴다
      keyframes: Math.max(0, ...pages.map((p) => p.animation.keyframes)),
      usesIntersectionObserver: pages.some((p) => p.animation.intersectionObserver > 0),
      usesScrollListeners: pages.some((p) => p.animation.scrollListeners > 0),
    },
    accessibility: {
      imagesMissingAlt: sum((p) => p.counts.imagesMissingAlt),
      pagesWithoutH1: pages.filter((p) => !p.headings.some((h) => h.level === 1)).map((p) => p.url),
      pagesWithMultipleH1: pages.filter((p) => p.headings.filter((h) => h.level === 1).length > 1).map((p) => p.url),
      pagesWithoutMain: pages.filter((p) => p.landmarks.main === 0).map((p) => p.url),
      pagesWithoutLang: pages.filter((p) => !p.lang).map((p) => p.url),
      pagesWithoutDescription: pages.filter((p) => !p.description).map((p) => p.url),
    },
    forms: sum((p) => p.counts.forms),
    network: {
      count: sum((p) => p.network.total.count),
      bytes: sum((p) => p.network.total.bytes),
      byType: [...byType.values()].sort((a, b) => b.bytes - a.bytes),
    },
    apiCalls: unique(pages.flatMap((p) => p.apiCalls)).sort(),
    averageLoadMs: loads.length ? Math.round(loads.reduce((a, b) => a + b, 0) / loads.length) : null,
  };
}

const listText = (items, n = 3) => (items.length > n ? `${items.slice(0, n).join(", ")} 외 ${items.length - n}개` : items.join(", "));
const pathOf = (url) => new URL(url).pathname;

/** 요약을 바탕으로 "다시 만들 때 참고할 점" 체크리스트를 만든다 */
export function buildChecklist(summary) {
  const items = [];
  const { accessibility: a11y, animation: anim } = summary;

  if (summary.breakpoints.length > 0) {
    const bps = unique(summary.breakpoints.map((b) => `${b.px}px`));
    items.push(`반응형: 브레이크포인트 ${bps.join(", ")} 를 기준으로 레이아웃이 바뀐다. 모바일·태블릿·데스크톱 스크린샷을 나란히 보고 무엇이 바뀌는지 정리한다.`);
  } else {
    items.push("반응형: @media 브레이크포인트를 찾지 못했다. flex/grid·clamp() 같은 유동 레이아웃인지 스크린샷으로 확인한다.");
  }
  items.push("뼈대: header·nav·main·footer 랜드마크와 h1 → h2 → h3 순서로 페이지 구조를 먼저 잡는다.");
  if (a11y.pagesWithoutMain.length) items.push(`접근성: main 랜드마크가 없는 페이지가 있다(${listText(a11y.pagesWithoutMain.map(pathOf))}). 새로 만들 때는 본문을 <main> 으로 감싼다.`);
  if (a11y.pagesWithoutH1.length) items.push(`제목 구조: h1 이 없는 페이지가 있다(${listText(a11y.pagesWithoutH1.map(pathOf))}). 페이지마다 h1 을 하나 둔다.`);
  if (a11y.pagesWithMultipleH1.length) items.push(`제목 구조: h1 이 여러 개인 페이지가 있다(${listText(a11y.pagesWithMultipleH1.map(pathOf))}).`);

  const colors = unique([...summary.colors.background.slice(0, 3), ...summary.colors.text.slice(0, 3)].map((c) => c.color));
  if (colors.length) items.push(`색상: 자주 쓰인 색(${colors.join(", ")})의 역할(배경·본문·강조)을 파악해 CSS 변수(디자인 토큰)로 정리하되, 실제 값은 자기 브랜드 색으로 정한다.`);
  if (summary.fonts.length) items.push(`글꼴: ${summary.fonts.map((f) => f.font).join(", ")} 사용. 라이선스를 확인하고 대체 글꼴(fallback)을 함께 지정한다.`);

  if (anim.animatedElements + anim.transitionElements + anim.keyframes > 0) {
    const motion = summary.mediaFeatures.prefersReducedMotion ? "대응하고 있다" : "대응이 보이지 않는다";
    items.push(`움직임: 애니메이션 요소 ${anim.animatedElements}개, 트랜지션 요소 ${anim.transitionElements}개, @keyframes 페이지당 최대 ${anim.keyframes}개. prefers-reduced-motion 에는 ${motion}. 움직임을 줄이는 설정을 존중한다.`);
  }
  if (anim.usesIntersectionObserver) items.push("스크롤 효과: IntersectionObserver 를 사용한다. 화면에 들어올 때 나타나는 효과는 이 API 로 직접 구현해 본다.");
  if (anim.usesScrollListeners) items.push("스크롤 이벤트: scroll/wheel 리스너가 있다. 직접 만들 때는 passive 리스너나 IntersectionObserver 로 성능을 챙긴다.");
  if (summary.mediaFeatures.prefersColorScheme) items.push("다크 모드: prefers-color-scheme 대응이 있다. 색상 토큰을 밝은/어두운 테마로 나눠 설계한다.");

  if (a11y.imagesMissingAlt > 0) items.push(`접근성: alt 속성이 없는 이미지 ${a11y.imagesMissingAlt}개. 의미 있는 이미지는 설명을, 장식 이미지는 alt="" 를 넣는다.`);
  if (a11y.pagesWithoutLang.length) items.push("접근성: <html lang> 이 없는 페이지가 있다. 화면 낭독기를 위해 lang=\"ko\" 등을 지정한다.");
  if (a11y.pagesWithoutDescription.length) items.push(`검색 최적화: meta description 이 없는 페이지 ${a11y.pagesWithoutDescription.length}개. 페이지마다 요약 문장을 넣는다.`);
  if (summary.forms > 0) items.push(`폼: 폼 ${summary.forms}개. label 연결, 입력 검증, 서버 측 처리는 직접 설계한다.`);
  if (summary.apiCalls.length) items.push(`API: ${listText(summary.apiCalls, 5)} 호출이 있다. 화면에 필요한 데이터 흐름만 참고하고, API 는 자기 백엔드로 새로 설계한다.`);

  const biggest = summary.network.byType[0];
  if (biggest && biggest.bytes > 0) items.push(`성능: 전체 ${summary.network.count}개 요청, ${formatBytes(summary.network.bytes)}. 가장 큰 종류는 ${biggest.type}(${formatBytes(biggest.bytes)}) 이다.`);

  items.push("저작권: 문구·이미지·로고·아이콘은 복제하지 말고 직접 만들거나 라이선스가 있는 자료를 쓴다. 이 보고서는 구조를 공부하는 참고 자료다.");
  return items;
}

/** 수집 결과에 요약과 체크리스트를 붙여 최종 보고서 데이터를 만든다 */
export function buildReport(base) {
  const summary = buildSiteSummary(base.pages);
  return { ...base, summary, checklist: buildChecklist(summary) };
}

// ---------- Markdown ----------

const cell = (v) => String(v ?? "-").replace(/\|/g, "\\|").replace(/\n/g, " ");
const yesNo = (v) => (v ? "있음" : "없음");
const colorList = (list) => (list.length ? list.map((c) => `\`${c.color}\`(${c.count})`).join(", ") : "-");
const fontList = (list) => (list.length ? list.map((f) => `${f.font}(${f.count})`).join(", ") : "-");
const bpList = (list) => (list.length ? list.map((b) => `${b.feature}-width ${b.px}px`).join(", ") : "없음");
const ms = (v) => (typeof v === "number" ? `${v}ms` : "-");

function table(headers, rows) {
  return [
    `| ${headers.join(" | ")} |`,
    `| ${headers.map(() => "---").join(" | ")} |`,
    ...rows.map((r) => `| ${r.map(cell).join(" | ")} |`),
  ].join("\n");
}

function renderPage(p, index) {
  const lines = [];
  lines.push(`### ${index + 1}. ${p.title || "(제목 없음)"}`, "");
  lines.push(`- URL: ${p.url}${p.finalUrl && p.finalUrl !== p.url ? ` → ${p.finalUrl}` : ""}`);
  lines.push(`- 상태: ${p.status} / lang: ${p.lang ?? "없음"}`);
  lines.push(`- meta description: ${p.description ?? "없음"}`);
  lines.push(`- 로드 시간: DOMContentLoaded ${ms(p.timing.domContentLoadedMs)}, load ${ms(p.timing.loadMs)}`, "");

  lines.push("#### 제목 구조", "");
  if (p.headings.length) for (const h of p.headings) lines.push(`${"  ".repeat(h.level - 1)}- H${h.level} ${h.text || "(빈 제목)"}`);
  else lines.push("- 제목(h1~h3)이 없습니다.");
  lines.push("");

  lines.push("#### 구조와 요소 개수", "");
  lines.push(
    table(
      ["header", "nav", "main", "footer", "링크", "버튼", "폼", "이미지", "alt 누락"],
      [[p.landmarks.header, p.landmarks.nav, p.landmarks.main, p.landmarks.footer, p.counts.links, p.counts.buttons, p.counts.forms, p.counts.images, p.counts.imagesMissingAlt]],
    ),
    "",
  );

  lines.push("#### 디자인", "");
  lines.push(`- 글꼴: ${fontList(p.fonts)}`);
  lines.push(`- 배경색: ${colorList(p.colors.background)}`);
  lines.push(`- 글자색: ${colorList(p.colors.text)}`);
  lines.push(`- 브레이크포인트: ${bpList(p.css.breakpoints)}`);
  lines.push(`- 다크 모드: ${yesNo(p.css.mediaFeatures.prefersColorScheme)} / 동작 줄이기: ${yesNo(p.css.mediaFeatures.prefersReducedMotion)} / 인쇄용: ${yesNo(p.css.mediaFeatures.print)}`);
  const sheetNote = p.css.skippedCrossOriginSheets ? `, 다른 출처라 건너뜀 ${p.css.skippedCrossOriginSheets}개` : "";
  lines.push(`- 스타일시트: ${p.css.stylesheets}개${sheetNote}`, "");

  lines.push("#### 애니메이션 단서", "");
  lines.push(`- CSS animation 요소 ${p.animation.animatedElements}개, transition 요소 ${p.animation.transitionElements}개, @keyframes ${p.animation.keyframes}개`);
  lines.push(`- IntersectionObserver ${p.animation.intersectionObserver}회 생성, scroll/wheel 리스너 ${p.animation.scrollListeners}개`, "");

  lines.push("#### 기술 스택 단서", "");
  if (p.tech.length) for (const t of p.tech) lines.push(`- ${t.name} (근거: ${t.evidence})`);
  else lines.push("- 뚜렷한 단서 없음 (직접 작성한 HTML/JS 이거나 흔적을 숨긴 빌드일 수 있음)");
  lines.push("");

  lines.push("#### 네트워크", "");
  lines.push(`전체 ${p.network.total.count}개 요청, ${formatBytes(p.network.total.bytes)}`, "");
  lines.push(table(["종류", "개수", "용량"], p.network.byType.map((t) => [t.type, t.count, formatBytes(t.bytes)])), "");
  lines.push(`- API 호출(fetch/xhr): ${p.apiCalls.length ? p.apiCalls.map((c) => `\`${c}\``).join(", ") : "없음"}`, "");

  lines.push("#### 스크린샷 (분석용)", "");
  lines.push(VIEWPORTS.map((vp) => `[${vp.label} ${vp.width}px](${p.screenshots[vp.name]})`).join(" · "), "");
  return lines.join("\n");
}

/** 보고서 데이터를 한글 Markdown 으로 렌더링한다 */
export function renderMarkdown(report) {
  const s = report.summary;
  const lines = [];
  lines.push(`# 웹사이트 분석 보고서`, "");
  lines.push(`- 대상: ${report.startUrl}`);
  lines.push(`- 분석 시각: ${report.analyzedAt}`);
  lines.push(`- 도구: ${report.tool.name} ${report.tool.version} (User-Agent: \`${report.tool.userAgent}\`)`);
  lines.push(`- 범위: ${report.options.sameOrigin ? "같은 출처 전체" : "시작 경로 아래"}, 최대 ${report.options.maxPages}페이지, 요청 간격 ${report.options.delayMs}ms`);
  lines.push(`- robots.txt: ${report.robots.status}${report.robots.note ? ` (${report.robots.note})` : ""}`, "");
  lines.push("> 이 보고서는 구조·기술·디자인 특징을 공부하기 위한 자료입니다. 콘텐츠·이미지·로고는 내려받거나 복제하지 않았습니다.", "");

  lines.push("## 사이트 요약", "");
  lines.push(
    table(
      ["항목", "내용"],
      [
        ["분석한 페이지", `${s.pageCount}개 (건너뜀 ${report.skipped.length}개)`],
        ["기술 스택 단서", s.tech.length ? s.tech.join(", ") : "뚜렷한 단서 없음"],
        ["주요 글꼴", fontList(s.fonts)],
        ["주요 배경색", colorList(s.colors.background)],
        ["주요 글자색", colorList(s.colors.text)],
        ["브레이크포인트", bpList(s.breakpoints)],
        ["애니메이션", `animation ${s.animation.animatedElements} · transition ${s.animation.transitionElements} · @keyframes 페이지당 최대 ${s.animation.keyframes} · IntersectionObserver ${yesNo(s.animation.usesIntersectionObserver)} · 스크롤 리스너 ${yesNo(s.animation.usesScrollListeners)}`],
        ["이미지 alt 누락", `${s.accessibility.imagesMissingAlt}개`],
        ["네트워크 합계", `${s.network.count}개 요청, ${formatBytes(s.network.bytes)}`],
        ["API 호출", s.apiCalls.length ? s.apiCalls.join(", ") : "없음"],
        ["평균 load 시간", ms(s.averageLoadMs)],
      ],
    ),
    "",
  );

  lines.push("## 다시 만들 때 참고할 점", "");
  for (const item of report.checklist) lines.push(`- [ ] ${item}`);
  lines.push("");

  if (report.skipped.length) {
    lines.push("## 건너뛴 페이지", "");
    lines.push(table(["URL", "이유"], report.skipped.map((x) => [x.url, x.reason])), "");
  }

  lines.push("## 페이지별 분석", "");
  report.pages.forEach((p, i) => lines.push(renderPage(p, i)));
  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}
