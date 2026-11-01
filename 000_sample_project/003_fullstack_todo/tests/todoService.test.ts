// TodoService 단위 테스트
import { beforeEach, describe, expect, it } from "vitest";
import { NotFoundError, ValidationError } from "../src/server/errors.js";
import { isValidDateString, TodoService } from "../src/server/todoService.js";

// "오늘"을 2026-10-31 로 고정한다
const fixedNow = () => new Date(2026, 9, 31, 12, 0, 0);

describe("TodoService", () => {
  let service: TodoService;

  beforeEach(() => {
    service = new TodoService(fixedNow);
  });

  describe("생성", () => {
    it("기본값(우선순위 보통, 미완료, 마감일 없음)으로 할 일을 만든다", () => {
      const todo = service.create({ title: "  보고서 작성  ", assignee: " 김민수 " });
      expect(todo).toMatchObject({
        id: 1,
        title: "보고서 작성",
        assignee: "김민수",
        priority: "medium",
        dueDate: null,
        completed: false,
        overdue: false,
      });
    });

    it("id 는 1부터 순서대로 증가한다", () => {
      const a = service.create({ title: "A", assignee: "가" });
      const b = service.create({ title: "B", assignee: "나" });
      expect([a.id, b.id]).toEqual([1, 2]);
    });

    it("제목과 담당자가 없으면 ValidationError 를 던지고 두 오류를 모두 알려 준다", () => {
      try {
        service.create({ title: "   " });
        expect.unreachable();
      } catch (error) {
        expect(error).toBeInstanceOf(ValidationError);
        expect((error as ValidationError).details).toHaveLength(2);
      }
    });

    it("잘못된 우선순위, 마감일, 완료 여부를 거부한다", () => {
      expect(() => service.create({ title: "A", assignee: "가", priority: "urgent" })).toThrow(ValidationError);
      expect(() => service.create({ title: "A", assignee: "가", dueDate: "2026-02-30" })).toThrow(ValidationError);
      expect(() => service.create({ title: "A", assignee: "가", dueDate: "10/31/2026" })).toThrow(ValidationError);
      expect(() => service.create({ title: "A", assignee: "가", completed: "yes" })).toThrow(ValidationError);
    });

    it("너무 긴 제목을 거부한다", () => {
      expect(() => service.create({ title: "가".repeat(101), assignee: "김민수" })).toThrow(ValidationError);
    });

    it("객체가 아닌 입력을 거부한다", () => {
      expect(() => service.create(null)).toThrow(ValidationError);
      expect(() => service.create([1, 2])).toThrow(ValidationError);
    });
  });

  describe("조회", () => {
    it("없는 id 는 NotFoundError 를 던진다", () => {
      expect(() => service.get(99)).toThrow(NotFoundError);
    });

    it("미완료 → 마감일 빠른 순 → 우선순위 순으로 정렬한다", () => {
      service.create({ title: "완료됨", assignee: "가", dueDate: "2026-10-01", completed: true });
      service.create({ title: "마감 없음", assignee: "가" });
      service.create({ title: "11월 낮음", assignee: "가", dueDate: "2026-11-05", priority: "low" });
      service.create({ title: "11월 높음", assignee: "가", dueDate: "2026-11-05", priority: "high" });
      service.create({ title: "10월", assignee: "가", dueDate: "2026-10-20" });
      expect(service.list().map((t) => t.title)).toEqual(["10월", "11월 높음", "11월 낮음", "마감 없음", "완료됨"]);
    });
  });

  describe("마감 지남 표시", () => {
    it("마감일이 오늘보다 이전이고 미완료이면 overdue 이다", () => {
      expect(service.create({ title: "어제", assignee: "가", dueDate: "2026-10-30" }).overdue).toBe(true);
    });

    it("마감일이 오늘이면 overdue 가 아니다", () => {
      expect(service.create({ title: "오늘", assignee: "가", dueDate: "2026-10-31" }).overdue).toBe(false);
    });

    it("완료된 항목은 마감일이 지나도 overdue 가 아니다", () => {
      expect(service.create({ title: "완료", assignee: "가", dueDate: "2026-10-01", completed: true }).overdue).toBe(false);
    });
  });

  describe("필터", () => {
    beforeEach(() => {
      service.create({ title: "진행 중", assignee: "김민수", dueDate: "2026-11-10" });
      service.create({ title: "마감 지남", assignee: "이지은", dueDate: "2026-10-01" });
      service.create({ title: "완료", assignee: "김민수", completed: true });
    });

    it("상태별로 거른다", () => {
      expect(service.list({ status: "all" })).toHaveLength(3);
      expect(service.list({ status: "active" }).map((t) => t.title)).toEqual(["마감 지남", "진행 중"]);
      expect(service.list({ status: "completed" }).map((t) => t.title)).toEqual(["완료"]);
      expect(service.list({ status: "overdue" }).map((t) => t.title)).toEqual(["마감 지남"]);
    });

    it("담당자로 거르고, 상태 필터와 함께 쓸 수 있다", () => {
      expect(service.list({ assignee: "김민수" })).toHaveLength(2);
      expect(service.list({ assignee: "김민수", status: "completed" }).map((t) => t.title)).toEqual(["완료"]);
      expect(service.list({ assignee: "없는사람" })).toEqual([]);
    });

    it("알 수 없는 상태 값은 ValidationError 를 던진다", () => {
      expect(() => service.list({ status: "done" as never })).toThrow(ValidationError);
    });

    it("담당자 목록을 중복 없이 돌려준다", () => {
      expect(service.assignees()).toEqual(["김민수", "이지은"]);
    });
  });

  describe("수정과 삭제", () => {
    it("일부 필드만 수정하고 나머지는 유지한다", () => {
      const created = service.create({ title: "원래 제목", assignee: "김민수", priority: "low" });
      const updated = service.update(created.id, { completed: true, dueDate: "2026-12-01" });
      expect(updated).toMatchObject({ title: "원래 제목", priority: "low", completed: true, dueDate: "2026-12-01" });
    });

    it("dueDate 에 null 을 주면 마감일을 지운다", () => {
      const created = service.create({ title: "A", assignee: "가", dueDate: "2026-12-01" });
      expect(service.update(created.id, { dueDate: null }).dueDate).toBeNull();
    });

    it("빈 수정 요청과 잘못된 값을 거부한다", () => {
      const created = service.create({ title: "A", assignee: "가" });
      expect(() => service.update(created.id, {})).toThrow(ValidationError);
      expect(() => service.update(created.id, { title: "" })).toThrow(ValidationError);
    });

    it("없는 id 수정/삭제는 NotFoundError 를 던진다", () => {
      expect(() => service.update(42, { title: "B" })).toThrow(NotFoundError);
      expect(() => service.remove(42)).toThrow(NotFoundError);
    });

    it("삭제하면 더 이상 조회되지 않는다", () => {
      const created = service.create({ title: "A", assignee: "가" });
      service.remove(created.id);
      expect(service.list()).toEqual([]);
    });
  });
});

describe("isValidDateString", () => {
  it("실제로 존재하는 날짜만 허용한다", () => {
    expect(isValidDateString("2028-02-29")).toBe(true);
    expect(isValidDateString("2026-02-29")).toBe(false);
    expect(isValidDateString("2026-13-01")).toBe(false);
    expect(isValidDateString("2026-1-1")).toBe(false);
  });
});
