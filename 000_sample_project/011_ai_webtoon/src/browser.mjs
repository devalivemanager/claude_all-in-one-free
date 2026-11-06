// Playwright 불러오기.
// playwright 는 package.json 에 넣지 않는다(이미 전역 설치된 환경을 그대로 쓰기 위해).
import { createRequire } from "node:module";

/** playwright 모듈을 돌려준다. 찾지 못하면 null */
export async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    // ES 모듈 import 는 NODE_PATH 를 보지 않으므로, 전역 설치본은 require 로 한 번 더 찾는다
    try {
      return createRequire(import.meta.url)("playwright");
    } catch {
      return null;
    }
  }
}

export const PLAYWRIGHT_INSTALL_HINT = [
  "playwright 를 찾을 수 없습니다. 이 폴더에서 아래 명령으로 설치한 뒤 다시 실행하세요.",
  "  npm i playwright && npx playwright install chromium",
].join("\n");
