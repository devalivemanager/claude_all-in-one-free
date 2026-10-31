package com.example.hr.controller;

import com.example.hr.dto.PayrollRequest;
import com.example.hr.dto.PayrollResponse;
import com.example.hr.service.PayrollService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 월 급여 계산 API. 계산 결과는 저장하지 않고 바로 돌려준다.
 */
@RestController
@RequestMapping("/api/payrolls")
public class PayrollController {

    private final PayrollService payrollService;

    public PayrollController(PayrollService payrollService) {
        this.payrollService = payrollService;
    }

    @PostMapping("/calculate")
    public PayrollResponse calculate(@Valid @RequestBody PayrollRequest request) {
        return payrollService.calculate(request);
    }
}
