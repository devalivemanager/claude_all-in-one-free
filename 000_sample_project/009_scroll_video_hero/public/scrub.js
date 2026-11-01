// 스크롤 스크러빙에 필요한 계산만 모아 둔 순수 함수 모듈입니다.
// DOM 에 의존하지 않으므로 브라우저와 Node(단위 테스트) 양쪽에서 그대로 import 할 수 있습니다.

/** 값을 [min, max] 범위로 자릅니다. NaN 은 min 으로 취급합니다. */
export function clamp(value, min, max) {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, value));
}

/**
 * 히어로 섹션의 위치 정보로 스크롤 진행률(0~1)을 계산합니다.
 * - sectionTop: getBoundingClientRect().top (화면 위쪽 기준, 스크롤하면 음수가 됨)
 * - sectionHeight: 섹션 전체 높이 (예: 400vh)
 * - viewportHeight: 화면 높이
 * sticky 영역이 화면에 붙어 있는 구간(섹션 높이 - 화면 높이)을 0~1 로 환산합니다.
 */
export function progressFromRect(sectionTop, sectionHeight, viewportHeight) {
  const scrollable = sectionHeight - viewportHeight;
  if (scrollable <= 0) return 0;
  return clamp(-sectionTop / scrollable, 0, 1);
}

/**
 * 진행률(0~1)을 프레임 인덱스(0 ~ frameCount-1)로 바꿉니다.
 * 진행률 0 은 첫 프레임, 1 은 마지막 프레임이 되도록 반올림합니다.
 */
export function progressToFrameIndex(progress, frameCount) {
  if (!Number.isFinite(frameCount) || frameCount <= 1) return 0;
  const p = clamp(progress, 0, 1);
  return Math.round(p * (frameCount - 1));
}

/** 0부터 시작하는 인덱스를 추출 스크립트가 만든 파일 이름(f_0001.jpg …)으로 바꿉니다. */
export function frameFileName(index) {
  return `f_${String(index + 1).padStart(4, '0')}.jpg`;
}

/**
 * CSS 의 object-fit: cover 처럼, 원본 비율을 유지하면서 대상 영역을 빈틈없이 채우는
 * 그리기 사각형을 계산합니다. 넘치는 부분은 캔버스 밖으로 잘려 나갑니다.
 */
export function coverRect(srcWidth, srcHeight, dstWidth, dstHeight) {
  if (srcWidth <= 0 || srcHeight <= 0) return { x: 0, y: 0, width: dstWidth, height: dstHeight };
  const scale = Math.max(dstWidth / srcWidth, dstHeight / srcHeight);
  const width = srcWidth * scale;
  const height = srcHeight * scale;
  return { x: (dstWidth - width) / 2, y: (dstHeight - height) / 2, width, height };
}
