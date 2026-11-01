// 저작권 걱정 없는 데모 영상을 ffmpeg 만으로 만듭니다.
// 격자 모양의 점(입자)들이 점점 가운데로 모이고 빛이 생겨나는 6초짜리 애니메이션입니다.
// 사용: node scripts/make-demo-video.mjs [출력 파일]   (기본값: demo.mp4)
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const PROJECT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DURATION = 6; // 초
const SIZE = '960x540';

// 시간이 지날수록 커지는 배율. 좌표에 곱하면 격자 간격이 화면상에서 좁아져 점들이 중심으로 모입니다.
const S = `(1+3*T/${DURATION})`;
// 중심에서의 거리
const DIST = 'hypot(X-W/2,Y-H/2)';
// 격자 점: 확대된 좌표계에서 40px 간격, 반지름 3*S (화면에서는 늘 약 3px)
const DOT = `lt(hypot(mod((X-W/2)*${S}+20,40)-20,mod((Y-H/2)*${S}+20,40)-20),3*${S})`;
// 점이 보이는 원형 영역: 반지름이 560px → 160px 로 줄어듦
const DISC = `lt(${DIST},560-400*T/${DURATION})`;
// 시간이 지날수록 밝아지는 가운데 빛
const GLOW = `200*exp(-${DIST}/50)*T/${DURATION}`;

export function buildFilter() {
  return [
    `nullsrc=s=${SIZE}:r=30:d=${DURATION}`,
    'format=gray',
    `geq=lum='min(255,230*${DOT}*${DISC}+${GLOW})'`,
    'format=rgb24',
    'colorchannelmixer=rr=0.45:gg=0.75:bb=1.0', // 푸른 빛으로 물들이기
    'hue=h=t*25', // 시간에 따라 색상 회전
  ].join(',');
}

function main() {
  const output = path.resolve(process.argv[2] ?? path.join(PROJECT_DIR, 'demo.mp4'));
  console.log('데모 영상 생성 중… (수십 초 걸릴 수 있습니다)');
  const result = spawnSync(
    'ffmpeg',
    ['-v', 'error', '-y', '-f', 'lavfi', '-i', buildFilter(), '-pix_fmt', 'yuv420p', output],
    { stdio: 'inherit' },
  );
  if (result.error) {
    console.error('ffmpeg 를 찾을 수 없습니다. 먼저 설치해 주세요.');
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
  console.log(`데모 영상 생성 완료 → ${output}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
