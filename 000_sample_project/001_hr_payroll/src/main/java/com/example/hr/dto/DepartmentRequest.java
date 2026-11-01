package com.example.hr.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 부서 등록·수정 요청.
 */
public record DepartmentRequest(
        @NotBlank(message = "부서명은 필수입니다.")
        @Size(max = 50, message = "부서명은 50자 이하여야 합니다.")
        String name
) {
}
