// 프레임 추출 스크립트 테스트: ffmpeg 로 짧은 영상을 만들어 실제로 추출해 봅니다.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { hasFfmpeg, parseArgs } from '../scripts/extract-frames.mjs';
import { makeTestVideo } from './helpers.mjs';

const SCRIPT = fileURLToPath(new URL('../scripts/extract-frames.mjs', import.meta.url));

function runScript(args, env = process.env) {
  return spawnSync(process.execPath, [SCRIPT, ...args], { encoding: 'utf8', env });
}

describe('parseArgs', () => {
  test('기본값은 fps 15, 너비 1280', () => {
    const options = parseArgs(['a.mp4']);
    assert.equal(options.input, 'a.mp4');
    assert.equal(options.fps, 15);
    assert.equal(options.width, 1280);
    assert.ok(options.out.endsWith(path.join('public', 'frames')));
  });
  test('옵션을 읽는다', () => {
    const options = parseArgs(['--fps', '10', 'b.mov', '--width', '640']);
    assert.deepEqual([options.input, options.fps, options.width], ['b.mov', 10, 640]);
  });
  test('잘못된 입력은 에러', () => {
    assert.throws(() => parseArgs([]), /영상 파일/);
    assert.throws(() => parseArgs(['a.mp4', '--fps', '0']), /fps/);
    assert.throws(() => parseArgs(['a.mp4', '--width', '641']), /width/);
    assert.throws(() => parseArgs(['a.mp4', '--speed', '2']), /알 수 없는 옵션/);
  });
});

describe('ffmpeg 가 없을 때', () => {
  test('안내 메시지를 출력하고 종료 코드 1 로 끝난다', () => {
    // PATH 를 비워 ffmpeg 를 못 찾게 만듭니다.
    const result = runScript(['whatever.mp4'], { ...process.env, PATH: '' });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /ffmpeg 를 찾을 수 없습니다/);
  });
});

describe('실제 추출', { skip: !hasFfmpeg() && 'ffmpeg 가 설치되어 있지 않아 건너뜀' }, () => {
  let dir;
  let video;
  let out;

  before(() => {
    dir = mkdtempSync(path.join(tmpdir(), 'extract-test-'));
    video = path.join(dir, 'input.mp4');
    out = path.join(dir, 'frames');
    makeTestVideo(video, { seconds: 2, size: '320x180', rate: 20 }); // 2초, 16:9
  });
  after(() => rmSync(dir, { recursive: true, force: true }));

  test('fps 와 너비에 맞춰 프레임과 manifest.json 을 만든다', () => {
    const result = runScript([video, '--fps', '5', '--width', '160', '--out', out]);
    assert.equal(result.status, 0, result.stderr);

    const manifest = JSON.parse(readFileSync(path.join(out, 'manifest.json'), 'utf8'));
    assert.deepEqual(manifest, { count: 10, width: 160, height: 90, fps: 5 }); // 2초 × 5fps

    const frames = readdirSync(out).filter((name) => name.endsWith('.jpg')).sort();
    assert.equal(frames.length, manifest.count);
    assert.equal(frames[0], 'f_0001.jpg');
    assert.equal(frames.at(-1), 'f_0010.jpg');
  });

  test('다시 실행하면 이전 프레임을 지우고 새로 만든다', () => {
    writeFileSync(path.join(out, 'f_0099.jpg'), 'old'); // 이전 실행에서 남은 파일이라고 가정
    const result = runScript([video, '--fps', '2', '--width', '64', '--out', out]);
    assert.equal(result.status, 0, result.stderr);

    const manifest = JSON.parse(readFileSync(path.join(out, 'manifest.json'), 'utf8'));
    assert.deepEqual(manifest, { count: 4, width: 64, height: 36, fps: 2 });
    assert.equal(existsSync(path.join(out, 'f_0099.jpg')), false);
  });

  test('없는 영상 파일이면 에러로 끝난다', () => {
    const result = runScript([path.join(dir, 'nope.mp4'), '--out', out]);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /영상 파일이 없습니다/);
  });
});
