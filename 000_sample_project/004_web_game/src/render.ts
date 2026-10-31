// Canvas 렌더링 모듈
// 게임 상태(GameState)를 받아 화면에 그리기만 한다. 상태를 바꾸지 않는다.
import { WORLD_HEIGHT, WORLD_WIDTH, getDifficulty, type GameState, type ItemKind } from './game';

const ITEM_EMOJI: Record<ItemKind, string> = {
  document: '📄',
  coffee: '☕',
  bomb: '💣',
};

/** 사무실 배경(벽, 창문, 바닥) */
function drawBackground(ctx: CanvasRenderingContext2D): void {
  ctx.fillStyle = '#2b3150';
  ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);

  // 밤하늘이 보이는 창문 세 개
  for (let i = 0; i < 3; i++) {
    const x = 40 + i * 150;
    ctx.fillStyle = '#121633';
    ctx.fillRect(x, 70, 100, 120);
    ctx.fillStyle = '#f5e27a';
    ctx.beginPath();
    ctx.arc(x + 75, 100, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#4a5280';
    ctx.lineWidth = 4;
    ctx.strokeRect(x, 70, 100, 120);
  }

  // 바닥
  ctx.fillStyle = '#3d4466';
  ctx.fillRect(0, WORLD_HEIGHT - 16, WORLD_WIDTH, 16);
}

/** 플레이어(직원). 커피 효과 중에는 주황색으로 빛난다. */
function drawPlayer(ctx: CanvasRenderingContext2D, state: GameState): void {
  const { x, y, width, height } = state.player;
  ctx.fillStyle = state.boostTime > 0 ? '#ff9f43' : '#54a0ff';
  ctx.fillRect(x, y + height * 0.45, width, height * 0.55); // 몸통
  ctx.fillStyle = '#ffeaa7';
  ctx.beginPath();
  ctx.arc(x + width / 2, y + height * 0.25, height * 0.25, 0, Math.PI * 2); // 머리
  ctx.fill();
  ctx.fillStyle = '#222';
  ctx.fillRect(x + width / 2 - 6, y + height * 0.2, 3, 3); // 눈
  ctx.fillRect(x + width / 2 + 3, y + height * 0.2, 3, 3);
  ctx.fillStyle = '#ee5253';
  ctx.fillRect(x + width / 2 - 2, y + height * 0.45, 4, height * 0.3); // 넥타이
}

function drawItems(ctx: CanvasRenderingContext2D, state: GameState): void {
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (const item of state.items) {
    ctx.font = `${item.width - 4}px sans-serif`;
    ctx.fillText(ITEM_EMOJI[item.kind], item.x + item.width / 2, item.y + item.height / 2);
  }
}

/** 상단 점수판: 점수, 최고 점수, 생명, 레벨 */
function drawHud(ctx: CanvasRenderingContext2D, state: GameState): void {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
  ctx.fillRect(0, 0, WORLD_WIDTH, 44);
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 18px sans-serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.fillText(`점수 ${state.score}`, 12, 22);
  ctx.textAlign = 'center';
  ctx.fillText(`최고 ${state.highScore} · Lv.${getDifficulty(state.elapsed).level}`, WORLD_WIDTH / 2, 22);
  ctx.textAlign = 'right';
  ctx.fillText('❤️'.repeat(state.lives) + '🤍'.repeat(3 - state.lives), WORLD_WIDTH - 12, 22);
}

/** 반투명 막 위에 제목과 안내 문구를 그린다. */
function drawOverlay(ctx: CanvasRenderingContext2D, title: string, lines: string[]): void {
  ctx.fillStyle = 'rgba(10, 12, 30, 0.75)';
  ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#feca57';
  ctx.font = 'bold 40px sans-serif';
  ctx.fillText(title, WORLD_WIDTH / 2, WORLD_HEIGHT / 2 - 90);
  ctx.fillStyle = '#fff';
  ctx.font = '18px sans-serif';
  lines.forEach((line, i) => ctx.fillText(line, WORLD_WIDTH / 2, WORLD_HEIGHT / 2 - 20 + i * 32));
}

/** 현재 상태 전체를 그린다. */
export function render(ctx: CanvasRenderingContext2D, state: GameState): void {
  drawBackground(ctx);
  drawItems(ctx, state);
  drawPlayer(ctx, state);
  drawHud(ctx, state);

  if (state.phase === 'ready') {
    drawOverlay(ctx, '야근 탈출', [
      '📄 결재 서류를 받으면 +10점',
      '☕ 커피를 받으면 잠시 이동 속도 UP',
      '💣 야근 폭탄에 맞으면 생명 -1',
      '←/→ 또는 화면 좌/우 탭으로 이동',
      '스페이스 또는 탭해서 시작',
    ]);
  } else if (state.phase === 'paused') {
    drawOverlay(ctx, '일시정지', ['스페이스를 누르거나 탭하면 계속']);
  } else if (state.phase === 'over') {
    drawOverlay(ctx, '야근 확정...', [
      `이번 점수: ${state.score}점`,
      `최고 점수: ${state.highScore}점`,
      '스페이스 또는 탭해서 다시 도전',
    ]);
  }
}
