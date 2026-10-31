package com.example.hr.service;

import com.example.hr.config.PayrollRates;
import com.example.hr.config.PayrollRates.TaxBracket;
import com.example.hr.dto.PayrollResult;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/**
 * 월 급여 계산기. 저장소에 의존하지 않는 순수 계산 로직이라 단위 테스트가 쉽다.
 * <p>
 * 계산 순서:
 * <ol>
 *   <li>지급 총액 = 기본급 + 식대 + 기타 수당</li>
 *   <li>비과세액 = min(식대, 20만원), 과세 대상액 = 지급 총액 - 비과세액</li>
 *   <li>4대 보험료 = 과세 대상액 × 요율 (장기요양은 건강보험료 × 요율)</li>
 *   <li>소득세 = 과세 대상액에 교육용 누진세율 적용, 지방소득세 = 소득세 × 10%</li>
 *   <li>실수령액 = 지급 총액 - 공제 합계</li>
 * </ol>
 * 각 공제 항목은 계산 직후 원 단위 미만을 절사한다.
 */
@Component
public class PayrollCalculator {

    public PayrollResult calculate(BigDecimal basePay, BigDecimal mealAllowance, BigDecimal otherAllowance) {
        BigDecimal meal = orZero(mealAllowance);
        BigDecimal other = orZero(otherAllowance);

        BigDecimal grossPay = basePay.add(meal).add(other);
        BigDecimal nonTaxable = meal.min(PayrollRates.MEAL_NON_TAXABLE_LIMIT);
        BigDecimal taxable = grossPay.subtract(nonTaxable);

        BigDecimal nationalPension = truncate(taxable.multiply(PayrollRates.NATIONAL_PENSION_RATE));
        BigDecimal healthInsurance = truncate(taxable.multiply(PayrollRates.HEALTH_INSURANCE_RATE));
        BigDecimal longTermCare = truncate(healthInsurance.multiply(PayrollRates.LONG_TERM_CARE_RATE));
        BigDecimal employmentInsurance = truncate(taxable.multiply(PayrollRates.EMPLOYMENT_INSURANCE_RATE));
        BigDecimal incomeTax = calculateIncomeTax(taxable);
        BigDecimal localIncomeTax = truncate(incomeTax.multiply(PayrollRates.LOCAL_INCOME_TAX_RATE));

        BigDecimal totalDeduction = nationalPension
                .add(healthInsurance)
                .add(longTermCare)
                .add(employmentInsurance)
                .add(incomeTax)
                .add(localIncomeTax);
        BigDecimal netPay = grossPay.subtract(totalDeduction);

        return new PayrollResult(
                truncate(basePay), truncate(meal), truncate(other),
                truncate(grossPay), truncate(nonTaxable), truncate(taxable),
                nationalPension, healthInsurance, longTermCare, employmentInsurance,
                incomeTax, localIncomeTax, totalDeduction, truncate(netPay));
    }

    /**
     * 교육용 누진세 계산. 각 구간에 속하는 금액에만 해당 구간 세율을 곱해 더한다.
     * 예) 과세 400만원 → (300만-106만)×2% + (400만-300만)×4%
     */
    BigDecimal calculateIncomeTax(BigDecimal taxable) {
        List<TaxBracket> brackets = PayrollRates.INCOME_TAX_BRACKETS;
        BigDecimal tax = BigDecimal.ZERO;
        for (int i = 0; i < brackets.size(); i++) {
            BigDecimal lower = brackets.get(i).lowerBound();
            if (taxable.compareTo(lower) <= 0) {
                break;
            }
            boolean isLast = i == brackets.size() - 1;
            BigDecimal upper = isLast ? taxable : taxable.min(brackets.get(i + 1).lowerBound());
            tax = tax.add(upper.subtract(lower).multiply(brackets.get(i).rate()));
        }
        return truncate(tax);
    }

    /** 원 단위 미만 절사 */
    private static BigDecimal truncate(BigDecimal amount) {
        return amount.setScale(0, RoundingMode.DOWN);
    }

    private static BigDecimal orZero(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }
}
