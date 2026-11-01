package com.example.hr.config;

import java.math.BigDecimal;
import java.util.List;

/**
 * 급여 계산에 쓰이는 모든 요율과 한도를 모아 둔 상수 클래스.
 * <p>
 * 요율이 바뀌면 이 파일만 고치면 된다.
 * 소득세 구간은 실제 근로소득 간이세액표가 아닌 교육용 단순화 누진세율이다.
 */
public final class PayrollRates {

    private PayrollRates() {
    }

    /** 식대 비과세 월 한도: 20만원 */
    public static final BigDecimal MEAL_NON_TAXABLE_LIMIT = new BigDecimal("200000");

    /** 국민연금 근로자 부담률: 4.5% */
    public static final BigDecimal NATIONAL_PENSION_RATE = new BigDecimal("0.045");

    /** 건강보험 근로자 부담률: 3.545% */
    public static final BigDecimal HEALTH_INSURANCE_RATE = new BigDecimal("0.03545");

    /** 장기요양보험료율: 건강보험료의 12.95% */
    public static final BigDecimal LONG_TERM_CARE_RATE = new BigDecimal("0.1295");

    /** 고용보험 근로자 부담률: 0.9% */
    public static final BigDecimal EMPLOYMENT_INSURANCE_RATE = new BigDecimal("0.009");

    /** 지방소득세율: 소득세의 10% */
    public static final BigDecimal LOCAL_INCOME_TAX_RATE = new BigDecimal("0.1");

    /**
     * 교육용 간이 누진세율 구간 (월 과세 급여 기준).
     * lowerBound 를 초과하는 금액 중 다음 구간 하한까지의 부분에 rate 를 적용한다.
     */
    public static final List<TaxBracket> INCOME_TAX_BRACKETS = List.of(
            new TaxBracket(new BigDecimal("0"), new BigDecimal("0.00")),
            new TaxBracket(new BigDecimal("1060000"), new BigDecimal("0.02")),
            new TaxBracket(new BigDecimal("3000000"), new BigDecimal("0.04")),
            new TaxBracket(new BigDecimal("5000000"), new BigDecimal("0.08")),
            new TaxBracket(new BigDecimal("10000000"), new BigDecimal("0.15"))
    );

    /**
     * 누진세 구간 하나.
     *
     * @param lowerBound 구간 하한(이 금액 초과분부터 적용)
     * @param rate       구간 세율
     */
    public record TaxBracket(BigDecimal lowerBound, BigDecimal rate) {
    }
}
