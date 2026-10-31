// 할 일 비즈니스 로직과 인메모리 저장소
import { NotFoundError, ValidationError } from "./errors.js";
import {
  PRIORITIES,
  STATUS_FILTERS,
  type CreateTodoInput,
  type Priority,
  type StatusFilter,
  type Todo,
  type TodoFilter,
  type TodoView,
  type UpdateTodoInput,
} from "./types.js";

const TITLE_MAX = 100;
const ASSIGNEE_MAX = 30;
const PRIORITY_RANK: Record<Priority, number> = { high: 0, medium: 1, low: 2 };

/** Date 객체를 로컬 기준 YYYY-MM-DD 문자열로 바꾼다 */
export function toDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** YYYY-MM-DD 형식이면서 실제로 존재하는 날짜인지 확인한다 (예: 2026-02-30 은 거부) */
export function isValidDateString(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [y, m, d] = value.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d;
}

/**
 * 입력값을 검증한다. partial=true 이면 수정(PATCH)용으로, 들어온 필드만 검사한다.
 * 문제가 있으면 ValidationError 를 던지고, 정리된(trim 된) 값을 돌려준다.
 */
function validateInput(raw: unknown, partial: boolean): UpdateTodoInput {
  const errors: string[] = [];
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    throw new ValidationError(["요청 본문은 JSON 객체여야 합니다."]);
  }
  const body = raw as Record<string, unknown>;
  const result: UpdateTodoInput = {};

  // 제목
  if (body.title !== undefined || !partial) {
    if (typeof body.title !== "string" || body.title.trim() === "") {
      errors.push("title(제목)은 비어 있지 않은 문자열이어야 합니다.");
    } else if (body.title.trim().length > TITLE_MAX) {
      errors.push(`title(제목)은 ${TITLE_MAX}자 이하여야 합니다.`);
    } else {
      result.title = body.title.trim();
    }
  }

  // 담당자
  if (body.assignee !== undefined || !partial) {
    if (typeof body.assignee !== "string" || body.assignee.trim() === "") {
      errors.push("assignee(담당자)는 비어 있지 않은 문자열이어야 합니다.");
    } else if (body.assignee.trim().length > ASSIGNEE_MAX) {
      errors.push(`assignee(담당자)는 ${ASSIGNEE_MAX}자 이하여야 합니다.`);
    } else {
      result.assignee = body.assignee.trim();
    }
  }

  // 우선순위 (생성 시 생략하면 보통)
  if (body.priority !== undefined) {
    if (!PRIORITIES.includes(body.priority as Priority)) {
      errors.push(`priority(우선순위)는 ${PRIORITIES.join(", ")} 중 하나여야 합니다.`);
    } else {
      result.priority = body.priority as Priority;
    }
  }

  // 마감일 (null 또는 빈 문자열이면 마감일 없음)
  if (body.dueDate !== undefined) {
    if (body.dueDate === null || body.dueDate === "") {
      result.dueDate = null;
    } else if (typeof body.dueDate !== "string" || !isValidDateString(body.dueDate)) {
      errors.push("dueDate(마감일)는 YYYY-MM-DD 형식의 올바른 날짜여야 합니다.");
    } else {
      result.dueDate = body.dueDate;
    }
  }

  // 완료 여부
  if (body.completed !== undefined) {
    if (typeof body.completed !== "boolean") {
      errors.push("completed(완료 여부)는 true 또는 false 여야 합니다.");
    } else {
      result.completed = body.completed;
    }
  }

  if (partial && errors.length === 0 && Object.keys(result).length === 0) {
    errors.push("수정할 필드가 하나 이상 필요합니다.");
  }
  if (errors.length > 0) throw new ValidationError(errors);
  return result;
}

export class TodoService {
  private todos = new Map<number, Todo>();
  private nextId = 1;

  /** now 는 테스트에서 "오늘"을 고정하기 위해 주입할 수 있다 */
  constructor(private readonly now: () => Date = () => new Date()) {}

  /** 마감 지남 = 미완료이면서 마감일이 오늘보다 이전 */
  private toView(todo: Todo): TodoView {
    const today = toDateString(this.now());
    const overdue = !todo.completed && todo.dueDate !== null && todo.dueDate < today;
    return { ...todo, overdue };
  }

  list(filter: TodoFilter = {}): TodoView[] {
    const status: StatusFilter = filter.status ?? "all";
    if (!STATUS_FILTERS.includes(status)) {
      throw new ValidationError([`status(상태)는 ${STATUS_FILTERS.join(", ")} 중 하나여야 합니다.`]);
    }
    const assignee = filter.assignee?.trim();

    return [...this.todos.values()]
      .map((todo) => this.toView(todo))
      .filter((todo) => {
        if (status === "active" && todo.completed) return false;
        if (status === "completed" && !todo.completed) return false;
        if (status === "overdue" && !todo.overdue) return false;
        if (assignee && todo.assignee !== assignee) return false;
        return true;
      })
      .sort(compareTodos);
  }

  get(id: number): TodoView {
    const todo = this.todos.get(id);
    if (!todo) throw new NotFoundError(`id=${id} 인 할 일을 찾을 수 없습니다.`);
    return this.toView(todo);
  }

  create(raw: unknown): TodoView {
    const input = validateInput(raw, false) as CreateTodoInput;
    const timestamp = this.now().toISOString();
    const todo: Todo = {
      id: this.nextId++,
      title: input.title,
      assignee: input.assignee,
      priority: input.priority ?? "medium",
      dueDate: input.dueDate ?? null,
      completed: input.completed ?? false,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    this.todos.set(todo.id, todo);
    return this.toView(todo);
  }

  update(id: number, raw: unknown): TodoView {
    const existing = this.todos.get(id);
    if (!existing) throw new NotFoundError(`id=${id} 인 할 일을 찾을 수 없습니다.`);
    const input = validateInput(raw, true);
    const updated: Todo = { ...existing, ...input, updatedAt: this.now().toISOString() };
    this.todos.set(id, updated);
    return this.toView(updated);
  }

  remove(id: number): void {
    if (!this.todos.delete(id)) throw new NotFoundError(`id=${id} 인 할 일을 찾을 수 없습니다.`);
  }

  /** 등록된 담당자 목록 (중복 제거, 가나다순) */
  assignees(): string[] {
    const names = new Set([...this.todos.values()].map((todo) => todo.assignee));
    return [...names].sort((a, b) => a.localeCompare(b, "ko"));
  }
}

/** 정렬: 미완료 먼저 → 마감일 빠른 순(없으면 뒤) → 우선순위 높은 순 → 등록 순 */
function compareTodos(a: Todo, b: Todo): number {
  if (a.completed !== b.completed) return a.completed ? 1 : -1;
  if (a.dueDate !== b.dueDate) {
    if (a.dueDate === null) return 1;
    if (b.dueDate === null) return -1;
    return a.dueDate < b.dueDate ? -1 : 1;
  }
  if (a.priority !== b.priority) return PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
  return a.id - b.id;
}
