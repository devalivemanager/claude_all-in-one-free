// 회차 대본(JSON)을 읽고 검증한다.
// 오류는 "어디(경로) - 무엇" 형태로 모두 모아서 돌려준다. 하나 고치고 다시 돌리는 일을 줄이기 위해서다.
import { readFile } from "node:fs/promises";

export const EXPRESSIONS = ["neutral", "happy", "sad", "surprised", "tired"];
export const HAIR_STYLES = ["short", "long", "bun"];
export const BACKGROUNDS = ["office", "night", "monitor", "plain"];
export const LIMITS = { minWidth: 360, maxWidth: 1080, minPanelHeight: 240, maxPanelHeight: 1600, maxPanels: 60, maxLineLength: 60, maxGap: 600 };
// 컷 다음 여백(px). 대본에 gap_after 가 없으면 이 값을 쓴다.
export const DEFAULT_GAP = 32;

// 특정 작가·작품의 그림체를 흉내 내라는 지시는 받지 않는다. 화풍은 선·색감 같은 특징으로 적는다.
const IMITATION_PATTERNS = [/화풍/, /그림체/, /style of/i, /in the style/i];
const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;

export class EpisodeError extends Error {
  constructor(errors) {
    super(`대본 오류 ${errors.length}건:\n` + errors.map((e) => `  - ${e}`).join("\n"));
    this.name = "EpisodeError";
    this.errors = errors;
  }
}

const isText = (v) => typeof v === "string" && v.trim() !== "";

/** 대본을 검증하고 오류 목록을 돌려준다. 빈 배열이면 통과. */
export function validateEpisode(ep) {
  const errors = [];
  if (typeof ep !== "object" || ep === null || Array.isArray(ep)) return ["대본은 JSON 객체여야 합니다."];

  if (!isText(ep.title)) errors.push("title - 제목이 필요합니다.");
  if (!Number.isInteger(ep.episode) || ep.episode < 1) errors.push("episode - 회차는 1 이상의 정수여야 합니다.");
  if (!Number.isInteger(ep.width) || ep.width < LIMITS.minWidth || ep.width > LIMITS.maxWidth) {
    errors.push(`width - 가로 폭은 ${LIMITS.minWidth}~${LIMITS.maxWidth} 사이 정수여야 합니다.`);
  }
  if (!isText(ep.style)) {
    errors.push("style - 그림 분위기 설명이 필요합니다(이미지 AI 프롬프트에 쓰임).");
  } else if (IMITATION_PATTERNS.some((p) => p.test(ep.style))) {
    errors.push("style - 특정 작가·작품의 화풍을 흉내 내라는 지시는 쓸 수 없습니다. 선·색감·분위기로 적으세요.");
  }

  const characters = ep.characters;
  if (typeof characters !== "object" || characters === null || Object.keys(characters).length === 0) {
    errors.push("characters - 등장인물이 한 명 이상 필요합니다.");
  } else {
    for (const [id, c] of Object.entries(characters)) {
      const at = `characters.${id}`;
      if (!isText(c?.name)) errors.push(`${at}.name - 이름이 필요합니다.`);
      if (!isText(c?.desc)) errors.push(`${at}.desc - 외모 설명이 필요합니다(컷마다 같은 문장으로 쓰임).`);
      for (const key of ["hair", "skin", "shirt"]) {
        if (!HEX_COLOR.test(c?.look?.[key] ?? "")) errors.push(`${at}.look.${key} - #RRGGBB 형식의 색이어야 합니다.`);
      }
      if (!HAIR_STYLES.includes(c?.look?.hairStyle)) errors.push(`${at}.look.hairStyle - ${HAIR_STYLES.join(", ")} 중 하나여야 합니다.`);
    }
  }

  if (!Array.isArray(ep.panels) || ep.panels.length === 0) {
    errors.push("panels - 컷이 한 개 이상 필요합니다.");
    return errors;
  }
  if (ep.panels.length > LIMITS.maxPanels) errors.push(`panels - 컷은 ${LIMITS.maxPanels}개까지입니다.`);

  const seenIds = new Set();
  ep.panels.forEach((p, i) => {
    const at = `panels[${i}]`;
    if (!isText(p?.id)) errors.push(`${at}.id - 컷 id 가 필요합니다.`);
    else if (seenIds.has(p.id)) errors.push(`${at}.id - 컷 id '${p.id}' 가 중복됩니다.`);
    else seenIds.add(p.id);
    if (!Number.isInteger(p?.height) || p.height < LIMITS.minPanelHeight || p.height > LIMITS.maxPanelHeight) {
      errors.push(`${at}.height - 컷 높이는 ${LIMITS.minPanelHeight}~${LIMITS.maxPanelHeight} 사이 정수여야 합니다.`);
    }
    if (!BACKGROUNDS.includes(p?.background)) errors.push(`${at}.background - ${BACKGROUNDS.join(", ")} 중 하나여야 합니다.`);
    if (p?.gap_after !== undefined && (!Number.isInteger(p.gap_after) || p.gap_after < 0 || p.gap_after > LIMITS.maxGap)) {
      errors.push(`${at}.gap_after - 컷 다음 여백은 0~${LIMITS.maxGap} 사이 정수(px)여야 합니다.`);
    }
    if (!isText(p?.scene)) errors.push(`${at}.scene - 장면 설명이 필요합니다(이미지 AI 프롬프트·대체 텍스트에 쓰임).`);

    const cast = Array.isArray(p?.cast) ? p.cast : [];
    const inPanel = new Set();
    cast.forEach((c, j) => {
      const cAt = `${at}.cast[${j}]`;
      if (!characters?.[c?.who]) errors.push(`${cAt}.who - 등장인물 목록에 없는 인물 '${c?.who}' 입니다.`);
      else inPanel.add(c.who);
      if (typeof c?.x !== "number" || c.x < 0.1 || c.x > 0.9) errors.push(`${cAt}.x - 가로 위치는 0.1~0.9 사이 비율이어야 합니다.`);
      if (!EXPRESSIONS.includes(c?.expression)) errors.push(`${cAt}.expression - ${EXPRESSIONS.join(", ")} 중 하나여야 합니다.`);
    });

    const lines = Array.isArray(p?.lines) ? p.lines : [];
    lines.forEach((l, j) => {
      const lAt = `${at}.lines[${j}]`;
      if (!isText(l?.text)) errors.push(`${lAt}.text - 대사가 비어 있습니다.`);
      else if ([...l.text].length > LIMITS.maxLineLength) errors.push(`${lAt}.text - 대사 하나는 ${LIMITS.maxLineLength}자까지입니다. 말풍선을 나누세요.`);
      if (!inPanel.has(l?.who)) errors.push(`${lAt}.who - '${l?.who}' 는 이 컷에 나오지 않습니다(cast 에 추가하세요).`);
    });
  });
  return errors;
}

