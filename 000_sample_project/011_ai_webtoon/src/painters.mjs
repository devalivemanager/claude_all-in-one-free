// 그림 도구(painter).
// - svg : 기본값. 외부 서비스 없이 코드로 그린다(characters.mjs). paint() 가 null 을 돌려주면 코드 그림을 쓴다.
// - api : 이미지 생성 서비스에 프롬프트를 보내 그림을 받는다.
//         서비스마다 요청 형식이 다르므로, 여기서는 아래의 단순한 형식만 정해 둔다.
//         실제 서비스에 붙일 때는 이 형식으로 바꿔 주는 작은 중계 서버나 함수를 만든다.
//           요청: POST { prompt, width, height }   (Authorization: Bearer <키>)
//           응답: { imageBase64, mimeType }
// 키는 환경변수(IMAGE_API_KEY)로만 받는다. 코드·파일에 쓰지 않는다.

export function createSvgPainter() {
  return { name: "svg", async paint() { return null; } };
}

const ALLOWED_MIME = /^image\/(png|jpeg|webp)$/;

export function createImageApiPainter({ endpoint, apiKey, fetchImpl = fetch } = {}) {
  if (!endpoint) throw new Error("이미지 API 주소(IMAGE_API_URL)가 필요합니다.");
  if (!apiKey) throw new Error("이미지 API 키(IMAGE_API_KEY)가 필요합니다. 키는 환경변수로만 넣으세요.");
  return {
    name: "api",
    async paint({ prompt, width, height }) {
      const response = await fetchImpl(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ prompt, width, height }),
      });
      if (!response.ok) throw new Error(`이미지 API 가 ${response.status} 로 응답했습니다.`);
      const data = await response.json();
      if (typeof data?.imageBase64 !== "string" || data.imageBase64 === "") {
        throw new Error("이미지 API 응답에 imageBase64 가 없습니다.");
      }
      const mime = data.mimeType ?? "image/png";
      if (!ALLOWED_MIME.test(mime)) throw new Error(`지원하지 않는 이미지 형식입니다: ${mime}`);
      return `data:${mime};base64,${data.imageBase64}`;
    },
  };
}
