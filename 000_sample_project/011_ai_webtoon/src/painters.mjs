// 그림 도구(painter).
// - svg : 기본값. 외부 서비스 없이 코드로 그린다(characters.mjs). paint() 가 null 을 돌려주면 코드 그림을 쓴다.
// - api : 이미지 생성 서비스에 프롬프트를 보내 그림을 받는다.
//         서비스마다 요청 형식이 다르므로, 여기서는 아래의 단순한 형식만 정해 둔다.
//         실제 서비스에 붙일 때는 이 형식으로 바꿔 주는 작은 중계 서버나 함수를 만든다.
//           요청: POST { prompt, width, height }   (Authorization: Bearer <키>)
//           응답: { imageBase64, mimeType }
// - files : 사람이 이미지 AI 로 직접 만든 그림 파일을 폴더에서 읽는다. 파일 이름은 컷 id(예: p1.png).
// 키는 환경변수(IMAGE_API_KEY)로만 받는다. 코드·파일에 쓰지 않는다.
import { readFile, stat } from "node:fs/promises";
import { join } from "node:path";

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

// 그림 파일 폴더에서 찾는 확장자(이 순서로 찾는다)와, 파일 앞부분으로 확인하는 실제 형식
export const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];
export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const SAFE_ID = /^[A-Za-z0-9_-]+$/;

/** 파일 앞부분(매직 바이트)으로 이미지 형식을 알아낸다. 모르는 형식이면 null */
export function sniffImageMime(bytes) {
  const b = bytes;
  if (b.length >= 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return "image/png";
  if (b.length >= 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return "image/jpeg";
  if (b.length >= 12 && b.toString("ascii", 0, 4) === "RIFF" && b.toString("ascii", 8, 12) === "WEBP") return "image/webp";
  return null;
}

/**
 * 폴더의 그림 파일을 컷에 까는 painter. 컷 id 가 p3 이면 p3.png → p3.jpg → p3.jpeg → p3.webp 순서로 찾는다.
 * 파일이 없거나, 여러 개이거나, 이미지가 아니거나, 너무 크면 오류를 던진다.
 * (buildEpisode 가 그 컷만 코드 그림으로 대신하고 경고로 남긴다)
 */
export function createFolderPainter({ dir } = {}) {
  if (!dir) throw new Error("그림 파일 폴더가 필요합니다.");
  return {
    name: "files",
    async paint({ panel }) {
      if (!SAFE_ID.test(panel.id)) throw new Error(`컷 id '${panel.id}' 는 파일 이름으로 쓸 수 없습니다(영문·숫자·_·- 만)`);
      const found = [];
      for (const ext of IMAGE_EXTENSIONS) {
        const file = join(dir, panel.id + ext);
        const info = await stat(file).catch(() => null);
        if (info?.isFile()) found.push({ file, size: info.size });
      }
      if (found.length === 0) throw new Error(`그림 파일이 없습니다(${panel.id}.png/.jpg/.jpeg/.webp)`);
      if (found.length > 1) throw new Error(`같은 컷의 그림 파일이 여러 개입니다: ${found.map((f) => f.file.split(/[\\/]/).pop()).join(", ")}`);
      const [{ file, size }] = found;
      if (size > MAX_IMAGE_BYTES) throw new Error(`그림 파일이 너무 큽니다(${Math.round(size / 1024 / 1024)}MB, 최대 10MB)`);
      const bytes = await readFile(file);
      const mime = sniffImageMime(bytes);
      if (!mime) throw new Error(`이미지 파일이 아닙니다(PNG·JPEG·WebP 만): ${file.split(/[\\/]/).pop()}`);
      return `data:${mime};base64,${bytes.toString("base64")}`;
    },
  };
}
