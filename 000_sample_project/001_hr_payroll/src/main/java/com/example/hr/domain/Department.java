package com.example.hr.domain;

/**
 * 부서.
 *
 * @param id   부서 ID(저장소에서 자동 발급)
 * @param name 부서명
 */
public record Department(Long id, String name) {
}
