// 서비스 계층에서 던지는 에러. HTTP 상태 코드를 함께 가진다.

export class ValidationError extends Error {
  readonly status = 400;
  constructor(public readonly details: string[]) {
    super("입력값이 올바르지 않습니다.");
    this.name = "ValidationError";
  }
}

export class NotFoundError extends Error {
  readonly status = 404;
  constructor(message = "할 일을 찾을 수 없습니다.") {
    super(message);
    this.name = "NotFoundError";
  }
}
