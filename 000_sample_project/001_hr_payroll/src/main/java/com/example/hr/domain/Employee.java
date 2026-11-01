package com.example.hr.domain;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 사원.
 *
 * @param employeeNo   사번(예: E0001)
 * @param name         이름
 * @param departmentId 소속 부서 ID
 * @param basePay      월 기본급(원)
 * @param hireDate     입사일
 */
public record Employee(String employeeNo, String name, Long departmentId,
                       BigDecimal basePay, LocalDate hireDate) {
}
