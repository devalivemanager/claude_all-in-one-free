import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ContentBlock, Message, MessageParam, StopReason } from '@anthropic-ai/sdk/resources/messages';
import { MaxIterationsError, runAgent, type MessagesClient } from '../src/agent.js';
import { resetSubmittedExpenses } from '../src/tools.js';

// 테스트에 필요한 필드만 채운 가짜 Message 를 만든다.
function fakeMessage(content: unknown[], stopReason: StopReason): Message {
  return {
    id: 'msg_test',
    type: 'message',
    role: 'assistant',
    model: 'claude-opus-5-5',
    content: content as ContentBlock[],
    stop_reason: stopReason,
    stop_sequence: null,
  } as unknown as Message;
}

const text = (value: string) => ({ type: 'text', text: value, citations: null });
const toolUse = (id: string, name: string, input: unknown) => ({ type: 'tool_use', id, name, input });

// 미리 정해 둔 응답을 순서대로 돌려주는 가짜 클라이언트
function fakeClient(responses: Message[]) {
  const create = vi.fn();
  for (const response of responses) create.mockResolvedValueOnce(response);
  const client: MessagesClient = { messages: { create } };
  return { client, create };
}

// 대화 기록에서 마지막 tool_result 묶음(user 메시지)을 꺼낸다.
// mock 은 messages 배열의 참조를 기억하므로, 최종 답변까지 추가된 상태에서 찾아야 한다.
function lastToolResults(messages: MessageParam[]) {
  const found = messages.findLast(
    (m) => m.role === 'user' && Array.isArray(m.content) && m.content.some((b) => b.type === 'tool_result'),
  );
  return (found?.content ?? []) as unknown as Array<Record<string, unknown>>;
}

