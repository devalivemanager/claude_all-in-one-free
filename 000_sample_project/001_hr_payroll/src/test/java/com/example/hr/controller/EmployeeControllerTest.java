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
import org.springframework.test.web.servlet.ResultActions;

import java.time.LocalDate;

import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 사원 API MockMvc 테스트.
 */
@SpringBootTest
@AutoConfigureMockMvc
class EmployeeControllerTest {

    @Autowired
    MockMvc mockMvc;
    @Autowired
    DepartmentRepository departmentRepository;
    @Autowired
    EmployeeRepository employeeRepository;

    @BeforeEach
    void setUp() {
        employeeRepository.clear();
        departmentRepository.clear();
        departmentRepository.create("인사팀"); // id = 1
    }

    private ResultActions postEmployee(String json) throws Exception {
        return mockMvc.perform(post("/api/employees")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json));
    }

    private static final String VALID_EMPLOYEE = """
            {"employeeNo":"E0001","name":"홍길동","departmentId":1,
             "basePay":3000000,"hireDate":"2024-03-01"}
            """;

    @Test
    @DisplayName("사원을 등록하면 201 과 등록된 사원 정보를 돌려준다")
    void createEmployee() throws Exception {
        postEmployee(VALID_EMPLOYEE)
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.employeeNo").value("E0001"))
                .andExpect(jsonPath("$.name").value("홍길동"))
                .andExpect(jsonPath("$.departmentId").value(1))
                .andExpect(jsonPath("$.basePay").value(3000000))
                .andExpect(jsonPath("$.hireDate").value("2024-03-01"));
    }

    @Test
    @DisplayName("필수값 누락·형식 오류가 있으면 400 과 모든 필드 오류를 돌려준다")
    void createEmployeeWithInvalidFields() throws Exception {
        postEmployee("""
                {"employeeNo":"123","name":"","basePay":-1}
                """)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.errors[*].field",
                        containsInAnyOrder("employeeNo", "name", "departmentId", "basePay", "hireDate")));
    }

    @Test
    @DisplayName("기본급에 원 단위 미만 소수가 있으면 400 을 돌려준다")
    void createEmployeeWithFractionalBasePay() throws Exception {
        postEmployee("""
                {"employeeNo":"E0001","name":"홍길동","departmentId":1,
                 "basePay":3000000.5,"hireDate":"2024-03-01"}
                """)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("basePay"));
    }

    @Test
    @DisplayName("입사일이 미래이면 400 을 돌려준다")
    void createEmployeeWithFutureHireDate() throws Exception {
        String future = LocalDate.now().plusDays(1).toString();
        postEmployee("""
                {"employeeNo":"E0001","name":"홍길동","departmentId":1,
                 "basePay":3000000,"hireDate":"%s"}
                """.formatted(future))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("hireDate"));
    }

    @Test
    @DisplayName("날짜 형식이 잘못되면 400 MALFORMED_REQUEST 를 돌려준다")
    void createEmployeeWithMalformedDate() throws Exception {
        postEmployee("""
                {"employeeNo":"E0001","name":"홍길동","departmentId":1,
                 "basePay":3000000,"hireDate":"2024/03/01"}
                """)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"));
    }

    @Test
    @DisplayName("같은 사번으로 다시 등록하면 409 를 돌려준다")
    void createDuplicateEmployee() throws Exception {
        postEmployee(VALID_EMPLOYEE).andExpect(status().isCreated());

        postEmployee(VALID_EMPLOYEE)
                .andExpect(status().isConflict());
    }

    @Test
    @DisplayName("존재하지 않는 부서로 등록하면 404 를 돌려준다")
    void createEmployeeWithMissingDepartment() throws Exception {
        postEmployee("""
                {"employeeNo":"E0001","name":"홍길동","departmentId":99,
                 "basePay":3000000,"hireDate":"2024-03-01"}
                """)
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("사원 목록과 단건을 조회할 수 있다")
    void findEmployees() throws Exception {
        postEmployee(VALID_EMPLOYEE).andExpect(status().isCreated());

        mockMvc.perform(get("/api/employees"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)));
        mockMvc.perform(get("/api/employees/E0001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("홍길동"));
        mockMvc.perform(get("/api/employees/E9999"))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("사원 정보를 수정할 수 있다")
    void updateEmployee() throws Exception {
        postEmployee(VALID_EMPLOYEE).andExpect(status().isCreated());

        mockMvc.perform(put("/api/employees/E0001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"홍길동","departmentId":1,
                                 "basePay":3500000,"hireDate":"2024-03-01"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.basePay").value(3500000));
    }

    @Test
    @DisplayName("사원을 삭제하면 204 를 돌려주고 이후 조회 시 404 이다")
    void deleteEmployee() throws Exception {
        postEmployee(VALID_EMPLOYEE).andExpect(status().isCreated());

        mockMvc.perform(delete("/api/employees/E0001"))
                .andExpect(status().isNoContent());
        mockMvc.perform(get("/api/employees/E0001"))
                .andExpect(status().isNotFound());
    }
}
