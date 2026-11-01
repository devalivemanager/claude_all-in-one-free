// 테스트용 로컬 정적 서버. 외부 네트워크 없이 분석 도구를 검증하기 위해 쓴다.
// 직접 실행하면(npm run fixture) 브라우저나 CLI 로 확인할 수 있다.
import { readFile } from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SITE_DIR = fileURLToPath(new URL("../fixtures/site/", import.meta.url));
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
};

/**
 * 서버를 띄운다. port 0 이면 빈 포트를 고른다.
 * 반환: { url, requests: [{ path, userAgent, time }], close() }
 */
export async function startFixtureServer(port = 0) {
  const requests = [];
  const server = http.createServer(async (req, res) => {
    const { pathname } = new URL(req.url, "http://localhost");
    requests.push({ path: pathname, userAgent: req.headers["user-agent"] ?? "", time: Date.now() });
    // 기술 스택 감지를 확인하기 위한 헤더
    res.setHeader("Server", "FixtureServer/1.0");
    res.setHeader("X-Powered-By", "node:http");

    if (pathname === "/api/data") {
      res.writeHead(200, { "content-type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ items: [{ name: "튤립 다발", price: 25000 }, { name: "장미 한 송이", price: 5000 }] }));
      return;
    }
    const relative = pathname.endsWith("/") ? `${pathname}index.html` : pathname;
    const file = path.join(SITE_DIR, path.normalize(relative));
    if (!file.startsWith(SITE_DIR)) {
      res.writeHead(403).end();
      return;
    }
    try {
      const body = await readFile(file);
      res.writeHead(200, { "content-type": TYPES[path.extname(file)] ?? "application/octet-stream" });
      res.end(body);
    } catch {
      res.writeHead(404, { "content-type": "text/plain; charset=utf-8" }).end("없는 페이지");
    }
  });
  await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
  return {
    url: `http://127.0.0.1:${server.address().port}/`,
    requests,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const fixture = await startFixtureServer(Number(process.env.PORT ?? 4173));
  console.log(`테스트용 사이트 실행 중: ${fixture.url} (종료: Ctrl+C)`);
}
