// 서버와 클라이언트가 함께 쓰는 할 일(Todo) 관련 타입 정의

/** 우선순위: 높음 / 보통 / 낮음 */
export const PRIORITIES = ["high", "medium", "low"] as const;
export type Priority = (typeof PRIORITIES)[number];

/** 목록 필터용 상태: 전체 / 진행 중 / 완료 / 마감 지남 */
export const STATUS_FILTERS = ["all", "active", "completed", "overdue"] as const;
export type StatusFilter = (typeof STATUS_FILTERS)[number];

export interface Todo {
  id: number;
  title: string;
  assignee: string;
  priority: Priority;
  /** 마감일 (YYYY-MM-DD), 없으면 null */
  dueDate: string | null;
  completed: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 응답에 포함되는 할 일: 마감 지남 여부를 계산해서 붙인다 */
export interface TodoView extends Todo {
  overdue: boolean;
}

export interface CreateTodoInput {
  title: string;
  assignee: string;
  priority?: Priority;
  dueDate?: string | null;
  completed?: boolean;
}

export type UpdateTodoInput = Partial<CreateTodoInput>;

export interface TodoFilter {
  status?: StatusFilter;
  assignee?: string;
}

/** 에러 응답 형식 */
export interface ErrorResponse {
  error: string;
  details?: string[];
}
