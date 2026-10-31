package com.example.hr.dto;

import java.time.YearMonth;

/**
 * 월 급여 계산 API 응답.
 */
public record PayrollResponse(
        String employeeNo,
        String employeeName,
        String departmentName,
        YearMonth payMonth,
        PayrollResult payroll
) {
}
