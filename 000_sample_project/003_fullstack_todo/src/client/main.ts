// 프론트엔드: 프레임워크 없이 DOM API 와 fetch 로 REST API 를 호출한다
import type { ErrorResponse, Priority, StatusFilter, TodoView } from "../server/types.js";

const PRIORITY_LABELS: Record<Priority, string> = { high: "높음", medium: "보통", low: "낮음" };

// 화면 요소
const form = document.querySelector<HTMLFormElement>("#todo-form")!;
const formTitle = document.querySelector<HTMLHeadingElement>("#form-title")!;
const formError = document.querySelector<HTMLParagraphElement>("#form-error")!;
const submitButton = document.querySelector<HTMLButtonElement>("#submit-button")!;
const cancelEditButton = document.querySelector<HTMLButtonElement>("#cancel-edit")!;
const statusFilter = document.querySelector<HTMLSelectElement>("#status-filter")!;
const assigneeFilter = document.querySelector<HTMLSelectElement>("#assignee-filter")!;
const todoList = document.querySelector<HTMLUListElement>("#todo-list")!;
const emptyMessage = document.querySelector<HTMLParagraphElement>("#empty-message")!;
const summary = document.querySelector<HTMLSpanElement>("#summary")!;

/** 수정 중인 할 일 id (null 이면 새로 추가 모드) */
let editingId: number | null = null;

/** API 호출 공통 함수: 실패하면 서버의 에러 메시지로 Error 를 던진다 */
async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({ error: "요청에 실패했습니다." }))) as ErrorResponse;
    throw new Error([body.error, ...(body.details ?? [])].join("\n"));
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

/** 필터 조건으로 목록을 다시 불러와 그린다 */
async function refresh(): Promise<void> {
  const params = new URLSearchParams({ status: statusFilter.value as StatusFilter });
  if (assigneeFilter.value) params.set("assignee", assigneeFilter.value);

  const [todos, assignees] = await Promise.all([
    request<TodoView[]>(`/api/todos?${params}`),
    request<string[]>("/api/assignees"),
  ]);
  renderAssigneeOptions(assignees);
  renderTodos(todos);
}

function renderAssigneeOptions(assignees: string[]): void {
  const selected = assigneeFilter.value;
  assigneeFilter.replaceChildren(new Option("전체", ""));
  for (const name of assignees) assigneeFilter.add(new Option(name, name));
  // 선택했던 담당자가 아직 있으면 선택 상태를 유지한다
  assigneeFilter.value = assignees.includes(selected) ? selected : "";
}

function renderTodos(todos: TodoView[]): void {
  todoList.replaceChildren(...todos.map(createTodoItem));
  emptyMessage.hidden = todos.length > 0;
  const overdueCount = todos.filter((todo) => todo.overdue).length;
  summary.textContent = `${todos.length}건 표시 · 마감 지남 ${overdueCount}건`;
}

/** 텍스트를 넣은 요소를 만든다 (innerHTML 대신 textContent 로 XSS 방지) */
function el<K extends keyof HTMLElementTagNameMap>(tag: K, className: string, text = ""): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = text;
  return element;
}

function createTodoItem(todo: TodoView): HTMLLIElement {
  const item = el("li", "todo-item");
  item.dataset.id = String(todo.id);
  item.classList.toggle("completed", todo.completed);
  item.classList.toggle("overdue", todo.overdue);

  // 완료 체크박스
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = todo.completed;
  checkbox.title = "완료 여부";
  checkbox.addEventListener("change", () => {
    void runAction(() => request(`/api/todos/${todo.id}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: checkbox.checked }),
    }));
  });

  // 제목과 부가 정보
  const main = el("div", "todo-main");
  main.append(el("div", "todo-title", todo.title));
  const meta = el("div", "todo-meta");
  meta.append(el("span", `badge ${todo.priority}`, PRIORITY_LABELS[todo.priority]));
  if (todo.overdue) meta.append(el("span", "badge overdue", "마감 지남"));
  meta.append(`담당: ${todo.assignee} · 마감: ${todo.dueDate ?? "없음"}`);
  main.append(meta);

  // 수정 / 삭제 버튼
  const actions = el("div", "todo-actions");
  const editButton = el("button", "secondary", "수정");
  editButton.type = "button";
  editButton.addEventListener("click", () => startEdit(todo));
  const deleteButton = el("button", "danger", "삭제");
  deleteButton.type = "button";
  deleteButton.addEventListener("click", () => {
    if (!confirm(`"${todo.title}" 할 일을 삭제할까요?`)) return;
    void runAction(() => request(`/api/todos/${todo.id}`, { method: "DELETE" }));
  });
  actions.append(editButton, deleteButton);

  item.append(checkbox, main, actions);
  return item;
}

/** 수정 모드로 전환하고 폼에 기존 값을 채운다 */
function startEdit(todo: TodoView): void {
  editingId = todo.id;
  (form.elements.namedItem("title") as HTMLInputElement).value = todo.title;
  (form.elements.namedItem("assignee") as HTMLInputElement).value = todo.assignee;
  (form.elements.namedItem("priority") as HTMLSelectElement).value = todo.priority;
  (form.elements.namedItem("dueDate") as HTMLInputElement).value = todo.dueDate ?? "";
  formTitle.textContent = "할 일 수정";
  submitButton.textContent = "저장";
  cancelEditButton.hidden = false;
  formError.textContent = "";
}

function resetForm(): void {
  editingId = null;
  form.reset();
  formTitle.textContent = "새 할 일 추가";
  submitButton.textContent = "추가";
  cancelEditButton.hidden = true;
}

/** 작업을 실행한 뒤 목록을 새로고침하고, 실패하면 에러를 보여 준다 */
async function runAction(action: () => Promise<unknown>): Promise<boolean> {
  formError.textContent = "";
  try {
    await action();
    await refresh();
    return true;
  } catch (error) {
    formError.textContent = error instanceof Error ? error.message : String(error);
    await refresh().catch(() => undefined);
    return false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const payload = {
    title: String(data.get("title") ?? ""),
    assignee: String(data.get("assignee") ?? ""),
    priority: String(data.get("priority") ?? "medium"),
    dueDate: String(data.get("dueDate") ?? "") || null,
  };
  const url = editingId === null ? "/api/todos" : `/api/todos/${editingId}`;
  const method = editingId === null ? "POST" : "PATCH";
  void runAction(() => request(url, { method, body: JSON.stringify(payload) })).then((ok) => {
    if (ok) resetForm();
  });
});

cancelEditButton.addEventListener("click", resetForm);
statusFilter.addEventListener("change", () => void runAction(async () => undefined));
assigneeFilter.addEventListener("change", () => void runAction(async () => undefined));

void runAction(async () => undefined);
