// 야근 탈출 게임 로직 모듈
// 렌더링(Canvas)이나 브라우저 API에 의존하지 않는 순수 함수만 모아 두었다.
// 덕분에 Vitest로 충돌 판정, 점수, 난이도, 상태 전이를 쉽게 테스트할 수 있다.

/** 게임 화면 크기(논리 좌표, 픽셀) */
export const WORLD_WIDTH = 480;
export const WORLD_HEIGHT = 640;

/** 플레이어(직원) 크기와 기본 이동 속도 */
export const PLAYER_WIDTH = 56;
export const PLAYER_HEIGHT = 48;
export const PLAYER_BASE_SPEED = 280; // 초당 픽셀

/** 떨어지는 물건 크기 */
export const ITEM_SIZE = 36;

/** 규칙 관련 상수 */
export const START_LIVES = 3;
export const DOCUMENT_SCORE = 10;
export const COFFEE_SCORE = 5;
export const COFFEE_BOOST_MULTIPLIER = 1.6;
export const COFFEE_BOOST_DURATION = 5; // 초
export const SECONDS_PER_LEVEL = 15;

/** 게임 화면 상태: 시작 대기 → 진행 중 ⇄ 일시정지 → 게임 오버 */
export type Phase = 'ready' | 'playing' | 'paused' | 'over';

/** 떨어지는 물건 종류: 결재 서류, 커피, 야근 폭탄 */
export type ItemKind = 'document' | 'coffee' | 'bomb';

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Item extends Rect {
  id: number;
  kind: ItemKind;
  speed: number; // 초당 낙하 픽셀
}

export interface GameState {
  phase: Phase;
  player: Rect;
  items: Item[];
  score: number;
  highScore: number;
  lives: number;
  elapsed: number; // 플레이한 시간(초), 일시정지 시간은 제외
  spawnTimer: number; // 다음 물건이 나올 때까지 남은 시간(초)
  boostTime: number; // 커피 효과 남은 시간(초)
  nextItemId: number;
}

/** 이번 프레임에 눌린 방향 입력 */
export interface InputState {
  left: boolean;
  right: boolean;
}

/** 0 이상 1 미만의 난수를 돌려주는 함수(테스트에서 고정값을 넣기 위해 주입받는다) */
export type RandomFn = () => number;

/** 처음 상태(시작 화면)를 만든다. */
export function createInitialState(highScore = 0): GameState {
  return {
    phase: 'ready',
    player: {
      x: (WORLD_WIDTH - PLAYER_WIDTH) / 2,
      y: WORLD_HEIGHT - PLAYER_HEIGHT - 16,
      width: PLAYER_WIDTH,
      height: PLAYER_HEIGHT,
    },
    items: [],
    score: 0,
    highScore,
    lives: START_LIVES,
    elapsed: 0,
    spawnTimer: 0.5,
    boostTime: 0,
    nextItemId: 1,
  };
}

