// 테스트용 최소 대본. 필요한 부분만 덮어써서 쓴다.
export function sampleEpisode(overrides = {}) {
  return {
    title: "시험 회차",
    episode: 1,
    width: 720,
    style: "깔끔한 선, 밝은 색감",
    characters: {
      a: { name: "가", desc: "짧은 갈색 머리에 파란 셔츠", look: { hair: "#6b4a3a", hairStyle: "short", skin: "#f3d6bd", shirt: "#4f86c6" } },
      b: { name: "나", desc: "긴 검은 머리에 분홍 셔츠", look: { hair: "#222222", hairStyle: "long", skin: "#f1d0b5", shirt: "#e58fa6" } },
    },
    panels: [
      {
        id: "p1",
        height: 520,
        background: "office",
        scene: "사무실에서 두 사람이 이야기한다",
        cast: [
          { who: "a", x: 0.3, expression: "happy" },
          { who: "b", x: 0.7, expression: "neutral" },
        ],
        lines: [{ who: "a", text: "안녕하세요" }],
      },
    ],
    ...overrides,
  };
}