/**
 * 영어 프롬프트(--prompt-lang en)를 쓸 때 필요한 영어 필드가 다 있는지 본다.
 * style_en, characters.*.desc_en, panels[].scene_en. 한국어(ko)면 검사하지 않는다.
 */
export function validatePromptLang(ep, lang) {
  if (lang !== "en") return [];
  const errors = [];
  if (!isText(ep.style_en)) errors.push("style_en - 영어 프롬프트에는 영어 그림 분위기 설명이 필요합니다.");
  else if (IMITATION_PATTERNS.some((p) => p.test(ep.style_en))) {
    errors.push("style_en - 특정 작가·작품의 화풍을 흉내 내라는 지시는 쓸 수 없습니다.");
  }
  for (const [id, c] of Object.entries(ep.characters ?? {})) {
    if (!isText(c?.desc_en)) errors.push(`characters.${id}.desc_en - 영어 외모 설명이 필요합니다(컷마다 같은 문장으로 쓰임).`);
  }
  (ep.panels ?? []).forEach((p, i) => {
    if (!isText(p?.scene_en)) errors.push(`panels[${i}].scene_en - 영어 장면 설명이 필요합니다.`);
  });
  return errors;
}

/** 파일을 읽어 검증까지 마친 대본을 돌려준다. 문제가 있으면 EpisodeError. */
export async function loadEpisode(path) {
  let ep;
  try {
    ep = JSON.parse(await readFile(path, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") throw new EpisodeError([`파일을 찾을 수 없습니다: ${path}`]);
    throw new EpisodeError([`JSON 형식 오류: ${error.message}`]);
  }
  const errors = validateEpisode(ep);
  if (errors.length > 0) throw new EpisodeError(errors);
  return ep;
}
