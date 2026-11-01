package com.example.hr.dto;

import java.math.BigDecimal;

/**
 * 급여 계산 결과(지급 항목, 공제 항목, 실수령액). 모든 금액은 원 단위 절사된 값이다.
 */
public record PayrollResult(
        BigDecimal basePay,
        BigDecimal mealAllowance,
        BigDecimal otherAllowance,
        BigDecimal grossPay,
        BigDecimal nonTaxableAmount,
        BigDecimal taxableAmount,
        BigDecimal nationalPension,
        BigDecimal healthInsurance,
        BigDecimal longTermCareInsurance,
        BigDecimal employmentInsurance,
        BigDecimal incomeTax,
        BigDecimal localIncomeTax,
        BigDecimal totalDeduction,
        BigDecimal netPay
) {
}
