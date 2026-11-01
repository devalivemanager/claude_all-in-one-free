package com.example.hr.exception;

import org.springframework.http.HttpStatus;

/**
 * 비즈니스 규칙 위반을 HTTP 상태 코드와 함께 표현하는 예외.
 */
public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final String code;

    public ApiException(HttpStatus status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    /** 대상을 찾을 수 없음(404). */
    public static ApiException notFound(String message) {
        return new ApiException(HttpStatus.NOT_FOUND, "NOT_FOUND", message);
    }

    /** 현재 상태와 충돌(409). 예: 사번 중복, 사원이 있는 부서 삭제. */
    public static ApiException conflict(String message) {
        return new ApiException(HttpStatus.CONFLICT, "CONFLICT", message);
    }

    /** 잘못된 요청(400). 예: 입사 전 월의 급여 계산. */
    public static ApiException badRequest(String message) {
        return new ApiException(HttpStatus.BAD_REQUEST, "BAD_REQUEST", message);
    }

    public HttpStatus getStatus() {
        return status;
    }

    public String getCode() {
        return code;
    }
}
