// 이미지 AI 에 줄 컷별 프롬프트를 만든다.
// 캐릭터 일관성을 위해 설정표의 외모 설명(desc / desc_en)을 매 컷 "글자 그대로" 넣는다.
// 한글은 이미지 AI 가 자주 틀리게 그리므로 글자·말풍선은 그리지 말라고 하고, 대사는 코드로 얹는다.
// 미드저니 같은 도구는 영어 프롬프트가 잘 맞아서 lang="en" 이면 영어로 만든다(영어 필드는 대본에 적어 둔다).

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
    frame: (w, h) => `세로 웹툰 한 컷, 가로 ${w}px × 세로 ${h}px 비율.`,
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
    frame: (w, h) => `Single vertical webtoon panel, aspect ratio ${w}x${h}.`,
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
    w.frame(episode.width, panel.height),
    lang === "en" ? NO_TEXT_RULE_EN : NO_TEXT_RULE,
  ].join("\n");
}
