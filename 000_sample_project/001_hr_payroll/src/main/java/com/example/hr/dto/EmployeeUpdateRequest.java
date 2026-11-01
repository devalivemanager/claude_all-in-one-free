package com.example.hr.dto;

import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PastOrPresent;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 사원 수정 요청. 사번은 URL 경로로 받으므로 본문에 없다.
 */
public record EmployeeUpdateRequest(
        @NotBlank(message = "이름은 필수입니다.")
        @Size(max = 30, message = "이름은 30자 이하여야 합니다.")
        String name,

        @NotNull(message = "부서 ID 는 필수입니다.")
        Long departmentId,

        @NotNull(message = "기본급은 필수입니다.")
        @PositiveOrZero(message = "기본급은 0 이상이어야 합니다.")
        @Digits(integer = 12, fraction = 0, message = "기본급은 원 단위 정수여야 합니다.")
        BigDecimal basePay,

        @NotNull(message = "입사일은 필수입니다.")
        @PastOrPresent(message = "입사일은 오늘 이전이어야 합니다.")
        LocalDate hireDate
) {
}
