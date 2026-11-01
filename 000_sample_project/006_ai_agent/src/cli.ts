import { existsSync } from 'node:fs';
import Anthropic from '@anthropic-ai/sdk';
import { IncompleteAnswerError, MaxIterationsError, runAgent } from './agent.js';
import { getModel, hasApiKey } from './config.js';

async function main(): Promise<void> {
  // .env 파일이 있으면 환경변수로 읽어 들인다(Node 22 내장 기능).
  if (existsSync('.env')) {
    process.loadEnvFile('.env');
  }

  const question = process.argv.slice(2).join(' ').trim();
  if (!question) {
    console.log('사용법: npm start -- "김민준 님의 잔여 연차를 알려줘"');
    process.exitCode = 1;
    return;
  }

  if (!hasApiKey()) {
    console.log('ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.');
    console.log('.env.example 을 참고해 키를 환경변수로 설정한 뒤 다시 실행하세요.');
    console.log('예) export ANTHROPIC_API_KEY=... && npm start -- "질문"');
    process.exitCode = 1;
    return;
  }

  // 클라이언트는 ANTHROPIC_API_KEY 환경변수를 자동으로 읽는다.
  const client = new Anthropic();
  const model = getModel();
  console.log(`[모델] ${model}`);
  console.log(`[질문] ${question}\n`);

  try {
    const result = await runAgent({
      client,
      question,
      model,
      onToolCall: (name, input, toolResult) => {
        const mark = toolResult.is_error ? '실패' : '성공';
        console.log(`[도구 ${mark}] ${name} ${JSON.stringify(input)}`);
      },
    });
    console.log(`\n[답변]\n${result.answer}`);
    console.log(`\n(모델 호출 ${result.iterations}회, 종료 사유: ${result.stopReason})`);
  } catch (error) {
    if (error instanceof MaxIterationsError || error instanceof IncompleteAnswerError) {
      console.error(error.message);
    } else if (error instanceof Anthropic.APIError) {
      console.error(`API 오류(${error.status}): ${error.message}`);
    } else {
      console.error('예상하지 못한 오류:', error);
    }
    process.exitCode = 1;
  }
}

void main();
