// 진입점: 입력(키보드·터치)을 받고, 게임 루프를 돌리며, 화면을 그린다.
import { WORLD_HEIGHT, WORLD_WIDTH, createInitialState, startGame, togglePause, update, type GameState, type InputState } from './game';
import { render } from './render';
import { loadHighScore, saveHighScore } from './storage';

const canvas = document.querySelector<HTMLCanvasElement>('#game');
if (!canvas) throw new Error('#game 캔버스를 찾을 수 없습니다.');
const ctx = canvas.getContext('2d');
if (!ctx) throw new Error('2D 컨텍스트를 만들 수 없습니다.');

// localStorage는 환경에 따라 접근 자체가 막힐 수 있어 안전하게 꺼낸다.
function getStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

let state: GameState = createInitialState(loadHighScore(getStorage()));
const keys: InputState = { left: false, right: false };
const touch: InputState = { left: false, right: false };

/** 스페이스/탭 한 번에 해당하는 동작: 시작·재시작 또는 일시정지 전환 */
function handleAction(): void {
  state = state.phase === 'ready' || state.phase === 'over' ? startGame(state) : togglePause(state);
}

// ---------- 키보드 ----------
window.addEventListener('keydown', (e) => {
  if (e.code === 'ArrowLeft') keys.left = true;
  else if (e.code === 'ArrowRight') keys.right = true;
  else if (e.code === 'Space') {
    if (!e.repeat) handleAction();
  } else return;
  e.preventDefault(); // 스페이스로 페이지가 스크롤되지 않게 막는다
});

window.addEventListener('keyup', (e) => {
  if (e.code === 'ArrowLeft') keys.left = false;
  else if (e.code === 'ArrowRight') keys.right = false;
});

// ---------- 터치/마우스 ----------
// 진행 중: 화면 왼쪽 절반을 누르고 있으면 왼쪽, 오른쪽 절반이면 오른쪽으로 이동.
//          상단 점수판을 탭하면 일시정지.
// 그 외 화면(시작/일시정지/게임 오버): 아무 곳이나 탭하면 시작·재개.
canvas.addEventListener('pointerdown', (e) => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * WORLD_WIDTH;
  const y = ((e.clientY - rect.top) / rect.height) * WORLD_HEIGHT;

  if (state.phase !== 'playing' || y < 44) {
    handleAction();
    return;
  }
  touch.left = x < WORLD_WIDTH / 2;
  touch.right = !touch.left;
});

function releaseTouch(): void {
  touch.left = false;
  touch.right = false;
}
canvas.addEventListener('pointerup', releaseTouch);
canvas.addEventListener('pointercancel', releaseTouch);
canvas.addEventListener('pointerleave', releaseTouch);

// 다른 탭으로 이동하면 자동으로 일시정지
document.addEventListener('visibilitychange', () => {
  if (document.hidden && state.phase === 'playing') state = togglePause(state);
});

// ---------- 게임 루프 ----------
let lastTime = performance.now();

function frame(now: number): void {
  // 탭 전환 등으로 시간이 크게 튀어도 한 번에 0.05초까지만 진행한다.
  const dt = Math.min(0.05, (now - lastTime) / 1000);
  lastTime = now;

  const prevPhase = state.phase;
  const input = { left: keys.left || touch.left, right: keys.right || touch.right };
  state = update(state, dt, input, Math.random);

  // 게임 오버로 바뀐 순간 최고 점수를 저장한다.
  if (prevPhase === 'playing' && state.phase === 'over') {
    saveHighScore(getStorage(), state.score);
    releaseTouch();
  }

  render(ctx!, state);
  requestAnimationFrame(frame);
}

requestAnimationFrame(frame);
