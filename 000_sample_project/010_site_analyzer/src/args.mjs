// 명령행 인자 해석 (순수 함수)
import { parseArgs } from "node:util";
import { DEFAULTS, MAX_PAGES_LIMIT, MIN_DELAY_MS } from "./config.mjs";

export const USAGE = `사용법: node src/cli.mjs <URL> [옵션]

웹사이트의 구조·기술·디자인 특징을 분석해 보고서로 정리합니다.
콘텐츠·이미지·로고는 내려받지 않습니다. 내 사이트나 허락받은 사이트에만 사용하세요.

옵션:
  --out <폴더>        결과 폴더 (기본: ${DEFAULTS.outDir})
  --max-pages <수>    최대 방문 페이지 수, 1~${MAX_PAGES_LIMIT} (기본: ${DEFAULTS.maxPages})
  --same-origin       시작 경로 아래뿐 아니라 같은 출처 전체로 방문 범위를 넓힘
  --delay <ms>        페이지 사이 요청 간격, ${MIN_DELAY_MS} 이상 (기본: ${DEFAULTS.delayMs})
  -h, --help          도움말`;

/**
 * argv(노드 경로를 뺀 인자 배열)를 옵션 객체로 바꾼다.
 * 잘못된 값이면 Error 를 던진다.
 */
export function parseCliArgs(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      out: { type: "string", default: DEFAULTS.outDir },
      "max-pages": { type: "string", default: String(DEFAULTS.maxPages) },
      "same-origin": { type: "boolean", default: false },
      delay: { type: "string", default: String(DEFAULTS.delayMs) },
      help: { type: "boolean", short: "h", default: false },
    },
  });
  if (values.help) return { help: true };
  if (positionals.length !== 1) throw new Error("분석할 URL 을 하나 입력하세요.");

  const url = positionals[0];
  if (!/^https?:\/\//i.test(url)) throw new Error(`http:// 또는 https:// 로 시작하는 URL 이어야 합니다: ${url}`);

  const maxPages = Number(values["max-pages"]);
  if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > MAX_PAGES_LIMIT) {
    throw new Error(`--max-pages 는 1~${MAX_PAGES_LIMIT} 사이 정수여야 합니다.`);
  }
  const delayMs = Number(values.delay);
  if (!Number.isFinite(delayMs) || delayMs < MIN_DELAY_MS) {
    throw new Error(`--delay 는 ${MIN_DELAY_MS}ms 이상이어야 합니다(서버 부담을 줄이기 위한 최소 간격).`);
  }
  return { help: false, url, outDir: values.out, maxPages, sameOrigin: values["same-origin"], delayMs };
}
