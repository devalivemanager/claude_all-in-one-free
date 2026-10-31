package com.example.hr.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.List;

/**
 * 모든 컨트롤러의 예외를 공통 {@link ErrorResponse} 형식으로 변환한다.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    /** @Valid 검증 실패 → 400 + 필드별 오류 목록 */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        List<ErrorResponse.FieldError> errors = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> new ErrorResponse.FieldError(e.getField(), e.getDefaultMessage()))
                .toList();
        return build(HttpStatus.BAD_REQUEST, "VALIDATION_FAILED", "입력값 검증에 실패했습니다.", errors);
    }

    /** JSON 문법 오류, 날짜 형식 오류 등 본문을 읽을 수 없음 → 400 */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleNotReadable(HttpMessageNotReadableException ex) {
        return build(HttpStatus.BAD_REQUEST, "MALFORMED_REQUEST",
                "요청 본문을 해석할 수 없습니다. JSON 형식과 날짜 형식(yyyy-MM-dd, yyyy-MM)을 확인하세요.", List.of());
    }

    /** 경로 변수 타입 불일치(예: /api/departments/abc) → 400 */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponse> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        return build(HttpStatus.BAD_REQUEST, "TYPE_MISMATCH",
                "'" + ex.getName() + "' 값의 형식이 올바르지 않습니다.", List.of());
    }

    /** 비즈니스 규칙 위반 → 예외에 담긴 상태 코드 */
    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ErrorResponse> handleApi(ApiException ex) {
        return build(ex.getStatus(), ex.getCode(), ex.getMessage(), List.of());
    }

    private ResponseEntity<ErrorResponse> build(HttpStatus status, String code, String message,
                                                List<ErrorResponse.FieldError> errors) {
        return ResponseEntity.status(status)
                .body(new ErrorResponse(status.value(), code, message, errors));
    }
}
