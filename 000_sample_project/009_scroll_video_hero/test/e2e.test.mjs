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

  // README 4번: 이벤트에서는 예약만, 그리기는 화면 갱신당 한 번. 프레임 번호가 같으면 다시 그리지 않는다.
  test('스크롤 이벤트가 몰려도 한 번만 그리고, 프레임 번호가 같으면 다시 그리지 않는다', async () => {
    const context = await browser.newContext({ viewport: VIEWPORT });
    const page = await context.newPage();
    await page.addInitScript(() => {
      const original = CanvasRenderingContext2D.prototype.drawImage;
      window.__draws = 0;
      CanvasRenderingContext2D.prototype.drawImage = function (...args) {
        window.__draws += 1;
        return original.apply(this, args);
      };
    });
    await page.goto(baseUrl);
    await page.waitForSelector('body[data-hero-ready="true"]');
    await page.waitForTimeout(100);

    const before = await page.evaluate(() => window.__draws);
    await page.evaluate(() => window.scrollTo(0, 1)); // 1px 는 같은 프레임
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(() => window.__draws), before, '같은 프레임인데 다시 그림');

    const burst = await page.evaluate(async () => {
      const start = window.__draws;
      for (let y = 0; y < 100; y += 1) {
        window.scrollTo(0, 400 + y * 3);
        window.dispatchEvent(new Event('scroll'));
      }
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return window.__draws - start;
    });
    assert.equal(burst, 1, `스크롤 100번에 ${burst}번 그림`);
    await context.close();
  });

  // README 6번(진행률 표시)과 hero.js 주석(실패해도 전체 로딩이 멈추지 않음)
  test('프레임 하나를 받지 못해도 로딩이 끝까지 진행되고 진행률을 보여 준다', async () => {
    const context = await browser.newContext({ viewport: VIEWPORT });
    const page = await context.newPage();
    await page.route('**/frames/f_0002.jpg', (route) => route.abort());
    const texts = new Set();
    await page.exposeFunction('__loaderText', (text) => texts.add(text));
    await page.addInitScript(() => {
      new MutationObserver(() => {
        const el = document.getElementById('hero-loader-text');
        if (el) window.__loaderText(el.textContent);
      }).observe(document, { subtree: true, childList: true, characterData: true });
    });
    await page.goto(baseUrl);
    await page.waitForSelector('body[data-hero-ready="true"]', { timeout: 5000 });
    await page.waitForTimeout(100);
    assert.ok(texts.has(`프레임 불러오는 중… ${frameCount} / ${frameCount}`), `마지막 진행률 문구 없음: ${[...texts].join(', ')}`);
    await context.close();
  });

  // 홀마크 정적 검사에서 나온 기본기 : 링크 미리보기 설명, 키보드 포커스 표시, 로딩 막대는 transform 으로
  test('설명 메타·키보드 포커스 표시가 있고, 로딩 막대는 width 대신 transform 으로 움직인다', async () => {
    const context = await browser.newContext({ viewport: VIEWPORT });
    const page = await context.newPage();
    await page.goto(baseUrl);
    await page.waitForSelector('body[data-hero-ready="true"]', { timeout: 5000 });
    const desc = await page.evaluate(() => document.querySelector('meta[name="description"]')?.content ?? null);
    await page.keyboard.press('Tab');
    const focus = await page.evaluate(() => {
      const el = document.activeElement;
      const cs = getComputedStyle(el);
      return { tag: el.tagName, style: cs.outlineStyle, width: parseFloat(cs.outlineWidth) };
    });
    const problems = [];
    if (!(desc && desc.length >= 10)) problems.push(`meta description: ${desc}`);
    if (focus.tag !== 'A' || focus.style === 'none' || !(focus.width >= 2)) problems.push(`포커스 ${JSON.stringify(focus)}`);
    const fill = await page.evaluate(() => {
      const el = document.getElementById('hero-loader-fill');
      const cs = getComputedStyle(el);
      return { inlineWidth: el.style.width, transform: el.style.transform, transition: cs.transitionProperty };
    });
    if (fill.inlineWidth !== '' || fill.transform !== 'scaleX(1)' || /width/.test(fill.transition)) problems.push(`로딩 막대 ${JSON.stringify(fill)}`);
    assert.deepEqual(problems, []);
    await context.close();
  });

  // README 7번: 움직임 줄이기면 첫 프레임만 받고, 긴 스크롤 구간도 없앤다.
  test('움직임 줄이기면 첫 프레임 한 장만 받고, 히어로가 화면 한 개 높이다', async () => {
    const context = await browser.newContext({ viewport: VIEWPORT, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const requested = [];
    page.on('request', (req) => /f_\d{4}\.jpg/.test(req.url()) && requested.push(req.url()));
    await page.goto(baseUrl);
    await page.waitForSelector('body[data-hero-ready="true"]');
    const heroHeight = await page.evaluate(() => document.getElementById('hero').getBoundingClientRect().height);
    assert.equal(requested.length, 1);
    assert.ok(requested[0].endsWith('f_0001.jpg'));
    assert.equal(heroHeight, VIEWPORT.height);
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
