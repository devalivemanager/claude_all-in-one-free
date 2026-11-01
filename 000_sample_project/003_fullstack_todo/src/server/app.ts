// Express 앱 구성: REST API 라우트 + 정적 파일 서빙 + 에러 처리
import path from "node:path";
import { fileURLToPath } from "node:url";
import express, { type NextFunction, type Request, type Response } from "express";
import { NotFoundError, ValidationError } from "./errors.js";
import { TodoService } from "./todoService.js";
import type { ErrorResponse, StatusFilter } from "./types.js";

// 이 파일 위치(src/server 또는 dist/server)에서 프로젝트 루트를 찾는다
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

/** URL 의 :id 를 양의 정수로 변환한다. 숫자가 아니면 400 */
function parseId(value: string): number {
  const id = Number(value);
  if (!Number.isInteger(id) || id <= 0) {
    throw new ValidationError(["id 는 양의 정수여야 합니다."]);
  }
  return id;
}

/** 쿼리 문자열 값을 문자열 하나로 정리한다 (배열 등은 무시) */
function queryString(value: unknown): string | undefined {
  return typeof value === "string" && value !== "" ? value : undefined;
}

export function createApp(service: TodoService = new TodoService()) {
  const app = express();
  app.use(express.json());

  const api = express.Router();

  // 목록 조회 (필터: ?status=all|active|completed|overdue&assignee=이름)
  api.get("/todos", (req, res) => {
    const status = queryString(req.query.status) as StatusFilter | undefined;
    const assignee = queryString(req.query.assignee);
    res.json(service.list({ status, assignee }));
  });

  api.get("/todos/:id", (req, res) => {
    res.json(service.get(parseId(req.params.id)));
  });

  api.post("/todos", (req, res) => {
    res.status(201).json(service.create(req.body));
  });

  api.patch("/todos/:id", (req, res) => {
    res.json(service.update(parseId(req.params.id), req.body));
  });

  api.delete("/todos/:id", (req, res) => {
    service.remove(parseId(req.params.id));
    res.status(204).end();
  });

  api.get("/assignees", (_req, res) => {
    res.json(service.assignees());
  });

  // 정의되지 않은 API 경로
  api.use((_req, _res, next) => {
    next(new NotFoundError("요청한 API 경로를 찾을 수 없습니다."));
  });

  app.use("/api", api);

  // 프론트엔드: HTML/CSS 는 public/, 빌드된 app.js 는 dist/public/
  app.use(express.static(path.join(projectRoot, "public")));
  app.use(express.static(path.join(projectRoot, "dist/public")));

  // 공통 에러 처리기: 모든 에러를 JSON 으로 응답한다
  app.use((err: unknown, _req: Request, res: Response<ErrorResponse>, _next: NextFunction) => {
    if (err instanceof ValidationError) {
      res.status(400).json({ error: err.message, details: err.details });
      return;
    }
    if (err instanceof NotFoundError) {
      res.status(404).json({ error: err.message });
      return;
    }
    // express.json() 이 잘못된 JSON 을 만나면 type 이 entity.parse.failed 인 에러를 던진다
    if (typeof err === "object" && err !== null && (err as { type?: string }).type === "entity.parse.failed") {
      res.status(400).json({ error: "요청 본문이 올바른 JSON 이 아닙니다." });
      return;
    }
    console.error(err);
    res.status(500).json({ error: "서버 내부 오류가 발생했습니다." });
  });

  return app;
}
