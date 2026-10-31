package com.example.hr.service;

import com.example.hr.domain.Employee;
import com.example.hr.dto.EmployeeCreateRequest;
import com.example.hr.dto.EmployeeUpdateRequest;
import com.example.hr.exception.ApiException;
import com.example.hr.repository.EmployeeRepository;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 사원 CRUD 비즈니스 로직.
 */
@Service
public class EmployeeService {

    private final EmployeeRepository employeeRepository;
    private final DepartmentService departmentService;

    public EmployeeService(EmployeeRepository employeeRepository, DepartmentService departmentService) {
        this.employeeRepository = employeeRepository;
        this.departmentService = departmentService;
    }

    public Employee create(EmployeeCreateRequest request) {
        if (employeeRepository.existsByEmployeeNo(request.employeeNo())) {
            throw ApiException.conflict("이미 존재하는 사번입니다. employeeNo=" + request.employeeNo());
        }
        // 존재하지 않는 부서면 404
        departmentService.findById(request.departmentId());
        return employeeRepository.save(new Employee(
                request.employeeNo(), request.name().trim(), request.departmentId(),
                request.basePay(), request.hireDate()));
    }

    public List<Employee> findAll() {
        return employeeRepository.findAll();
    }

    public Employee findByEmployeeNo(String employeeNo) {
        return employeeRepository.findByEmployeeNo(employeeNo)
                .orElseThrow(() -> ApiException.notFound("사원을 찾을 수 없습니다. employeeNo=" + employeeNo));
    }

    public Employee update(String employeeNo, EmployeeUpdateRequest request) {
        findByEmployeeNo(employeeNo);
        departmentService.findById(request.departmentId());
        return employeeRepository.save(new Employee(
                employeeNo, request.name().trim(), request.departmentId(),
                request.basePay(), request.hireDate()));
    }

    public void delete(String employeeNo) {
        findByEmployeeNo(employeeNo);
        employeeRepository.deleteByEmployeeNo(employeeNo);
    }
}
