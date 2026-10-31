package com.example.hr.dto;

import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;
import java.time.YearMonth;

/**
 * 월 급여 계산 요청.
 *
 * @param employeeNo     사번
 * @param payMonth       급여 귀속 월(yyyy-MM)
 * @param mealAllowance  식대(월 20만원까지 비과세). 생략하면 0
 * @param otherAllowance 기타 과세 수당. 생략하면 0
 */
public record PayrollRequest(
        @NotBlank(message = "사번은 필수입니다.")
        String employeeNo,

        @NotNull(message = "급여 월(yyyy-MM)은 필수입니다.")
        YearMonth payMonth,

        @PositiveOrZero(message = "식대는 0 이상이어야 합니다.")
        @Digits(integer = 12, fraction = 0, message = "식대는 원 단위 정수여야 합니다.")
        BigDecimal mealAllowance,

        @PositiveOrZero(message = "기타 수당은 0 이상이어야 합니다.")
        @Digits(integer = 12, fraction = 0, message = "기타 수당은 원 단위 정수여야 합니다.")
        BigDecimal otherAllowance
) {
}
