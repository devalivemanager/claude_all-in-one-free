// 이미지 AI 에 줄 컷별 프롬프트를 만든다.
// 캐릭터 일관성을 위해 설정표의 외모 설명(desc / desc_en)을 매 컷 "글자 그대로" 넣는다.
// 한글은 이미지 AI 가 자주 틀리게 그리므로 글자·말풍선은 그리지 말라고 하고, 대사는 코드로 얹는다.
// 미드저니 같은 도구는 영어 프롬프트가 잘 맞아서 lang="en" 이면 영어로 만든다(영어 필드는 대본에 적어 둔다).

import { castPosition } from "./characters.mjs";

// 이미지 AI 가 받는 흔한 비율. 픽셀 크기 대신 가장 가까운 비율을 알려 주고, 남는 부분은 조립할 때 가운데 기준으로 잘린다
export const COMMON_RATIOS = ["1:1", "5:4", "4:3", "3:2", "16:9", "4:5", "3:4", "2:3", "9:16"];

/** 가로·세로에 가장 가까운 흔한 비율(로그 차이가 가장 작은 것) */
export function nearestRatio(width, height) {
  const target = Math.log(width / height);
  let best = COMMON_RATIOS[0];
  for (const r of COMMON_RATIOS) {
    const [a, b] = r.split(":").map(Number);
    if (Math.abs(Math.log(a / b) - target) < Math.abs(Math.log(best.split(":")[0] / best.split(":")[1]) - target)) best = r;
  }
  return best;
}

/** 말풍선 자리: 인물 머리 꼭대기가 컷 위에서 몇 % 지점인지(레이아웃과 같은 계산) */
export function headroomPercent(episode, panel) {
  const tops = (panel.cast ?? []).map((c) => castPosition(c, panel.height, episode.width).headTop);
  return tops.length > 0 ? Math.round((Math.min(...tops) / panel.height) * 100) : null;
}

const WORDS = {
  ko: {
    expression: { neutral: "무표정", happy: "웃는 얼굴", sad: "시무룩한 얼굴", surprised: "깜짝 놀란 얼굴", tired: "지친 얼굴" },
    side: { left: "왼쪽", center: "가운데", right: "오른쪽" },
    style: "그림 분위기",
    scene: "장면",
    cast: "등장인물",
    none: "없음",
    position: "위치",
    face: "표정",
    frame: (w, h, r) => `세로 웹툰 한 컷, 비율 ${r}(가로 ${w}px × 세로 ${h}px).`,
    headroom: (p) => `말풍선 자리: 그림 위쪽 ${p}% 는 단순한 배경으로 비워 둔다. 인물의 머리 꼭대기는 위에서 ${p}% 지점 아래에 오게 한다.`,
    sheet: "캐릭터 기준 그림: 전신, 정면으로 서 있음, 무표정, 흰 단색 배경, 한 사람만.",
  },
  en: {
    expression: { neutral: "neutral expression", happy: "smiling", sad: "sad, downcast", surprised: "surprised, wide eyes", tired: "tired, half-closed eyes" },
    side: { left: "left", center: "center", right: "right" },
    style: "Style",
    scene: "Scene",
    cast: "Characters",
    none: "none",
    position: "position",
    face: "expression",
    frame: (w, h, r) => `Single vertical webtoon panel, aspect ratio ${r} (${w}x${h}).`,
    headroom: (p) => `Keep the top ${p}% of the image as plain, simple background for speech bubbles; the top of every character's head must be below ${p}% from the top.`,
    sheet: "Character reference: full body, standing, front view, neutral expression, plain white background, single character only.",
  },
};

export const NO_TEXT_RULE = "그림 안에 글자, 숫자, 말풍선을 넣지 않는다.";
export const NO_TEXT_RULE_EN = "No text, no letters, no numbers, no speech bubbles in the image.";
export const PROMPT_LANGS = ["ko", "en"];

/** 언어에 맞는 필드를 고른다. 영어 필드가 없으면 검증 단계(validatePromptLang)에서 이미 막힌다. */
const pick = (obj, key, lang) => (lang === "en" ? obj[`${key}_en`] : obj[key]);

export function buildPanelPrompt(episode, panel, lang = "ko") {
  const w = WORDS[lang];
  const cast = (panel.cast ?? []).map((c) => {
    const ch = episode.characters[c.who];
    const side = c.x < 0.4 ? w.side.left : c.x > 0.6 ? w.side.right : w.side.center;
    const name = lang === "en" && ch.name_en ? ch.name_en : ch.name; // 영어 이름(name_en)은 선택
    return `- ${name}: ${pick(ch, "desc", lang)} / ${w.position}: ${side} / ${w.face}: ${w.expression[c.expression]}`;
  });
  return [
    `${w.style}: ${pick(episode, "style", lang)}`,
    `${w.scene}: ${pick(panel, "scene", lang)}`,
    cast.length > 0 ? `${w.cast}:\n${cast.join("\n")}` : `${w.cast}: ${w.none}`,
    w.frame(episode.width, panel.height, nearestRatio(episode.width, panel.height)),
    (panel.lines ?? []).length > 0 ? w.headroom(headroomPercent(episode, panel)) : null,
    lang === "en" ? NO_TEXT_RULE_EN : NO_TEXT_RULE,
  ].filter(Boolean).join("\n");
}

/** 캐릭터 기준 그림 프롬프트. 컷 그림을 받기 전에 먼저 만들어, 이후 컷에서 「같은 사람」의 기준으로 쓴다 */
export function buildCharacterSheetPrompt(episode, who, lang = "ko") {
  const w = WORDS[lang];
  const ch = episode.characters[who];
  const name = lang === "en" && ch.name_en ? ch.name_en : ch.name;
  return [`${w.style}: ${pick(episode, "style", lang)}`, `${name}: ${pick(ch, "desc", lang)}`, w.sheet, lang === "en" ? NO_TEXT_RULE_EN : NO_TEXT_RULE].join("\n");
}