/** 두 사각형이 겹치는지 확인한다(AABB 충돌 판정). 모서리만 닿는 경우는 겹치지 않은 것으로 본다. */
export function isColliding(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

export interface Difficulty {
  level: number;
  fallSpeed: number; // 물건 낙하 속도(초당 픽셀)
  spawnInterval: number; // 물건 생성 간격(초)
  bombChance: number; // 폭탄이 나올 확률
}

/** 경과 시간에 따른 난이도. 15초마다 레벨이 오르고 최대 10레벨까지 어려워진다. */
export function getDifficulty(elapsed: number): Difficulty {
  const level = Math.min(10, 1 + Math.floor(elapsed / SECONDS_PER_LEVEL));
  const step = level - 1;
  return {
    level,
    fallSpeed: 140 + step * 25,
    spawnInterval: Math.max(0.35, 0.9 - step * 0.06),
    bombChance: Math.min(0.45, 0.2 + step * 0.03),
  };
}

/** 난수 하나로 물건 종류를 고른다. 커피는 항상 10%, 나머지는 폭탄 확률에 따라 나눈다. */
export function pickItemKind(r: number, bombChance: number): ItemKind {
  if (r < bombChance) return 'bomb';
  if (r < bombChance + 0.1) return 'coffee';
  return 'document';
}

/** 현재 플레이어 이동 속도(커피 효과 반영) */
export function getPlayerSpeed(state: GameState): number {
  return state.boostTime > 0 ? PLAYER_BASE_SPEED * COFFEE_BOOST_MULTIPLIER : PLAYER_BASE_SPEED;
}

/** 시작 화면이나 게임 오버 화면에서 새 게임을 시작한다. 다른 상태에서는 변화 없음. */
export function startGame(state: GameState): GameState {
  if (state.phase !== 'ready' && state.phase !== 'over') return state;
  return { ...createInitialState(state.highScore), phase: 'playing' };
}

/** 진행 중이면 일시정지, 일시정지 중이면 재개한다. */
export function togglePause(state: GameState): GameState {
  if (state.phase === 'playing') return { ...state, phase: 'paused' };
  if (state.phase === 'paused') return { ...state, phase: 'playing' };
  return state;
}

/** 물건 하나를 화면 위쪽 임의의 가로 위치에 만든다. */
function spawnItem(state: GameState, random: RandomFn, difficulty: Difficulty): Item {
  const kind = pickItemKind(random(), difficulty.bombChance);
  const x = random() * (WORLD_WIDTH - ITEM_SIZE);
  return {
    id: state.nextItemId,
    kind,
    x,
    y: -ITEM_SIZE,
    width: ITEM_SIZE,
    height: ITEM_SIZE,
    speed: difficulty.fallSpeed,
  };
}

/**
 * 한 프레임만큼 게임을 진행한다.
 * @param dt 지난 프레임 이후 흐른 시간(초)
 * 진행 중(playing)이 아니면 상태를 그대로 돌려준다.
 */
export function update(state: GameState, dt: number, input: InputState, random: RandomFn): GameState {
  if (state.phase !== 'playing') return state;

  const elapsed = state.elapsed + dt;
  const difficulty = getDifficulty(elapsed);

  // 1) 플레이어 이동(화면 밖으로 나가지 않게 제한)
  const direction = (input.right ? 1 : 0) - (input.left ? 1 : 0);
  const speed = getPlayerSpeed(state);
  const maxX = WORLD_WIDTH - state.player.width;
  const playerX = Math.min(maxX, Math.max(0, state.player.x + direction * speed * dt));
  const player = { ...state.player, x: playerX };

  // 2) 물건 생성
  let next: GameState = { ...state, elapsed, player, boostTime: Math.max(0, state.boostTime - dt) };
  let spawnTimer = state.spawnTimer - dt;
  const items = [...state.items];
  if (spawnTimer <= 0) {
    items.push(spawnItem(next, random, difficulty));
    next = { ...next, nextItemId: next.nextItemId + 1 };
    spawnTimer += difficulty.spawnInterval;
  }

  // 3) 낙하 + 충돌 처리
  let { score, lives, boostTime } = next;
  const remaining: Item[] = [];
  for (const item of items) {
    const moved = { ...item, y: item.y + item.speed * dt };
    if (isColliding(player, moved)) {
      if (moved.kind === 'document') score += DOCUMENT_SCORE;
      else if (moved.kind === 'coffee') {
        score += COFFEE_SCORE;
        boostTime = COFFEE_BOOST_DURATION;
      } else lives -= 1;
      continue; // 받은 물건은 사라진다
    }
    if (moved.y < WORLD_HEIGHT) remaining.push(moved); // 바닥 아래로 떨어진 물건은 제거
  }

  lives = Math.max(0, lives);
  const isOver = lives === 0;
  return {
    ...next,
    items: remaining,
    spawnTimer,
    score,
    lives,
    boostTime,
    phase: isOver ? 'over' : 'playing',
    highScore: Math.max(next.highScore, score),
  };
}
