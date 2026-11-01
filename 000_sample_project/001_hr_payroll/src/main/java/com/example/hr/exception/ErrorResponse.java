package com.example.hr.exception;

import java.util.List;

/**
 * 공통 에러 응답 본문.
 *
 * @param status  HTTP 상태 코드
 * @param code    에러 코드(예: VALIDATION_FAILED, NOT_FOUND)
 * @param message 사람이 읽을 수 있는 메시지
 * @param errors  필드별 검증 오류 목록(검증 실패가 아니면 빈 목록)
 */
public record ErrorResponse(int status, String code, String message, List<FieldError> errors) {

    public record FieldError(String field, String message) {
    }
}
