import { beforeEach, describe, expect, it } from 'vitest';
import {
  ToolError,
  executeTool,
  getEmployee,
  getExpensePolicy,
  getLeaveBalance,
  getSubmittedExpenses,
  resetSubmittedExpenses,
  submitExpense,
  toolDefinitions,
} from '../src/tools.js';
import { DEFAULT_MODEL, getModel, hasApiKey } from '../src/config.js';

describe('get_employee', () => {
  it('사번으로 사원을 찾는다', () => {
    expect(getEmployee({ employee_id: 'E002' })).toMatchObject({ name: '이서연', department: '재무팀' });
  });

  it('이름으로 사원을 찾는다', () => {
    expect(getEmployee({ name: '박지호' })).toMatchObject({ id: 'E003' });
  });

  it('없는 사원이면 ToolError', () => {
    expect(() => getEmployee({ employee_id: 'E999' })).toThrow(ToolError);
  });

  it('사번과 이름이 모두 없으면 ToolError', () => {
    expect(() => getEmployee({})).toThrow(/employee_id/);
  });
});

describe('get_leave_balance', () => {
  it('잔여 연차 = 총 연차 - 사용 연차', () => {
    expect(getLeaveBalance({ employee_id: 'E001' })).toEqual({
      employee_id: 'E001',
      name: '김민준',
      total_days: 15,
      used_days: 4.5,
      remaining_days: 10.5,
    });
  });

  it('employee_id 가 없으면 ToolError', () => {
    expect(() => getLeaveBalance({})).toThrow(ToolError);
  });
});

describe('get_expense_policy', () => {
  it('category 를 생략하면 전체 정책을 돌려준다', () => {
    const policies = getExpensePolicy({});
    expect(Array.isArray(policies)).toBe(true);
    expect(policies).toHaveLength(4);
  });

  it('특정 항목의 한도를 돌려준다', () => {
    expect(getExpensePolicy({ category: 'taxi' })).toMatchObject({ limitPerClaim: 50000 });
  });

  it('알 수 없는 항목이면 ToolError', () => {
    expect(() => getExpensePolicy({ category: 'golf' })).toThrow(/알 수 없는 경비 항목/);
  });
});

describe('submit_expense', () => {
  beforeEach(() => resetSubmittedExpenses());

  const valid = { employee_id: 'E001', category: 'meal', amount: 25000, description: '야근 식대' };

  it('한도 이내 금액은 승인 대기 상태로 등록된다', () => {
    const expense = submitExpense(valid);
    expect(expense).toMatchObject({ expenseId: 'EXP-0001', status: '승인 대기', amount: 25000 });
    expect(getSubmittedExpenses()).toHaveLength(1);
  });

  it('한도와 같은 금액은 허용된다', () => {
    expect(() => submitExpense({ ...valid, amount: 30000 })).not.toThrow();
  });

  it('한도를 초과하면 ToolError 이고 등록되지 않는다', () => {
    expect(() => submitExpense({ ...valid, amount: 30001 })).toThrow(/한도/);
    expect(getSubmittedExpenses()).toHaveLength(0);
  });

  it.each([0, -1000, 1234.5, '25000'])('잘못된 금액(%s)은 거절한다', (amount) => {
    expect(() => submitExpense({ ...valid, amount })).toThrow(/amount/);
  });

  it('없는 사원이나 항목은 거절한다', () => {
    expect(() => submitExpense({ ...valid, employee_id: 'E999' })).toThrow(ToolError);
    expect(() => submitExpense({ ...valid, category: 'golf' })).toThrow(ToolError);
  });

  it('신청 번호는 순서대로 증가한다', () => {
    submitExpense(valid);
    expect(submitExpense(valid).expenseId).toBe('EXP-0002');
  });
});

describe('executeTool / toolDefinitions', () => {
  it('정의된 도구 이름과 실행 가능한 도구가 일치한다', () => {
    for (const tool of toolDefinitions) {
      expect(() => executeTool(tool.name, tool.name === 'get_expense_policy' ? {} : { employee_id: 'E001' })).not.toThrow(
        /알 수 없는 도구/,
      );
    }
  });

  it('결과를 JSON 문자열로 돌려준다', () => {
    expect(JSON.parse(executeTool('get_employee', { employee_id: 'E001' }))).toMatchObject({ name: '김민준' });
  });

  it('입력이 객체가 아니면 ToolError', () => {
    expect(() => executeTool('get_employee', 'E001')).toThrow(/JSON 객체/);
  });
});

describe('config', () => {
  it('ANTHROPIC_MODEL 이 없으면 기본 모델을 쓴다', () => {
    expect(getModel({})).toBe(DEFAULT_MODEL);
    expect(DEFAULT_MODEL).toBe('claude-opus-5-5');
  });

  it('ANTHROPIC_MODEL 이 있으면 그 값을 쓴다', () => {
    expect(getModel({ ANTHROPIC_MODEL: 'claude-haiku-5-5' })).toBe('claude-haiku-5-5');
  });

  it('API 키 유무를 판별한다', () => {
    expect(hasApiKey({})).toBe(false);
    expect(hasApiKey({ ANTHROPIC_API_KEY: '  ' })).toBe(false);
    expect(hasApiKey({ ANTHROPIC_API_KEY: 'dummy' })).toBe(true);
  });
});
