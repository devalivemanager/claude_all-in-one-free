package com.example.hr.repository;

import com.example.hr.domain.Employee;
import org.springframework.stereotype.Repository;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 사원 인메모리 저장소. 사번을 키로 사용한다.
 */
@Repository
public class EmployeeRepository {

    private final Map<String, Employee> store = new ConcurrentHashMap<>();

    public Employee save(Employee employee) {
        store.put(employee.employeeNo(), employee);
        return employee;
    }

    public Optional<Employee> findByEmployeeNo(String employeeNo) {
        return Optional.ofNullable(store.get(employeeNo));
    }

    public boolean existsByEmployeeNo(String employeeNo) {
        return store.containsKey(employeeNo);
    }

    public boolean existsByDepartmentId(Long departmentId) {
        return store.values().stream()
                .anyMatch(e -> e.departmentId().equals(departmentId));
    }

    public List<Employee> findAll() {
        return store.values().stream()
                .sorted(Comparator.comparing(Employee::employeeNo))
                .toList();
    }

    public void deleteByEmployeeNo(String employeeNo) {
        store.remove(employeeNo);
    }

    /** 테스트 격리를 위해 모든 데이터를 지운다. */
    public void clear() {
        store.clear();
    }
}
