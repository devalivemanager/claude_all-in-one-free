// 이미지 AI 에 줄 컷별 프롬프트를 만든다.
// 캐릭터 일관성을 위해 설정표의 외모 설명(desc)을 매 컷 "글자 그대로" 넣는다.
// 한글은 이미지 AI 가 자주 틀리게 그리므로 글자·말풍선은 그리지 말라고 하고, 대사는 코드로 얹는다.

const EXPRESSION_KO = { neutral: "무표정", happy: "웃는 얼굴", sad: "시무룩한 얼굴", surprised: "깜짝 놀란 얼굴", tired: "지친 얼굴" };
export const NO_TEXT_RULE = "그림 안에 글자, 숫자, 말풍선을 넣지 않는다.";

export function buildPanelPrompt(episode, panel) {
  const cast = (panel.cast ?? []).map((c) => {
    const ch = episode.characters[c.who];
    const side = c.x < 0.4 ? "왼쪽" : c.x > 0.6 ? "오른쪽" : "가운데";
    return `- ${ch.name}: ${ch.desc} / 위치: ${side} / 표정: ${EXPRESSION_KO[c.expression]}`;
  });
  return [
    `그림 분위기: ${episode.style}`,
    `장면: ${panel.scene}`,
    cast.length > 0 ? `등장인물:\n${cast.join("\n")}` : "등장인물: 없음",
    `세로 웹툰 한 컷, 가로 ${episode.width}px × 세로 ${panel.height}px 비율.`,
    NO_TEXT_RULE,
  ].join("\n");
}
