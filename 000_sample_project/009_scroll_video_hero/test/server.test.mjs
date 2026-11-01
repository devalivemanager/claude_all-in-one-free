// 정적 파일 서버 테스트
import assert from 'node:assert/strict';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createStaticServer } from '../server.mjs';

const PUBLIC_DIR = fileURLToPath(new URL('../public', import.meta.url));

describe('정적 파일 서버', () => {
  let server;
  let baseUrl;

  before(async () => {
    server = createStaticServer(PUBLIC_DIR);
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve)); // 0: 빈 포트 자동 선택
    baseUrl = `http://127.0.0.1:${server.address().port}`;
  });
  after(() => new Promise((resolve) => server.close(resolve)));

  test('/ 는 index.html 을 HTML 로 내려준다', async () => {
    const res = await fetch(`${baseUrl}/`);
    assert.equal(res.status, 200);
    assert.match(res.headers.get('content-type'), /text\/html/);
    assert.match(await res.text(), /hero-canvas/);
  });

  test('ES 모듈은 JavaScript MIME 타입으로 내려준다', async () => {
    const res = await fetch(`${baseUrl}/scrub.js`);
    assert.equal(res.status, 200);
    assert.match(res.headers.get('content-type'), /text\/javascript/);
  });

  test('없는 파일은 404', async () => {
    const res = await fetch(`${baseUrl}/nope.txt`);
    assert.equal(res.status, 404);
  });

  test('public 폴더 밖(../)으로 나가는 요청은 막는다', async () => {
    const res = await fetch(`${baseUrl}/..%2Fpackage.json`);
    assert.notEqual(res.status, 200);
  });
});
