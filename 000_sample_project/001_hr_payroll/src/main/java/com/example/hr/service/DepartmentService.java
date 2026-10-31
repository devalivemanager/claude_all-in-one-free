package com.example.hr.service;

import com.example.hr.domain.Department;
import com.example.hr.dto.DepartmentRequest;
import com.example.hr.exception.ApiException;
import com.example.hr.repository.DepartmentRepository;
import com.example.hr.repository.EmployeeRepository;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 부서 CRUD 비즈니스 로직.
 */
@Service
public class DepartmentService {

    private final DepartmentRepository departmentRepository;
    private final EmployeeRepository employeeRepository;

    public DepartmentService(DepartmentRepository departmentRepository,
                             EmployeeRepository employeeRepository) {
        this.departmentRepository = departmentRepository;
        this.employeeRepository = employeeRepository;
    }

    public Department create(DepartmentRequest request) {
        return departmentRepository.create(request.name().trim());
    }

    public List<Department> findAll() {
        return departmentRepository.findAll();
    }

    public Department findById(Long id) {
        return departmentRepository.findById(id)
                .orElseThrow(() -> ApiException.notFound("부서를 찾을 수 없습니다. id=" + id));
    }

    public Department update(Long id, DepartmentRequest request) {
        findById(id);
        return departmentRepository.update(new Department(id, request.name().trim()));
    }

    /** 소속 사원이 있는 부서는 삭제할 수 없다. */
    public void delete(Long id) {
        findById(id);
        if (employeeRepository.existsByDepartmentId(id)) {
            throw ApiException.conflict("소속 사원이 있는 부서는 삭제할 수 없습니다. id=" + id);
        }
        departmentRepository.deleteById(id);
    }
}
