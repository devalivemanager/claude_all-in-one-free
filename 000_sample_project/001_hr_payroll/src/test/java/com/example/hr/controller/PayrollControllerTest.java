package com.example.hr.controller;

import com.example.hr.domain.Employee;
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

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 월 급여 계산 API MockMvc 테스트.
 */
@SpringBootTest
@AutoConfigureMockMvc
class PayrollControllerTest {

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
        Long deptId = departmentRepository.create("개발팀").id();
        employeeRepository.save(new Employee("E0001", "홍길동", deptId,
                new BigDecimal("3000000"), LocalDate.of(2024, 3, 15)));
    }

    private ResultActions calculate(String json) throws Exception {
        return mockMvc.perform(post("/api/payrolls/calculate")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json));
    }

    @Test
    @DisplayName("사번과 급여 월을 주면 월 급여 명세를 계산해 돌려준다")
    void calculatePayroll() throws Exception {
        calculate("""
                {"employeeNo":"E0001","payMonth":"2026-10","mealAllowance":200000,"otherAllowance":0}
                """)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.employeeNo").value("E0001"))
                .andExpect(jsonPath("$.employeeName").value("홍길동"))
                .andExpect(jsonPath("$.departmentName").value("개발팀"))
                .andExpect(jsonPath("$.payMonth").value("2026-10"))
                .andExpect(jsonPath("$.payroll.grossPay").value(3200000))
                .andExpect(jsonPath("$.payroll.taxableAmount").value(3000000))
                .andExpect(jsonPath("$.payroll.nationalPension").value(135000))
                .andExpect(jsonPath("$.payroll.healthInsurance").value(106350))
                .andExpect(jsonPath("$.payroll.longTermCareInsurance").value(13772))
                .andExpect(jsonPath("$.payroll.employmentInsurance").value(27000))
                .andExpect(jsonPath("$.payroll.incomeTax").value(38800))
                .andExpect(jsonPath("$.payroll.localIncomeTax").value(3880))
                .andExpect(jsonPath("$.payroll.totalDeduction").value(324802))
                .andExpect(jsonPath("$.payroll.netPay").value(2875198));
    }

    @Test
    @DisplayName("수당을 생략하면 0원으로 계산한다")
    void calculateWithoutAllowances() throws Exception {
        calculate("""
                {"employeeNo":"E0001","payMonth":"2026-10"}
                """)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.payroll.grossPay").value(3000000))
                .andExpect(jsonPath("$.payroll.nonTaxableAmount").value(0));
    }

    @Test
    @DisplayName("입사한 달의 급여는 계산할 수 있다(경계값)")
    void calculateInHireMonth() throws Exception {
        calculate("""
                {"employeeNo":"E0001","payMonth":"2024-03"}
                """)
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("입사월 이전의 급여를 요청하면 400 을 돌려준다")
    void calculateBeforeHireMonth() throws Exception {
        calculate("""
                {"employeeNo":"E0001","payMonth":"2024-02"}
                """)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("BAD_REQUEST"));
    }

    @Test
    @DisplayName("없는 사번이면 404 를 돌려준다")
    void calculateForMissingEmployee() throws Exception {
        calculate("""
                {"employeeNo":"E9999","payMonth":"2026-10"}
                """)
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("수당이 음수이거나 필수값이 없으면 400 과 필드 오류를 돌려준다")
    void calculateWithInvalidRequest() throws Exception {
        calculate("""
                {"mealAllowance":-1}
                """)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.errors.length()").value(3));
    }

    @Test
    @DisplayName("급여 월 형식이 yyyy-MM 이 아니면 400 MALFORMED_REQUEST 를 돌려준다")
    void calculateWithMalformedPayMonth() throws Exception {
        calculate("""
                {"employeeNo":"E0001","payMonth":"2026/10"}
                """)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"));
    }
}
