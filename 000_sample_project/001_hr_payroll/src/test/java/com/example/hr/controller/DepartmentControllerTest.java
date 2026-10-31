package com.example.hr.controller;

import com.example.hr.repository.DepartmentRepository;
import com.example.hr.repository.EmployeeRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 부서 API MockMvc 테스트.
 */
@SpringBootTest
@AutoConfigureMockMvc
class DepartmentControllerTest {

    @Autowired
    MockMvc mockMvc;
    @Autowired
    DepartmentRepository departmentRepository;
    @Autowired
    EmployeeRepository employeeRepository;

    @BeforeEach
    void setUp() {
        // 테스트 간 인메모리 데이터가 섞이지 않도록 초기화
        employeeRepository.clear();
        departmentRepository.clear();
    }

    private void createDepartment(String name) throws Exception {
        mockMvc.perform(post("/api/departments")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"" + name + "\"}"))
                .andExpect(status().isCreated());
    }

    @Test
    @DisplayName("부서를 등록하면 201 과 발급된 ID 를 돌려준다")
    void createDepartment() throws Exception {
        mockMvc.perform(post("/api/departments")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"인사팀\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.name").value("인사팀"));
    }

    @Test
    @DisplayName("부서명이 비어 있으면 400 과 필드 오류를 돌려준다")
    void createDepartmentWithBlankName() throws Exception {
        mockMvc.perform(post("/api/departments")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"  \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.errors[0].field").value("name"));
    }

    @Test
    @DisplayName("부서 목록과 단건을 조회할 수 있다")
    void findDepartments() throws Exception {
        createDepartment("인사팀");
        createDepartment("재무팀");

        mockMvc.perform(get("/api/departments"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[1].name").value("재무팀"));

        mockMvc.perform(get("/api/departments/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("인사팀"));
    }

    @Test
    @DisplayName("없는 부서를 조회하면 404 를 돌려준다")
    void findMissingDepartment() throws Exception {
        mockMvc.perform(get("/api/departments/99"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    @DisplayName("부서 ID 가 숫자가 아니면 400 을 돌려준다")
    void invalidDepartmentIdType() throws Exception {
        mockMvc.perform(get("/api/departments/abc"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("TYPE_MISMATCH"));
    }

    @Test
    @DisplayName("부서명을 수정할 수 있다")
    void updateDepartment() throws Exception {
        createDepartment("인사팀");

        mockMvc.perform(put("/api/departments/1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"인사총무팀\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("인사총무팀"));
    }

    @Test
    @DisplayName("부서를 삭제하면 204 를 돌려주고 이후 조회 시 404 이다")
    void deleteDepartment() throws Exception {
        createDepartment("인사팀");

        mockMvc.perform(delete("/api/departments/1"))
                .andExpect(status().isNoContent());
        mockMvc.perform(get("/api/departments/1"))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("소속 사원이 있는 부서를 삭제하면 409 를 돌려준다")
    void deleteDepartmentWithEmployees() throws Exception {
        createDepartment("인사팀");
        mockMvc.perform(post("/api/employees")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"employeeNo":"E0001","name":"홍길동","departmentId":1,
                                 "basePay":3000000,"hireDate":"2024-03-01"}
                                """))
                .andExpect(status().isCreated());

        mockMvc.perform(delete("/api/departments/1"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("CONFLICT"));
    }
}
