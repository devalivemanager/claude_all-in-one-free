// 의존성 없는 정적 파일 서버 (node:http)
// 사용: node server.mjs  → http://localhost:3000  (PORT 환경 변수로 변경 가능)
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

/** rootDir 아래의 파일만 내려주는 서버를 만듭니다. (listen 은 호출하는 쪽에서) */
export function createStaticServer(rootDir) {
  const root = path.resolve(rootDir);

  return http.createServer(async (req, res) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405).end('Method Not Allowed');
      return;
    }

    // URL 을 디코딩한 뒤 root 밖으로 나가는 경로(../)는 막습니다.
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    } catch {
      res.writeHead(400).end('Bad Request');
      return;
    }
    if (pathname.endsWith('/')) pathname += 'index.html';
    const filePath = path.join(root, pathname);
    if (filePath !== root && !filePath.startsWith(root + path.sep)) {
      res.writeHead(403).end('Forbidden');
      return;
    }

    try {
      const info = await stat(filePath);
      if (!info.isFile()) throw new Error('not a file');
      res.writeHead(200, {
        'Content-Type': MIME_TYPES[path.extname(filePath).toLowerCase()] ?? 'application/octet-stream',
        'Content-Length': info.size,
        'Cache-Control': 'no-cache',
      });
      if (req.method === 'HEAD') res.end();
      else createReadStream(filePath).pipe(res);
    } catch {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('Not Found');
    }
  });
}

// 직접 실행했을 때만 서버를 띄웁니다. (테스트에서 import 할 때는 띄우지 않음)
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT) || 3000;
  const publicDir = path.join(path.dirname(fileURLToPath(import.meta.url)), 'public');
  createStaticServer(publicDir).listen(port, () => {
    console.log(`개발 서버 실행 중: http://localhost:${port}`);
  });
}
