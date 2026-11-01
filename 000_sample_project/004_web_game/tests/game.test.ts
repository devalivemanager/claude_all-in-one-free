import { describe, expect, it } from 'vitest';
import {
  COFFEE_BOOST_DURATION,
  DOCUMENT_SCORE,
  ITEM_SIZE,
  PLAYER_BASE_SPEED,
  START_LIVES,
  WORLD_HEIGHT,
  WORLD_WIDTH,
  createInitialState,
  getDifficulty,
  getPlayerSpeed,
  isColliding,
  pickItemKind,
  startGame,
  togglePause,
  update,
  type GameState,
  type Item,
  type ItemKind,
} from '../src/game';

const NO_INPUT = { left: false, right: false };
const fixedRandom = (value: number) => () => value;

/** 진행 중 상태를 만들고, 새 물건이 바로 생기지 않도록 생성 타이머를 넉넉히 둔다. */
function playingState(overrides: Partial<GameState> = {}): GameState {
  return { ...startGame(createInitialState()), spawnTimer: 100, ...overrides };
}

/** 플레이어 바로 위에 겹치도록 물건을 놓는다. */
function itemOnPlayer(state: GameState, kind: ItemKind): Item {
  return {
    id: 99,
    kind,
    x: state.player.x,
    y: state.player.y,
    width: ITEM_SIZE,
    height: ITEM_SIZE,
    speed: 0,
  };
}

describe('충돌 판정 isColliding', () => {
  const base = { x: 0, y: 0, width: 10, height: 10 };

  it('겹치는 사각형은 충돌이다', () => {
    expect(isColliding(base, { x: 5, y: 5, width: 10, height: 10 })).toBe(true);
  });

  it('떨어져 있는 사각형은 충돌이 아니다', () => {
    expect(isColliding(base, { x: 20, y: 0, width: 10, height: 10 })).toBe(false);
  });

  it('모서리만 맞닿은 경우는 충돌이 아니다', () => {
    expect(isColliding(base, { x: 10, y: 0, width: 10, height: 10 })).toBe(false);
    expect(isColliding(base, { x: 0, y: 10, width: 10, height: 10 })).toBe(false);
  });

  it('한 사각형이 다른 사각형 안에 완전히 들어가도 충돌이다', () => {
    expect(isColliding(base, { x: 2, y: 2, width: 3, height: 3 })).toBe(true);
  });
});

describe('난이도 getDifficulty', () => {
  it('시작할 때는 1레벨이다', () => {
    expect(getDifficulty(0).level).toBe(1);
    expect(getDifficulty(14.9).level).toBe(1);
  });

  it('15초마다 레벨이 오르고 더 빠르고 자주, 폭탄도 많아진다', () => {
    const easy = getDifficulty(0);
    const hard = getDifficulty(30);
    expect(hard.level).toBe(3);
    expect(hard.fallSpeed).toBeGreaterThan(easy.fallSpeed);
    expect(hard.spawnInterval).toBeLessThan(easy.spawnInterval);
    expect(hard.bombChance).toBeGreaterThan(easy.bombChance);
  });

  it('최대 10레벨에서 멈추고 생성 간격은 하한을 지킨다', () => {
    const max = getDifficulty(10_000);
    expect(max.level).toBe(10);
    expect(max.spawnInterval).toBeGreaterThanOrEqual(0.35);
    expect(max.bombChance).toBeLessThanOrEqual(0.45);
  });
});

describe('물건 종류 pickItemKind', () => {
  it('난수 구간에 따라 폭탄 → 커피 → 서류 순서로 고른다', () => {
    expect(pickItemKind(0.1, 0.2)).toBe('bomb');
    expect(pickItemKind(0.25, 0.2)).toBe('coffee');
    expect(pickItemKind(0.9, 0.2)).toBe('document');
  });
});

describe('상태 전이', () => {
  it('처음에는 시작 대기 상태이고 생명은 3개다', () => {
    const state = createInitialState(42);
    expect(state.phase).toBe('ready');
    expect(state.lives).toBe(START_LIVES);
    expect(state.highScore).toBe(42);
  });

  it('시작 대기 → 진행 중으로 바뀐다', () => {
    expect(startGame(createInitialState()).phase).toBe('playing');
  });

  it('진행 중 ⇄ 일시정지를 오간다', () => {
    const playing = playingState();
    const paused = togglePause(playing);
    expect(paused.phase).toBe('paused');
    expect(togglePause(paused).phase).toBe('playing');
  });

  it('시작 대기 상태에서는 일시정지가 되지 않는다', () => {
    expect(togglePause(createInitialState()).phase).toBe('ready');
  });

  it('진행 중에는 startGame을 불러도 초기화되지 않는다', () => {
    const playing = playingState({ score: 50 });
    expect(startGame(playing)).toBe(playing);
  });

  it('게임 오버 후 다시 시작하면 점수·생명은 초기화되고 최고 점수는 유지된다', () => {
    const over: GameState = { ...playingState(), phase: 'over', score: 120, highScore: 120, lives: 0 };
    const restarted = startGame(over);
    expect(restarted.phase).toBe('playing');
    expect(restarted.score).toBe(0);
    expect(restarted.lives).toBe(START_LIVES);
    expect(restarted.highScore).toBe(120);
  });

  it('일시정지 중에는 시간이 흐르지 않는다', () => {
    const paused = togglePause(playingState());
    const after = update(paused, 1, { left: true, right: false }, fixedRandom(0.5));
    expect(after).toBe(paused);
  });
});

