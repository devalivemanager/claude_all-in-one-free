// URL 정규화와 방문 범위 판정 (순수 함수)

// 문서가 아닌 파일은 방문하지 않는다
const NON_PAGE_EXTENSIONS =
  /\.(pdf|zip|gz|rar|7z|png|jpe?g|gif|svg|webp|avif|ico|bmp|mp4|webm|mov|mp3|wav|woff2?|ttf|otf|css|js|mjs|json|xml|txt|csv|docx?|xlsx?|pptx?)$/i;

/**
 * URL 을 비교하기 좋은 형태로 바꾼다.
 * - 상대 경로는 base 기준으로 풀고, #해시는 지운다.
 * - http/https 가 아니면(mailto:, javascript: 등) null.
 */
export function normalizeUrl(raw, base) {
  let url;
  try {
    url = new URL(raw, base);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  url.hash = "";
  return url.href;
}

/** 두 URL 의 출처(프로토콜 + 호스트 + 포트)가 같은지 */
export function isSameOrigin(a, b) {
  try {
    return new URL(a).origin === new URL(b).origin;
  } catch {
    return false;
  }
}

/** 시작 URL 이 속한 디렉터리 경로. 예: /blog/post.html → /blog/ */
export function scopePrefix(startUrl) {
  const { pathname } = new URL(startUrl);
  return pathname.slice(0, pathname.lastIndexOf("/") + 1);
}

/**
 * 방문해도 되는 범위인지 판정한다.
 * - 다른 출처는 어떤 경우에도 방문하지 않는다.
 * - 기본: 시작 URL 의 디렉터리 아래만 (예: /docs/ 에서 시작하면 /docs/... 만)
 * - sameOrigin=true: 같은 출처 전체
 */
export function isInScope(url, startUrl, { sameOrigin = false } = {}) {
  if (!isSameOrigin(url, startUrl)) return false;
  if (sameOrigin) return true;
  return new URL(url).pathname.startsWith(scopePrefix(startUrl));
}

/** 확장자로 보아 HTML 페이지일 가능성이 있는지 */
export function looksLikePage(url) {
  return !NON_PAGE_EXTENSIONS.test(new URL(url).pathname);
}

/** robots.txt 규칙과 비교할 경로(경로 + 쿼리) */
export function pathWithQuery(url) {
  const u = new URL(url);
  return u.pathname + u.search;
}
