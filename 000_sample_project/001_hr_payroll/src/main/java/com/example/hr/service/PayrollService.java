package com.example.hr.service;

import com.example.hr.domain.Department;
import com.example.hr.domain.Employee;
import com.example.hr.dto.PayrollRequest;
import com.example.hr.dto.PayrollResponse;
import com.example.hr.dto.PayrollResult;
import com.example.hr.exception.ApiException;
import org.springframework.stereotype.Service;

import java.time.YearMonth;

/**
 * 사원 정보를 조회해 월 급여를 계산한다.
 */
@Service
public class PayrollService {

    private final EmployeeService employeeService;
    private final DepartmentService departmentService;
    private final PayrollCalculator payrollCalculator;

    public PayrollService(EmployeeService employeeService, DepartmentService departmentService,
                          PayrollCalculator payrollCalculator) {
        this.employeeService = employeeService;
        this.departmentService = departmentService;
        this.payrollCalculator = payrollCalculator;
    }

    public PayrollResponse calculate(PayrollRequest request) {
        Employee employee = employeeService.findByEmployeeNo(request.employeeNo());

        // 입사한 달보다 이전 월의 급여는 계산하지 않는다.
        if (request.payMonth().isBefore(YearMonth.from(employee.hireDate()))) {
            throw ApiException.badRequest("입사월(" + YearMonth.from(employee.hireDate())
                    + ") 이전의 급여는 계산할 수 없습니다.");
        }

        Department department = departmentService.findById(employee.departmentId());
        PayrollResult result = payrollCalculator.calculate(
                employee.basePay(), request.mealAllowance(), request.otherAllowance());
        return new PayrollResponse(employee.employeeNo(), employee.name(), department.name(),
                request.payMonth(), result);
    }
}