describe('한 프레임 진행 update', () => {
  it('왼쪽 입력이면 기본 속도만큼 왼쪽으로 움직인다', () => {
    const state = playingState();
    const after = update(state, 0.1, { left: true, right: false }, fixedRandom(0.5));
    expect(after.player.x).toBeCloseTo(state.player.x - PLAYER_BASE_SPEED * 0.1);
  });

  it('플레이어는 화면 밖으로 나가지 않는다', () => {
    const state = playingState();
    const left = update(state, 10, { left: true, right: false }, fixedRandom(0.5));
    const right = update(state, 10, { left: false, right: true }, fixedRandom(0.5));
    expect(left.player.x).toBe(0);
    expect(right.player.x).toBe(WORLD_WIDTH - state.player.width);
  });

  it('결재 서류를 받으면 점수가 오르고 서류는 사라진다', () => {
    const state = playingState();
    const after = update({ ...state, items: [itemOnPlayer(state, 'document')] }, 0.016, NO_INPUT, fixedRandom(0.5));
    expect(after.score).toBe(DOCUMENT_SCORE);
    expect(after.items).toHaveLength(0);
    expect(after.highScore).toBe(DOCUMENT_SCORE);
  });

  it('커피를 받으면 일정 시간 이동 속도가 빨라진다', () => {
    const state = playingState();
    const after = update({ ...state, items: [itemOnPlayer(state, 'coffee')] }, 0.016, NO_INPUT, fixedRandom(0.5));
    expect(after.boostTime).toBe(COFFEE_BOOST_DURATION);
    expect(getPlayerSpeed(after)).toBeGreaterThan(PLAYER_BASE_SPEED);

    const later = update(after, COFFEE_BOOST_DURATION, NO_INPUT, fixedRandom(0.5));
    expect(later.boostTime).toBe(0);
    expect(getPlayerSpeed(later)).toBe(PLAYER_BASE_SPEED);
  });

  it('야근 폭탄에 맞으면 생명이 하나 줄어든다', () => {
    const state = playingState();
    const after = update({ ...state, items: [itemOnPlayer(state, 'bomb')] }, 0.016, NO_INPUT, fixedRandom(0.5));
    expect(after.lives).toBe(START_LIVES - 1);
    expect(after.phase).toBe('playing');
  });

  it('마지막 생명에서 폭탄에 맞으면 게임 오버가 된다', () => {
    const state = playingState({ lives: 1, score: 30, highScore: 20 });
    const after = update({ ...state, items: [itemOnPlayer(state, 'bomb')] }, 0.016, NO_INPUT, fixedRandom(0.5));
    expect(after.lives).toBe(0);
    expect(after.phase).toBe('over');
    expect(after.highScore).toBe(30);
  });

  it('생성 타이머가 끝나면 화면 위에 새 물건이 생긴다', () => {
    const state = playingState({ spawnTimer: 0.01 });
    const after = update(state, 0.016, NO_INPUT, fixedRandom(0.9));
    expect(after.items).toHaveLength(1);
    expect(after.items[0].kind).toBe('document');
    expect(after.items[0].y).toBeLessThan(0);
    expect(after.spawnTimer).toBeGreaterThan(0);
  });

  it('바닥 아래로 떨어진 물건은 제거되고 점수 변화는 없다', () => {
    const state = playingState();
    const falling: Item = { id: 1, kind: 'document', x: 0, y: WORLD_HEIGHT - 1, width: ITEM_SIZE, height: ITEM_SIZE, speed: 200 };
    const farFromPlayer = { ...state, player: { ...state.player, x: WORLD_WIDTH - state.player.width } };
    const after = update({ ...farFromPlayer, items: [falling] }, 0.1, NO_INPUT, fixedRandom(0.5));
    expect(after.items).toHaveLength(0);
    expect(after.score).toBe(0);
  });

  it('같은 프레임에 폭탄 두 개를 마지막 생명에서 맞아도 생명은 0이고 게임 오버다', () => {
    // 생명이 -1 로 내려가면 lives === 0 판정을 지나쳐 게임이 끝나지 않는다.
    const state = playingState({ lives: 1 });
    const bomb = itemOnPlayer(state, 'bomb');
    const after = update({ ...state, items: [bomb, { ...bomb, id: 100 }] }, 0.016, NO_INPUT, fixedRandom(0.5));
    expect(after.lives).toBe(0);
    expect(after.phase).toBe('over');
  });

  it('이번 프레임에 떨어져 플레이어와 겹친 물건도 받은 것으로 친다', () => {
    // 이동 전에는 플레이어 위에 떨어져 있고, 이동 후에야 겹친다.
    const state = playingState();
    const above: Item = { ...itemOnPlayer(state, 'document'), y: state.player.y - ITEM_SIZE - 5, speed: 100 };
    const after = update({ ...state, items: [above] }, 0.1, NO_INPUT, fixedRandom(0.5));
    expect(after.score).toBe(DOCUMENT_SCORE);
  });

  it('진행 시간이 쌓여 15초가 지나면 레벨이 오른다', () => {
    let state = playingState();
    for (let i = 0; i < 300; i += 1) state = update(state, 0.05, NO_INPUT, fixedRandom(0.5));
    expect(state.elapsed).toBeCloseTo(15);
    expect(getDifficulty(state.elapsed + 0.01).level).toBe(2);
  });
});

describe('규칙 경계 보강', () => {
  it('왼쪽에서 모서리만 맞닿은 경우도 충돌이 아니다', () => {
    const base = { x: 10, y: 0, width: 10, height: 10 };
    expect(isColliding(base, { x: 0, y: 0, width: 10, height: 10 })).toBe(false);
  });

  it('커피는 폭탄 확률 바로 다음 10% 구간이다', () => {
    expect(pickItemKind(0.29, 0.2)).toBe('coffee');
    expect(pickItemKind(0.31, 0.2)).toBe('document');
  });
});
