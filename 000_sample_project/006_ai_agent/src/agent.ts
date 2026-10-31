import type {
  Message,
  MessageCreateParamsNonStreaming,
  MessageParam,
  Tool,
  ToolResultBlockParam,
} from '@anthropic-ai/sdk/resources/messages';
import { executeTool as defaultExecuteTool, toolDefinitions } from './tools.js';

// 에이전트가 필요로 하는 최소한의 클라이언트 모양.
// 실제 Anthropic 클라이언트도, 테스트용 가짜 클라이언트도 이 모양만 맞추면 된다.
export interface MessagesClient {
  messages: {
    create(params: MessageCreateParamsNonStreaming): Promise<Message>;
  };
}

export const SYSTEM_PROMPT = [
  '당신은 사내 HR/회계 도우미입니다.',
  '사원 정보, 잔여 연차, 경비 정책 조회와 경비 신청 등록을 도구로 처리합니다.',
  '추측하지 말고 반드시 도구로 확인한 사실만 답하세요.',
  '도구가 오류를 돌려주면 그 이유를 사용자에게 알기 쉽게 설명하세요.',
  '답변은 한국어로 간결하게 작성하세요.',
].join('\n');

export interface RunAgentOptions {
  client: MessagesClient;
  question: string;
  model: string;
  // 모델 호출 최대 횟수. 도구 호출이 끝없이 반복되는 것을 막는다.
  maxIterations?: number;
  maxTokens?: number;
  tools?: Tool[];
  executeTool?: (name: string, input: unknown) => string | Promise<string>;
  // 진행 상황을 보고 싶을 때(CLI 로그 등) 사용하는 선택적 콜백
  onToolCall?: (name: string, input: unknown, result: ToolResultBlockParam) => void;
}

export interface AgentResult {
  answer: string;
  iterations: number;
  stopReason: Message['stop_reason'];
  messages: MessageParam[];
}

export class MaxIterationsError extends Error {
  constructor(public readonly maxIterations: number) {
    super(`최대 반복 횟수(${maxIterations}회)를 초과했습니다. 질문을 더 구체적으로 나눠 보세요.`);
    this.name = 'MaxIterationsError';
  }
}

// 응답의 text 블록만 모아 최종 답변 문자열로 만든다.
function extractText(message: Message): string {
  return message.content
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('\n')
    .trim();
}

// 도구 하나를 실행하고 tool_result 블록으로 감싼다. 실패하면 is_error: true 로 돌려준다.
async function runTool(
  execute: NonNullable<RunAgentOptions['executeTool']>,
  toolUseId: string,
  name: string,
  input: unknown,
): Promise<ToolResultBlockParam> {
  try {
    const content = await execute(name, input);
    return { type: 'tool_result', tool_use_id: toolUseId, content };
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    return { type: 'tool_result', tool_use_id: toolUseId, content: `오류: ${reason}`, is_error: true };
  }
}

export async function runAgent(options: RunAgentOptions): Promise<AgentResult> {
  const {
    client,
    question,
    model,
    maxIterations = 8,
    maxTokens = 1024,
    tools = toolDefinitions,
    executeTool = defaultExecuteTool,
    onToolCall,
  } = options;

  const messages: MessageParam[] = [{ role: 'user', content: question }];

  for (let iteration = 1; iteration <= maxIterations; iteration++) {
    // 1) 지금까지의 대화와 도구 목록을 보내 모델을 호출한다.
    const response = await client.messages.create({
      model,
      max_tokens: maxTokens,
      system: SYSTEM_PROMPT,
      tools,
      messages,
    });

    // 2) 모델의 응답(도구 호출 포함)을 대화 기록에 그대로 남긴다.
    messages.push({ role: 'assistant', content: response.content });

    // 3) 도구 호출이 아니면 최종 답변으로 보고 종료한다.
    if (response.stop_reason !== 'tool_use') {
      return {
        answer: extractText(response),
        iterations: iteration,
        stopReason: response.stop_reason,
        messages,
      };
    }

    // 4) 요청된 도구를 모두 실행하고, 결과를 하나의 user 메시지로 묶어 돌려준다.
    const toolResults: ToolResultBlockParam[] = [];
    for (const block of response.content) {
      if (block.type !== 'tool_use') continue;
      const result = await runTool(executeTool, block.id, block.name, block.input);
      onToolCall?.(block.name, block.input, result);
      toolResults.push(result);
    }
    messages.push({ role: 'user', content: toolResults });
  }

  throw new MaxIterationsError(maxIterations);
}
