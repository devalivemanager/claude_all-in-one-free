// scrub.js 순수 함수 단위 테스트
import assert from 'node:assert/strict';
import { describe, test } from 'node:test';
import { clamp, coverRect, frameFileName, progressFromRect, progressToFrameIndex } from '../public/scrub.js';

describe('clamp', () => {
  test('범위 안의 값은 그대로 둔다', () => assert.equal(clamp(0.5, 0, 1), 0.5));
  test('범위 밖의 값은 경계로 자른다', () => {
    assert.equal(clamp(-3, 0, 1), 0);
    assert.equal(clamp(7, 0, 1), 1);
  });
  test('NaN 은 최솟값으로 취급한다', () => assert.equal(clamp(NaN, 0, 1), 0));
});

describe('progressFromRect', () => {
  // 섹션 높이 4000, 화면 높이 1000 → sticky 로 머무는 스크롤 구간은 3000px
  test('섹션 맨 위가 화면 위에 있으면 0', () => assert.equal(progressFromRect(0, 4000, 1000), 0));
  test('섹션이 아직 아래에 있으면 0', () => assert.equal(progressFromRect(500, 4000, 1000), 0));
  test('구간의 절반을 스크롤하면 0.5', () => assert.equal(progressFromRect(-1500, 4000, 1000), 0.5));
  test('구간 끝을 지나면 1 로 고정', () => {
    assert.equal(progressFromRect(-3000, 4000, 1000), 1);
    assert.equal(progressFromRect(-9999, 4000, 1000), 1);
  });
  test('섹션이 화면보다 짧으면 항상 0', () => assert.equal(progressFromRect(-100, 800, 1000), 0));
});

describe('progressToFrameIndex', () => {
  test('0 은 첫 프레임, 1 은 마지막 프레임', () => {
    assert.equal(progressToFrameIndex(0, 90), 0);
    assert.equal(progressToFrameIndex(1, 90), 89);
  });
  test('중간 값은 반올림한다', () => {
    assert.equal(progressToFrameIndex(0.5, 11), 5);
    assert.equal(progressToFrameIndex(0.5, 10), 5); // 4.5 → 5
  });
  test('진행률이 커지면 프레임 번호도 줄지 않는다(단조 증가)', () => {
    let prev = -1;
    for (let p = 0; p <= 1; p += 0.01) {
      const index = progressToFrameIndex(p, 37);
      assert.ok(index >= prev);
      prev = index;
    }
  });
  test('범위를 벗어난 진행률은 잘라서 처리', () => {
    assert.equal(progressToFrameIndex(-0.2, 10), 0);
    assert.equal(progressToFrameIndex(1.5, 10), 9);
  });
  test('프레임이 0~1장이면 항상 0', () => {
    assert.equal(progressToFrameIndex(0.7, 0), 0);
    assert.equal(progressToFrameIndex(0.7, 1), 0);
  });
});

describe('frameFileName', () => {
  test('0 부터 시작하는 인덱스를 1 부터 시작하는 4자리 파일 이름으로', () => {
    assert.equal(frameFileName(0), 'f_0001.jpg');
    assert.equal(frameFileName(41), 'f_0042.jpg');
  });
});

describe('coverRect', () => {
  test('비율이 같으면 꽉 채운다', () => {
    assert.deepEqual(coverRect(1600, 900, 800, 450), { x: 0, y: 0, width: 800, height: 450 });
  });
  test('세로로 긴 화면(모바일)에서는 높이에 맞추고 좌우를 자른다', () => {
    const r = coverRect(1600, 900, 400, 900);
    assert.equal(r.height, 900);
    assert.equal(r.width, 1600);
    assert.equal(r.x, -600); // 가운데 정렬 → 양쪽으로 600px 씩 잘림
    assert.equal(r.y, 0);
  });
  test('가로로 긴 화면에서는 너비에 맞추고 위아래를 자른다', () => {
    const r = coverRect(1600, 900, 3200, 900);
    assert.equal(r.width, 3200);
    assert.equal(r.height, 1800);
    assert.equal(r.y, -450);
  });
});
