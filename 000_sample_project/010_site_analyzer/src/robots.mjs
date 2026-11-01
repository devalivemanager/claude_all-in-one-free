// robots.txt 읽기와 허용 여부 판정

/**
 * robots.txt 본문을 그룹 목록으로 바꾼다.
 * 반환: [{ agents: ["*"], rules: [{ type: "allow" | "disallow", path: "/private/" }] }]
 */
export function parseRobots(text) {
  const groups = [];
  let current = null;
  let lastWasAgent = false;

  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.replace(/#.*$/, "").trim();
    const sep = line.indexOf(":");
    if (sep === -1) continue;
    const key = line.slice(0, sep).trim().toLowerCase();
    const value = line.slice(sep + 1).trim();

    if (key === "user-agent") {
      // User-agent 가 연달아 나오면 같은 그룹, 규칙 뒤에 나오면 새 그룹
      if (!current || !lastWasAgent) {
        current = { agents: [], rules: [] };
        groups.push(current);
      }
      current.agents.push(value.toLowerCase());
      lastWasAgent = true;
    } else if ((key === "allow" || key === "disallow") && current) {
      // 빈 Disallow 는 "모두 허용" 이라는 뜻이므로 규칙으로 저장하지 않는다
      if (value) current.rules.push({ type: key, path: value });
      lastWasAgent = false;
    } else {
      lastWasAgent = false;
    }
  }
  return groups;
}

/** robots 패턴(* 와 끝의 $ 지원)을 정규식으로 바꾼다 */
function patternToRegExp(pattern) {
  const anchored = pattern.endsWith("$");
  const body = anchored ? pattern.slice(0, -1) : pattern;
  const escaped = body.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp("^" + escaped + (anchored ? "$" : ""));
}

/**
 * 경로가 허용되는지 판정한다.
 * - 이 도구 이름과 같은 User-agent 그룹이 있으면 그것을, 없으면 * 그룹을 쓴다.
 * - 가장 길게 일치하는 규칙이 이긴다. 길이가 같으면 Allow 가 이긴다.
 */
export function isAllowed(groups, path, botToken) {
  const token = botToken.toLowerCase();
  let matched = groups.filter((g) => g.agents.includes(token));
  if (matched.length === 0) matched = groups.filter((g) => g.agents.includes("*"));

  let best = null;
  for (const rule of matched.flatMap((g) => g.rules)) {
    if (!patternToRegExp(rule.path).test(path)) continue;
    const longer = !best || rule.path.length > best.path.length;
    const sameLengthAllow = best && rule.path.length === best.path.length && rule.type === "allow";
    if (longer || sameLengthAllow) best = rule;
  }
  return !best || best.type === "allow";
}

// 서버 오류 등으로 robots.txt 를 확인할 수 없을 때 쓰는 "전부 금지" 규칙
const DENY_ALL = [{ agents: ["*"], rules: [{ type: "disallow", path: "/" }] }];

/**
 * 사이트의 robots.txt 를 가져온다.
 * - 2xx: 내용대로 따른다.
 * - 4xx(없음): 제한 없음으로 본다.
 * - 5xx·네트워크 오류: 확인할 수 없으므로 안전하게 "전부 금지" 로 본다.
 */
export async function fetchRobots(origin, userAgent, fetchImpl = fetch) {
  const url = new URL("/robots.txt", origin).href;
  try {
    const res = await fetchImpl(url, {
      headers: { "user-agent": userAgent },
      signal: AbortSignal.timeout(10_000),
    });
    if (res.ok) return { url, status: "found", groups: parseRobots(await res.text()) };
    if (res.status >= 400 && res.status < 500) return { url, status: "missing", groups: [] };
    return { url, status: "error", note: `HTTP ${res.status}`, groups: DENY_ALL };
  } catch (err) {
    return { url, status: "error", note: err.message, groups: DENY_ALL };
  }
}
