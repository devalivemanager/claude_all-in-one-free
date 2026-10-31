import { describe, expect, it } from 'vitest';
import { HIGH_SCORE_KEY, loadHighScore, saveHighScore, type SimpleStorage } from '../src/storage';

/** 메모리에만 저장하는 가짜 localStorage */
function createMemoryStorage(initial: Record<string, string> = {}): SimpleStorage {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
  };
}

describe('최고 점수 저장소', () => {
  it('저장된 값이 없으면 0을 돌려준다', () => {
    expect(loadHighScore(createMemoryStorage())).toBe(0);
    expect(loadHighScore(undefined)).toBe(0);
  });

  it('잘못된 값이 저장돼 있으면 0으로 본다', () => {
    expect(loadHighScore(createMemoryStorage({ [HIGH_SCORE_KEY]: 'abc' }))).toBe(0);
  });

  it('더 높은 점수일 때만 저장한다', () => {
    const storage = createMemoryStorage();
    expect(saveHighScore(storage, 50)).toBe(true);
    expect(saveHighScore(storage, 30)).toBe(false);
    expect(loadHighScore(storage)).toBe(50);
  });

  it('저장소 접근이 막혀 있어도 에러 없이 동작한다', () => {
    const broken: SimpleStorage = {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    };
    expect(loadHighScore(broken)).toBe(0);
    expect(saveHighScore(broken, 10)).toBe(false);
  });
});
