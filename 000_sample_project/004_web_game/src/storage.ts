// 최고 점수를 localStorage에 저장하고 읽어 오는 작은 모듈
// 테스트에서 가짜 저장소를 넣을 수 있도록 저장소 객체를 인자로 받는다.

export const HIGH_SCORE_KEY = 'overtime-escape:high-score';

/** localStorage 중 이 모듈이 사용하는 메서드만 정의한 타입 */
export type SimpleStorage = Pick<Storage, 'getItem' | 'setItem'>;

/** 저장된 최고 점수를 읽는다. 값이 없거나 잘못됐으면 0을 돌려준다. */
export function loadHighScore(storage: SimpleStorage | undefined): number {
  try {
    const value = Number(storage?.getItem(HIGH_SCORE_KEY));
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
  } catch {
    return 0; // 사생활 보호 모드 등에서 접근이 막힌 경우
  }
}

/** 기존 기록보다 높을 때만 저장한다. 저장했으면 true. */
export function saveHighScore(storage: SimpleStorage | undefined, score: number): boolean {
  if (score <= loadHighScore(storage)) return false;
  try {
    storage?.setItem(HIGH_SCORE_KEY, String(score));
    return storage !== undefined;
  } catch {
    return false;
  }
}
