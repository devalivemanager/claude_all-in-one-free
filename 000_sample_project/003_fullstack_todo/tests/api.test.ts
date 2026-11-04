// REST API 테스트 (supertest 로 실제 HTTP 요청을 보낸다)
import request from "supertest";
import { beforeEach, describe, expect, it } from "vitest";
import { createApp } from "../src/server/app.js";
import { TodoService } from "../src/server/todoService.js";

// "오늘"을 2026-10-31 로 고정한다
const fixedNow = () => new Date(2026, 9, 31, 12, 0, 0);

describe("할 일 REST API", () => {
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    app = createApp(new TodoService(fixedNow));
  });

  /** 테스트용 할 일을 하나 만든다 */
  async function createTodo(body: Record<string, unknown>) {
    const res = await request(app).post("/api/todos").send(body);
    expect(res.status).toBe(201);
    return res.body;
  }

  describe("POST /api/todos", () => {
    it("할 일을 만들고 201 과 생성된 항목을 돌려준다", async () => {
      const res = await request(app)
        .post("/api/todos")
        .send({ title: "보고서 작성", assignee: "김민수", priority: "high", dueDate: "2026-11-03" });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({ id: 1, title: "보고서 작성", priority: "high", completed: false, overdue: false });
    });

    it("검증에 실패하면 400 과 상세 오류를 돌려준다", async () => {
      const res = await request(app).post("/api/todos").send({ title: "", priority: "urgent" });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe("입력값이 올바르지 않습니다.");
      expect(res.body.details).toHaveLength(3);
    });

    it("잘못된 JSON 본문은 400 을 돌려준다", async () => {
      const res = await request(app).post("/api/todos").set("Content-Type", "application/json").send("{ 잘못된 json");
      expect(res.status).toBe(400);
      expect(res.body.error).toContain("JSON");
    });
  });

  describe("GET /api/todos", () => {
    beforeEach(async () => {
      await createTodo({ title: "진행 중", assignee: "김민수", dueDate: "2026-11-10" });
      await createTodo({ title: "마감 지남", assignee: "이지은", dueDate: "2026-10-01" });
      await createTodo({ title: "완료", assignee: "김민수", completed: true });
    });

    it("전체 목록을 돌려준다", async () => {
      const res = await request(app).get("/api/todos");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
    });

    it("status 와 assignee 쿼리로 필터링한다", async () => {
      const overdue = await request(app).get("/api/todos?status=overdue");
      expect(overdue.body.map((t: { title: string }) => t.title)).toEqual(["마감 지남"]);
      expect(overdue.body[0].overdue).toBe(true);

      const mine = await request(app).get("/api/todos").query({ assignee: "김민수", status: "active" });
      expect(mine.body.map((t: { title: string }) => t.title)).toEqual(["진행 중"]);
    });

    it("알 수 없는 status 는 400 을 돌려준다", async () => {
      const res = await request(app).get("/api/todos?status=unknown");
      expect(res.status).toBe(400);
    });

    it("GET /api/assignees 는 담당자 목록을 돌려준다", async () => {
      const res = await request(app).get("/api/assignees");
      expect(res.body).toEqual(["김민수", "이지은"]);
    });
  });

  describe("GET /api/todos/:id", () => {
    it("단건을 조회한다", async () => {
      const created = await createTodo({ title: "A", assignee: "가" });
      const res = await request(app).get(`/api/todos/${created.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("A");
    });

    it("없는 id 는 404, 숫자가 아닌 id 는 400 을 돌려준다", async () => {
      expect((await request(app).get("/api/todos/999")).status).toBe(404);
      expect((await request(app).get("/api/todos/abc")).status).toBe(400);
    });
  });

  describe("PATCH /api/todos/:id", () => {
    it("완료 처리하면 마감 지남 표시가 사라진다", async () => {
      const created = await createTodo({ title: "A", assignee: "가", dueDate: "2026-10-01" });
      expect(created.overdue).toBe(true);
      const res = await request(app).patch(`/api/todos/${created.id}`).send({ completed: true });
      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({ completed: true, overdue: false });
    });

    it("잘못된 값은 400, 없는 id 는 404 를 돌려준다", async () => {
      const created = await createTodo({ title: "A", assignee: "가" });
      expect((await request(app).patch(`/api/todos/${created.id}`).send({ dueDate: "내일" })).status).toBe(400);
      expect((await request(app).patch("/api/todos/999").send({ title: "B" })).status).toBe(404);
    });

    // README : 빈 PATCH 요청은 400
    it("바꿀 필드가 없는 빈 PATCH 는 400 과 상세 오류를 돌려준다", async () => {
      const created = await createTodo({ title: "A", assignee: "가" });
      const res = await request(app).patch(`/api/todos/${created.id}`).send({});
      expect(res.status).toBe(400);
      expect(res.body.error).toBeTruthy();
    });
  });

  describe("DELETE /api/todos/:id", () => {
    it("삭제하면 204 를 돌려주고, 다시 삭제하면 404 를 돌려준다", async () => {
      const created = await createTodo({ title: "A", assignee: "가" });
      expect((await request(app).delete(`/api/todos/${created.id}`)).status).toBe(204);
      expect((await request(app).delete(`/api/todos/${created.id}`)).status).toBe(404);
    });
  });

  it("정의되지 않은 API 경로는 JSON 404 를 돌려준다", async () => {
    const res = await request(app).get("/api/unknown");
    expect(res.status).toBe(404);
    expect(res.body.error).toBeDefined();
  });

  it("루트 경로에서 HTML 화면을 제공한다", async () => {
    const res = await request(app).get("/");
    expect(res.status).toBe(200);
    expect(res.text).toContain("업무 할 일 관리");
  });
});
