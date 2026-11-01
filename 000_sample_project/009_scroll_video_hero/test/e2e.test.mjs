// Playwright E2E 테스트: 실제 브라우저에서 스크롤에 따라 그려진 프레임 번호가 바뀌는지 확인합니다.
// playwright 를 불러올 수 없으면(설치 안 됨) 테스트 전체를 건너뜁니다.
import assert from 'node:assert/strict';
import { cpSync, mkdtempSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { progressToFrameIndex } from '../public/scrub.js';
import { extractFrames, hasFfmpeg } from '../scripts/extract-frames.mjs';
import { createStaticServer } from '../server.mjs';
import { makeTestVideo } from './helpers.mjs';

/** ESM import 를 먼저 시도하고, 안 되면 require(NODE_PATH 전역 설치 포함)로 불러옵니다. */
async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    try {
      return createRequire(import.meta.url)('playwright');
    } catch {
      return null;
    }
  }
}

const playwright = await loadPlaywright();
const skipReason = !playwright
  ? 'playwright 가 없어 건너뜀 (npm i -D playwright && npx playwright install chromium)'
  : !hasFfmpeg() && 'ffmpeg 가 없어 건너뜀';

const PUBLIC_DIR = fileURLToPath(new URL('../public', import.meta.url));
const VIEWPORT = { width: 1280, height: 720 };
const HERO_SCREENS = 4; // style.css 의 .hero { height: 400vh }

describe('스크롤 스크러빙 E2E', { skip: skipReason }, () => {
  let dir;
  let server;
  let baseUrl;
  let browser;
  let frameCount;

  before(async () => {
    // public 을 임시 폴더로 복사하고 테스트용 프레임을 만들어 넣습니다. (실제 public/frames 는 건드리지 않음)
    dir = mkdtempSync(path.join(tmpdir(), 'hero-e2e-'));
    const root = path.join(dir, 'public');
    cpSync(PUBLIC_DIR, root, { recursive: true, filter: (src) => !src.includes(`${path.sep}frames`) });
    const video = path.join(dir, 'input.mp4');
    makeTestVideo(video, { seconds: 2, size: '320x180', rate: 20 });
    frameCount = extractFrames({ input: video, fps: 15, width: 320, out: path.join(root, 'frames') }).count;

    server = createStaticServer(root);
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    baseUrl = `http://127.0.0.1:${server.address().port}/`;
    browser = await playwright.chromium.launch();
  });

  after(async () => {
    await browser?.close();
    await new Promise((resolve) => (server ? server.close(resolve) : resolve()));
    rmSync(dir, { recursive: true, force: true });
  });

  /** 페이지를 열고 콘솔 에러를 모으는 배열과 함께 돌려줍니다. */
  async function openPage(contextOptions = {}) {
    const context = await browser.newContext({ viewport: VIEWPORT, ...contextOptions });
    const page = await context.newPage();
    const errors = [];
    page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()));
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(baseUrl);
    await page.waitForSelector('body[data-hero-ready="true"]');
    return { context, page, errors };
  }

  /** 스크롤한 뒤 캔버스의 data-frame 이 기대값이 될 때까지 기다리고 그 값을 돌려줍니다. */
  async function scrollAndReadFrame(page, y, expected) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForFunction(
      (want) => document.getElementById('hero-canvas').dataset.frame === String(want),
      expected,
      { timeout: 5000 },
    );
    return Number(await page.getAttribute('#hero-canvas', 'data-frame'));
  }

  test('스크롤 0 → 중간 → 끝 → 다시 위로: 프레임 번호가 증가했다가 감소한다', async () => {
    const { context, page, errors } = await openPage();
    const scrollable = VIEWPORT.height * (HERO_SCREENS - 1); // sticky 로 머무는 스크롤 거리
    const expectAt = (y) => progressToFrameIndex(y / scrollable, frameCount);

    const top = await scrollAndReadFrame(page, 0, expectAt(0));
    const middle = await scrollAndReadFrame(page, scrollable / 2, expectAt(scrollable / 2));
    const end = await scrollAndReadFrame(page, scrollable, expectAt(scrollable));
    const backMiddle = await scrollAndReadFrame(page, scrollable / 4, expectAt(scrollable / 4));
    const backTop = await scrollAndReadFrame(page, 0, 0);

    assert.equal(top, 0);
    assert.ok(middle > top && middle < end, `중간 프레임(${middle})은 처음과 끝 사이여야 함`);
    assert.equal(end, frameCount - 1);
    assert.ok(backMiddle < end && backMiddle > backTop, '위로 스크롤하면 프레임이 줄어야 함(역재생)');
    assert.equal(backTop, 0);

    // 히어로를 완전히 지나 아래 콘텐츠까지 내려가도 마지막 프레임을 유지
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(100);
    assert.equal(await page.getAttribute('#hero-canvas', 'data-frame'), String(frameCount - 1));

    // 캔버스에 실제로 그림이 그려졌는지(전부 검은색이 아닌지) 확인
    const hasPixels = await page.evaluate(() => {
      const c = document.getElementById('hero-canvas');
      const data = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      for (let i = 0; i < data.length; i += 4) if (data[i] + data[i + 1] + data[i + 2] > 0) return true;
      return false;
    });
    assert.ok(hasPixels, '캔버스가 비어 있음');

    assert.deepEqual(errors, [], `콘솔 에러: ${errors.join('\n')}`);
    await context.close();
  });

  test('prefers-reduced-motion 이면 스크롤해도 첫 프레임에 고정된다', async () => {
    const { context, page, errors } = await openPage({ reducedMotion: 'reduce' });
    assert.equal(await page.getAttribute('#hero-canvas', 'data-frame'), '0');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(200);
    assert.equal(await page.getAttribute('#hero-canvas', 'data-frame'), '0');
    assert.deepEqual(errors, []);
    await context.close();
  });

  test('모바일 화면에서도 스크롤하면 마지막 프레임까지 재생된다', async () => {
    const { context, page, errors } = await openPage({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 3,
    });
    // 모바일 CSS 는 .hero { height: 300vh }
    await scrollAndReadFrame(page, 844 * 2, frameCount - 1);
    const size = await page.evaluate(() => {
      const c = document.getElementById('hero-canvas');
      return { width: c.width, height: c.height };
    });
    assert.deepEqual(size, { width: 390 * 2, height: 844 * 2 }); // 픽셀 비율은 2 로 제한
    assert.deepEqual(errors, []);
    await context.close();
  });
});
