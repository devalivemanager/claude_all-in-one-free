// 스크롤 스크러빙 히어로 (외부 라이브러리 없이 순수 JS)
// 흐름: manifest.json 읽기 → 프레임 이미지 프리로드 → 스크롤마다 진행률 계산 → rAF 에서 해당 프레임을 캔버스에 그림
import { coverRect, frameFileName, progressFromRect, progressToFrameIndex } from './scrub.js';

const FRAMES_DIR = 'frames/';
const MAX_DPR = 2; // 고해상도 화면에서도 캔버스가 너무 커지지 않도록 제한

const hero = document.getElementById('hero');
const canvas = document.getElementById('hero-canvas');
const ctx = canvas.getContext('2d');
const loader = document.getElementById('hero-loader');
const loaderText = document.getElementById('hero-loader-text');
const loaderFill = document.getElementById('hero-loader-fill');

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const state = {
  images: [], // 인덱스별 Image 객체 (로드 전이면 complete 가 false)
  drawnIndex: -1, // 마지막으로 캔버스에 그린 프레임
  rafId: 0,
};

/** 화면 크기와 기기 픽셀 비율에 맞춰 캔버스 해상도를 조정합니다. */
function resizeCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
  canvas.width = Math.round(canvas.clientWidth * dpr);
  canvas.height = Math.round(canvas.clientHeight * dpr);
  state.drawnIndex = -1; // 해상도가 바뀌면 캔버스가 지워지므로 다시 그려야 함
}

/** 지정한 프레임을 cover 방식으로 그립니다. 아직 로드되지 않았으면 아무것도 하지 않습니다. */
function drawFrame(index) {
  const img = state.images[index];
  if (!img || !img.complete || img.naturalWidth === 0) return;
  const r = coverRect(img.naturalWidth, img.naturalHeight, canvas.width, canvas.height);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, r.x, r.y, r.width, r.height);
  state.drawnIndex = index;
  canvas.dataset.frame = String(index); // E2E 테스트에서 현재 프레임 확인용
}

/** 현재 스크롤 위치에 맞는 프레임을 그립니다. rAF 콜백에서만 호출됩니다. */
function render() {
  state.rafId = 0;
  const rect = hero.getBoundingClientRect();
  const progress = reducedMotion ? 0 : progressFromRect(rect.top, rect.height, window.innerHeight);
  hero.style.setProperty('--progress', progress.toFixed(4));
  const index = progressToFrameIndex(progress, state.images.length);
  if (index !== state.drawnIndex) drawFrame(index);
}

/** 스크롤 이벤트가 아무리 많이 와도 한 화면 갱신(프레임)당 한 번만 그리도록 묶습니다. */
function requestRender() {
  if (!state.rafId) state.rafId = requestAnimationFrame(render);
}

function updateLoader(loaded, total) {
  loaderText.textContent = `프레임 불러오는 중… ${loaded} / ${total}`;
  loaderFill.style.transform = `scaleX(${loaded / total})`;
}

/** 이미지 하나를 불러옵니다. 실패해도 전체 로딩이 멈추지 않도록 항상 resolve 합니다. */
function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => resolve(img);
    img.onerror = () => resolve(img);
    img.src = src;
  });
}

async function init() {
  let manifest;
  try {
    const res = await fetch(`${FRAMES_DIR}manifest.json`, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    manifest = await res.json();
  } catch {
    loaderText.textContent = '프레임이 없습니다. 터미널에서 npm run demo 를 먼저 실행하세요.';
    return;
  }

  // 움직임 줄이기 설정이면 첫 프레임만 받아서 고정합니다.
  const total = reducedMotion ? 1 : manifest.count;
  let loaded = 0;
  updateLoader(0, total);

  state.images = Array.from({ length: total }, () => null);
  resizeCanvas();

  const jobs = state.images.map((_, i) =>
    loadImage(FRAMES_DIR + frameFileName(i)).then((img) => {
      state.images[i] = img;
      loaded += 1;
      updateLoader(loaded, total);
      requestRender(); // 첫 프레임 등 필요한 프레임이 도착하면 바로 그려 봄
    }),
  );
  await Promise.all(jobs);

  loader.classList.add('is-done');
  document.body.dataset.heroReady = 'true'; // E2E 테스트에서 로딩 완료 확인용
  state.drawnIndex = -1;
  requestRender();
}

window.addEventListener('scroll', requestRender, { passive: true });
window.addEventListener('resize', () => {
  resizeCanvas();
  requestRender();
});

init();
