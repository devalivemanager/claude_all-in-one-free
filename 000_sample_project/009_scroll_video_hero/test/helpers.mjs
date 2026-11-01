// 테스트에서 함께 쓰는 도우미 함수
import { spawnSync } from 'node:child_process';

/** ffmpeg 의 testsrc2 로 짧은 테스트 영상을 만듭니다. */
export function makeTestVideo(file, { seconds = 1, size = '320x180', rate = 20 } = {}) {
  const result = spawnSync(
    'ffmpeg',
    ['-v', 'error', '-y', '-f', 'lavfi', '-i', `testsrc2=s=${size}:r=${rate}:d=${seconds}`, '-pix_fmt', 'yuv420p', file],
    { encoding: 'utf8' },
  );
  if (result.status !== 0) throw new Error(`테스트 영상 생성 실패: ${result.stderr}`);
}