describe('runAgent 에이전트 루프', () => {
  beforeEach(() => resetSubmittedExpenses());

  it('도구 호출 → tool_result 전달 → 최종 답변 순서로 동작한다', async () => {
    const { client, create } = fakeClient([
      fakeMessage([text('연차를 조회할게요.'), toolUse('tu_1', 'get_leave_balance', { employee_id: 'E001' })], 'tool_use'),
      fakeMessage([text('김민준 님의 잔여 연차는 10.5일입니다.')], 'end_turn'),
    ]);

    const result = await runAgent({ client, question: '김민준 잔여 연차?', model: 'test-model' });

    expect(result.answer).toBe('김민준 님의 잔여 연차는 10.5일입니다.');
    expect(result.iterations).toBe(2);
    expect(result.stopReason).toBe('end_turn');
    expect(create).toHaveBeenCalledTimes(2);

    // 첫 호출에는 모델 ID, 시스템 프롬프트, 도구 목록이 함께 전달된다.
    const firstParams = create.mock.calls[0][0];
    expect(firstParams.model).toBe('test-model');
    expect(firstParams.system).toContain('HR/회계 도우미');
    expect(firstParams.tools.map((t: { name: string }) => t.name)).toEqual([
      'get_employee',
      'get_leave_balance',
      'get_expense_policy',
      'submit_expense',
    ]);

    // 두 번째 호출에는 user → assistant(tool_use) → user(tool_result) 대화가 담긴다.
    const secondMessages: MessageParam[] = create.mock.calls[1][0].messages;
    expect(secondMessages.map((m) => m.role).slice(0, 3)).toEqual(['user', 'assistant', 'user']);
    const toolResult = (secondMessages[2].content as unknown as Array<Record<string, unknown>>)[0];
    expect(toolResult).toMatchObject({ type: 'tool_result', tool_use_id: 'tu_1' });
    expect(toolResult.is_error).toBeUndefined();
    expect(JSON.parse(toolResult.content as string)).toMatchObject({ remaining_days: 10.5 });
  });

  it('한 응답에 도구 호출이 여러 개면 모두 실행해 한 메시지로 돌려준다', async () => {
    const { client, create } = fakeClient([
      fakeMessage(
        [
          toolUse('tu_a', 'get_employee', { name: '이서연' }),
          toolUse('tu_b', 'get_expense_policy', { category: 'meal' }),
        ],
        'tool_use',
      ),
      fakeMessage([text('완료')], 'end_turn'),
    ]);

    await runAgent({ client, question: '질문', model: 'm' });

    const results = lastToolResults(create.mock.calls[1][0].messages);
    expect(results.map((r) => r.tool_use_id)).toEqual(['tu_a', 'tu_b']);
    expect(results.every((r) => r.is_error === undefined)).toBe(true);
  });

  it('도구가 실패하면 is_error: true 인 tool_result 로 모델에 알린다', async () => {
    const { client, create } = fakeClient([
      fakeMessage(
        [toolUse('tu_1', 'submit_expense', { employee_id: 'E001', category: 'meal', amount: 99000, description: '회식' })],
        'tool_use',
      ),
      fakeMessage([text('식대 한도를 초과해 등록하지 못했습니다.')], 'end_turn'),
    ]);
    const onToolCall = vi.fn();

    const result = await runAgent({ client, question: '식대 99000원 신청', model: 'm', onToolCall });

    const [toolResult] = lastToolResults(create.mock.calls[1][0].messages);
    expect(toolResult.is_error).toBe(true);
    expect(toolResult.content).toContain('한도');
    expect(onToolCall).toHaveBeenCalledOnce();
    expect(result.answer).toContain('초과');
  });

  it('존재하지 않는 도구를 호출해도 루프가 멈추지 않고 is_error 로 전달한다', async () => {
    const { client, create } = fakeClient([
      fakeMessage([toolUse('tu_1', 'delete_database', {})], 'tool_use'),
      fakeMessage([text('해당 기능은 없습니다.')], 'end_turn'),
    ]);

    const result = await runAgent({ client, question: '질문', model: 'm' });

    const [toolResult] = lastToolResults(create.mock.calls[1][0].messages);
    expect(toolResult).toMatchObject({ is_error: true });
    expect(toolResult.content).toContain('알 수 없는 도구');
    expect(result.answer).toBe('해당 기능은 없습니다.');
  });

  it('주입한 executeTool 이 예외를 던져도 is_error 로 감싼다', async () => {
    const { client, create } = fakeClient([
      fakeMessage([toolUse('tu_1', 'get_employee', { employee_id: 'E001' })], 'tool_use'),
      fakeMessage([text('시스템 오류가 있었습니다.')], 'end_turn'),
    ]);
    const executeTool = vi.fn(async () => {
      throw new Error('HR 시스템 연결 실패');
    });

    await runAgent({ client, question: '질문', model: 'm', executeTool });

    const [toolResult] = lastToolResults(create.mock.calls[1][0].messages);
    expect(toolResult).toMatchObject({ is_error: true, content: '오류: HR 시스템 연결 실패' });
  });

  it('최대 반복 횟수를 넘으면 MaxIterationsError 를 던진다', async () => {
    // 모델이 계속 도구만 호출하는 상황을 흉내 낸다.
    const create = vi.fn(async () =>
      fakeMessage([toolUse('tu_loop', 'get_expense_policy', {})], 'tool_use'),
    );
    const client: MessagesClient = { messages: { create } };

    await expect(runAgent({ client, question: '질문', model: 'm', maxIterations: 3 })).rejects.toBeInstanceOf(
      MaxIterationsError,
    );
    expect(create).toHaveBeenCalledTimes(3);
  });

  it('도구 호출 없이 바로 답하면 한 번만 호출하고 끝난다', async () => {
    const { client, create } = fakeClient([fakeMessage([text('안녕하세요!')], 'end_turn')]);

    const result = await runAgent({ client, question: '안녕', model: 'm' });

    expect(result).toMatchObject({ answer: '안녕하세요!', iterations: 1 });
    expect(create).toHaveBeenCalledOnce();
  });
});
