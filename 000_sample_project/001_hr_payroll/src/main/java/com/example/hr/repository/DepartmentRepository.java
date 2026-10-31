package com.example.hr.repository;

import com.example.hr.domain.Department;
import org.springframework.stereotype.Repository;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 부서 인메모리 저장소. 애플리케이션을 재시작하면 데이터가 사라진다.
 */
@Repository
public class DepartmentRepository {

    private final Map<Long, Department> store = new ConcurrentHashMap<>();
    private final AtomicLong sequence = new AtomicLong();

    /** 새 부서를 저장하고 ID 를 발급한다. */
    public Department create(String name) {
        Department department = new Department(sequence.incrementAndGet(), name);
        store.put(department.id(), department);
        return department;
    }

    public Department update(Department department) {
        store.put(department.id(), department);
        return department;
    }

    public Optional<Department> findById(Long id) {
        return Optional.ofNullable(store.get(id));
    }

    public List<Department> findAll() {
        return store.values().stream()
                .sorted(Comparator.comparing(Department::id))
                .toList();
    }

    public void deleteById(Long id) {
        store.remove(id);
    }

    /** 테스트 격리를 위해 모든 데이터를 지우고 ID 순번도 초기화한다. */
    public void clear() {
        store.clear();
        sequence.set(0);
    }
}
