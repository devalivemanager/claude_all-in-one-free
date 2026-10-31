package com.example.hr.controller;

import com.example.hr.domain.Employee;
import com.example.hr.dto.EmployeeCreateRequest;
import com.example.hr.dto.EmployeeUpdateRequest;
import com.example.hr.service.EmployeeService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 사원 CRUD API. 사원은 사번(employeeNo)으로 식별한다.
 */
@RestController
@RequestMapping("/api/employees")
public class EmployeeController {

    private final EmployeeService employeeService;

    public EmployeeController(EmployeeService employeeService) {
        this.employeeService = employeeService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Employee create(@Valid @RequestBody EmployeeCreateRequest request) {
        return employeeService.create(request);
    }

    @GetMapping
    public List<Employee> findAll() {
        return employeeService.findAll();
    }

    @GetMapping("/{employeeNo}")
    public Employee findByEmployeeNo(@PathVariable String employeeNo) {
        return employeeService.findByEmployeeNo(employeeNo);
    }

    @PutMapping("/{employeeNo}")
    public Employee update(@PathVariable String employeeNo,
                           @Valid @RequestBody EmployeeUpdateRequest request) {
        return employeeService.update(employeeNo, request);
    }

    @DeleteMapping("/{employeeNo}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable String employeeNo) {
        employeeService.delete(employeeNo);
    }
}
