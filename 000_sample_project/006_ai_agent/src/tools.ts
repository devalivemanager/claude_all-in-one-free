import type { Tool } from '@anthropic-ai/sdk/resources/messages';
import { employees, expensePolicies, leaveBalances } from './data.js';

// 도구 실행 중 발생한 "예상된" 오류. 에이전트 루프에서 is_error 로 모델에 전달된다.
export class ToolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ToolError';
  }
}

export interface SubmittedExpense {
  expenseId: string;
  employeeId: string;
  category: string;
  amount: number;
  description: string;
  status: '승인 대기';
}

// 등록된 경비 신청 내역(인메모리). 프로세스가 끝나면 사라진다.
const submittedExpenses: SubmittedExpense[] = [];

export function getSubmittedExpenses(): readonly SubmittedExpense[] {
  return submittedExpenses;
}

// 테스트 간 상태를 초기화하기 위한 함수
export function resetSubmittedExpenses(): void {
  submittedExpenses.length = 0;
}

// ---- 입력값 검증 도우미 ----

function asRecord(input: unknown): Record<string, unknown> {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    throw new ToolError('도구 입력은 JSON 객체여야 합니다.');
  }
  return input as Record<string, unknown>;
}

function requireString(input: Record<string, unknown>, key: string): string {
  const value = input[key];
  if (typeof value !== 'string' || value.trim() === '') {
    throw new ToolError(`'${key}' 값(문자열)이 필요합니다.`);
  }
  return value.trim();
}

function findEmployeeOrThrow(employeeId: string) {
  const employee = employees.find((e) => e.id === employeeId);
  if (!employee) {
    throw new ToolError(`사번 '${employeeId}' 에 해당하는 사원이 없습니다.`);
  }
  return employee;
}

// ---- 도구 구현(순수 로직) ----

export function getEmployee(input: unknown) {
  const args = asRecord(input);
  const employeeId = typeof args.employee_id === 'string' ? args.employee_id.trim() : '';
  const name = typeof args.name === 'string' ? args.name.trim() : '';

  if (employeeId) {
    return findEmployeeOrThrow(employeeId);
  }
  if (name) {
    const employee = employees.find((e) => e.name === name);
    if (!employee) {
      throw new ToolError(`이름 '${name}' 에 해당하는 사원이 없습니다.`);
    }
    return employee;
  }
  throw new ToolError("'employee_id' 또는 'name' 중 하나는 반드시 입력해야 합니다.");
}

export function getLeaveBalance(input: unknown) {
  const employeeId = requireString(asRecord(input), 'employee_id');
  const employee = findEmployeeOrThrow(employeeId);
  const balance = leaveBalances.find((b) => b.employeeId === employeeId);
  if (!balance) {
    throw new ToolError(`'${employee.name}' 님의 연차 정보가 없습니다.`);
  }
  return {
    employee_id: employee.id,
    name: employee.name,
    total_days: balance.totalDays,
    used_days: balance.usedDays,
    remaining_days: balance.totalDays - balance.usedDays,
  };
}

export function getExpensePolicy(input: unknown) {
  const args = asRecord(input);
  // category 가 없으면 전체 정책 목록을 돌려준다.
  if (args.category === undefined) {
    return expensePolicies;
  }
  const category = requireString(args, 'category');
  const policy = expensePolicies.find((p) => p.category === category);
  if (!policy) {
    const known = expensePolicies.map((p) => p.category).join(', ');
    throw new ToolError(`알 수 없는 경비 항목 '${category}' 입니다. 가능한 값: ${known}`);
  }
  return policy;
}

export function submitExpense(input: unknown): SubmittedExpense {
  const args = asRecord(input);
  const employeeId = requireString(args, 'employee_id');
  const category = requireString(args, 'category');
  const description = requireString(args, 'description');
  const amount = args.amount;

  findEmployeeOrThrow(employeeId);

  const policy = expensePolicies.find((p) => p.category === category);
  if (!policy) {
    throw new ToolError(`알 수 없는 경비 항목 '${category}' 입니다.`);
  }
  if (typeof amount !== 'number' || !Number.isInteger(amount) || amount <= 0) {
    throw new ToolError("'amount' 는 0보다 큰 정수(원 단위)여야 합니다.");
  }
  // 핵심 업무 규칙: 정책 한도를 넘는 금액은 등록하지 않는다.
  if (amount > policy.limitPerClaim) {
    throw new ToolError(
      `${policy.label} 한도(${policy.limitPerClaim.toLocaleString('ko-KR')}원)를 초과했습니다. 신청 금액: ${amount.toLocaleString('ko-KR')}원`,
    );
  }

  const expense: SubmittedExpense = {
    expenseId: `EXP-${String(submittedExpenses.length + 1).padStart(4, '0')}`,
    employeeId,
    category,
    amount,
    description,
    status: '승인 대기',
  };
  submittedExpenses.push(expense);
  return expense;
}

// ---- 모델에 전달할 도구 정의(JSON Schema) ----

export const toolDefinitions: Tool[] = [
  {
    name: 'get_employee',
    description: '사번(employee_id) 또는 이름(name)으로 사원 정보(부서, 직급, 이메일)를 조회한다.',
    input_schema: {
      type: 'object',
      properties: {
        employee_id: { type: 'string', description: '사번. 예: E001' },
        name: { type: 'string', description: '사원 이름. 예: 김민준' },
      },
    },
  },
  {
    name: 'get_leave_balance',
    description: '사원의 연차 총일수, 사용일수, 잔여일수를 조회한다.',
    input_schema: {
      type: 'object',
      properties: {
        employee_id: { type: 'string', description: '사번. 예: E001' },
      },
      required: ['employee_id'],
    },
  },
  {
    name: 'get_expense_policy',
    description: '경비 항목별 정책(1건당 한도, 영수증 필요 여부)을 조회한다. category 를 생략하면 전체 목록을 돌려준다.',
    input_schema: {
      type: 'object',
      properties: {
        category: {
          type: 'string',
          enum: expensePolicies.map((p) => p.category),
          description: '경비 항목 코드',
        },
      },
    },
  },
  {
    name: 'submit_expense',
    description: '경비 신청을 등록한다. 정책 한도를 넘는 금액은 거절된다.',
    input_schema: {
      type: 'object',
      properties: {
        employee_id: { type: 'string', description: '사번. 예: E001' },
        category: { type: 'string', enum: expensePolicies.map((p) => p.category), description: '경비 항목 코드' },
        amount: { type: 'integer', description: '신청 금액(원)' },
        description: { type: 'string', description: '사용 내역 설명' },
      },
      required: ['employee_id', 'category', 'amount', 'description'],
    },
  },
];

const handlers: Record<string, (input: unknown) => unknown> = {
  get_employee: getEmployee,
  get_leave_balance: getLeaveBalance,
  get_expense_policy: getExpensePolicy,
  submit_expense: submitExpense,
};

// 도구 이름으로 실행하고 결과를 JSON 문자열로 돌려준다. 실패하면 예외를 던진다.
export function executeTool(name: string, input: unknown): string {
  const handler = handlers[name];
  if (!handler) {
    throw new ToolError(`알 수 없는 도구 '${name}' 입니다.`);
  }
  return JSON.stringify(handler(input));
}
