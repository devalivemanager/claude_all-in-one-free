// 영상 하나를 JPG 프레임들로 쪼개고 manifest.json 을 만듭니다.
// 사용: node scripts/extract-frames.mjs <영상> [--fps 15] [--width 1280] [--out public/frames]
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const PROJECT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FRAME_PATTERN = /^f_\d{4}\.jpg$/;

/** ffmpeg 가 PATH 에 있는지 확인합니다. */
export function hasFfmpeg() {
  const result = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' });
  return !result.error && result.status === 0;
}

/** 명령행 인자를 { input, fps, width, out } 으로 바꿉니다. */
export function parseArgs(argv) {
  const options = { input: null, fps: 15, width: 1280, out: path.join(PROJECT_DIR, 'public', 'frames') };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--fps') options.fps = Number(argv[++i]);
    else if (arg === '--width') options.width = Number(argv[++i]);
    else if (arg === '--out') options.out = path.resolve(argv[++i]);
    else if (!arg.startsWith('--')) options.input = arg;
    else throw new Error(`알 수 없는 옵션: ${arg}`);
  }
  if (!options.input) throw new Error('영상 파일 경로를 입력하세요.');
  if (!(options.fps > 0)) throw new Error('--fps 는 0보다 큰 숫자여야 합니다.');
  // yuv/jpg 인코딩은 짝수 크기가 안전하므로 너비를 짝수로 강제합니다.
  if (!(options.width >= 2) || options.width % 2 !== 0) throw new Error('--width 는 2 이상의 짝수여야 합니다.');
  return options;
}

/** ffprobe 로 이미지(또는 영상)의 가로·세로 크기를 읽습니다. */
function probeSize(file) {
  const result = spawnSync(
    'ffprobe',
    ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', file],
    { encoding: 'utf8' },
  );
  const [width, height] = result.stdout.trim().split('x').map(Number);
  return { width, height };
}

/** 프레임을 추출하고 manifest 객체를 돌려줍니다. */
export function extractFrames({ input, fps, width, out }) {
  if (!existsSync(input)) throw new Error(`영상 파일이 없습니다: ${input}`);

  // 이전에 만든 프레임이 섞이지 않도록 f_XXXX.jpg 와 manifest 를 먼저 지웁니다.
  mkdirSync(out, { recursive: true });
  for (const name of readdirSync(out)) {
    if (FRAME_PATTERN.test(name) || name === 'manifest.json') rmSync(path.join(out, name));
  }

  // fps 필터로 초당 프레임 수를 맞추고, scale 로 너비를 맞춥니다(-2: 비율 유지 + 짝수 높이).
  const result = spawnSync(
    'ffmpeg',
    ['-v', 'error', '-y', '-i', input, '-vf', `fps=${fps},scale=${width}:-2`, '-q:v', '4', path.join(out, 'f_%04d.jpg')],
    { encoding: 'utf8' },
  );
  if (result.status !== 0) throw new Error(`ffmpeg 실행 실패:\n${result.stderr}`);

  const frames = readdirSync(out).filter((name) => FRAME_PATTERN.test(name)).sort();
  if (frames.length === 0) throw new Error('추출된 프레임이 없습니다.');

  const size = probeSize(path.join(out, frames[0]));
  const manifest = { count: frames.length, width: size.width, height: size.height, fps };
  writeFileSync(path.join(out, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

function main() {
  if (!hasFfmpeg()) {
    console.error('ffmpeg 를 찾을 수 없습니다. 먼저 설치해 주세요.');
    console.error('  macOS: brew install ffmpeg / Ubuntu: sudo apt install ffmpeg / Windows: winget install ffmpeg');
    process.exit(1);
  }
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(err.message);
    console.error('사용법: node scripts/extract-frames.mjs <영상> [--fps 15] [--width 1280] [--out 폴더]');
    process.exit(1);
  }
  try {
    const manifest = extractFrames(options);
    console.log(`프레임 ${manifest.count}장 추출 완료 (${manifest.width}x${manifest.height}, ${manifest.fps}fps) → ${options.out}`);
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
