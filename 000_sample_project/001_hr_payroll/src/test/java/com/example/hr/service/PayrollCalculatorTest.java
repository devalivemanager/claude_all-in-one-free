package com.example.hr.service;

import com.example.hr.dto.PayrollResult;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 급여 계산기 단위 테스트. 스프링 컨텍스트 없이 순수 계산만 검증한다.
 */
class PayrollCalculatorTest {

    private final PayrollCalculator calculator = new PayrollCalculator();

    private static BigDecimal won(long amount) {
        return BigDecimal.valueOf(amount);
    }

    @Test
    @DisplayName("기본급 300만원 + 식대 20만원이면 모든 공제 항목과 실수령액이 기대값과 같다")
    void calculatesTypicalPayroll() {
        PayrollResult r = calculator.calculate(won(3_000_000), won(200_000), won(0));

        assertThat(r.grossPay()).isEqualByComparingTo("3200000");
        assertThat(r.nonTaxableAmount()).isEqualByComparingTo("200000");
        assertThat(r.taxableAmount()).isEqualByComparingTo("3000000");
        assertThat(r.nationalPension()).isEqualByComparingTo("135000");       // 3,000,000 × 4.5%
        assertThat(r.healthInsurance()).isEqualByComparingTo("106350");       // 3,000,000 × 3.545%
        assertThat(r.longTermCareInsurance()).isEqualByComparingTo("13772");  // 106,350 × 12.95% = 13,772.325
        assertThat(r.employmentInsurance()).isEqualByComparingTo("27000");    // 3,000,000 × 0.9%
        assertThat(r.incomeTax()).isEqualByComparingTo("38800");              // (300만-106만) × 2%
        assertThat(r.localIncomeTax()).isEqualByComparingTo("3880");          // 38,800 × 10%
        assertThat(r.totalDeduction()).isEqualByComparingTo("324802");
        assertThat(r.netPay()).isEqualByComparingTo("2875198");
    }

    @Test
    @DisplayName("모든 공제 항목은 원 단위 미만을 절사한다")
    void truncatesBelowOneWon() {
        // 과세 대상액 1,234,567원 (식대 없음)
        PayrollResult r = calculator.calculate(won(1_234_567), null, null);

        assertThat(r.nationalPension()).isEqualByComparingTo("55555");       // 55,555.515
        assertThat(r.healthInsurance()).isEqualByComparingTo("43765");       // 43,765.40015
        assertThat(r.longTermCareInsurance()).isEqualByComparingTo("5667");  // 43,765 × 12.95% = 5,667.5675
        assertThat(r.employmentInsurance()).isEqualByComparingTo("11111");   // 11,111.103
        assertThat(r.incomeTax()).isEqualByComparingTo("3491");              // 174,567 × 2% = 3,491.34
        assertThat(r.localIncomeTax()).isEqualByComparingTo("349");          // 349.1
        assertThat(r.netPay().scale()).isZero();
    }

    @Test
    @DisplayName("장기요양보험료는 과세 대상액이 아니라 절사된 건강보험료를 기준으로 계산한다")
    void longTermCareIsBasedOnHealthInsurance() {
        PayrollResult r = calculator.calculate(won(2_000_000), won(0), won(0));

        assertThat(r.healthInsurance()).isEqualByComparingTo("70900");
        assertThat(r.longTermCareInsurance()).isEqualByComparingTo("9181"); // 70,900 × 12.95% = 9,181.55
    }

    @Test
    @DisplayName("장기요양보험료는 건강보험료를 먼저 절사한 뒤 계산한다 (절사를 한 번 건너뛰면 1원 차이)")
    void longTermCareUsesTruncatedHealthInsurance() {
        // 위 시험은 건강보험료가 딱 떨어지는 금액(70,900원)이라 중간 절사를 빼먹어도 통과한다.
        // 건강보험료에 원 미만이 생기는 금액으로 중간 절사 여부를 구분한다.
        PayrollResult r = calculator.calculate(won(1_000_050), won(0), won(0));

        assertThat(r.healthInsurance()).isEqualByComparingTo("35451");      // 35,451.7725 → 절사
        assertThat(r.longTermCareInsurance()).isEqualByComparingTo("4590"); // 35,451 × 12.95% = 4,590.9045
        // 절사 없이 1,000,050 × 3.545% × 12.95% = 4,591.005... 로 계산하면 4,591원이 되어 틀린다.
    }

    @Test
    @DisplayName("기본급과 수당이 모두 0이면 모든 금액이 0이다")
    void zeroPay() {
        PayrollResult r = calculator.calculate(won(0), won(0), won(0));

        assertThat(r.grossPay()).isEqualByComparingTo("0");
        assertThat(r.totalDeduction()).isEqualByComparingTo("0");
        assertThat(r.netPay()).isEqualByComparingTo("0");
    }

    @Test
    @DisplayName("수당이 null 이면 0원으로 취급한다")
    void nullAllowancesAreZero() {
        PayrollResult r = calculator.calculate(won(2_500_000), null, null);

        assertThat(r.mealAllowance()).isEqualByComparingTo("0");
        assertThat(r.otherAllowance()).isEqualByComparingTo("0");
        assertThat(r.grossPay()).isEqualByComparingTo("2500000");
    }

    @Test
    @DisplayName("기타 수당은 전액 과세 대상에 포함된다")
    void otherAllowanceIsTaxable() {
        PayrollResult r = calculator.calculate(won(2_000_000), won(0), won(300_000));

        assertThat(r.nonTaxableAmount()).isEqualByComparingTo("0");
        assertThat(r.taxableAmount()).isEqualByComparingTo("2300000");
    }

    @Nested
    @DisplayName("식대 비과세 한도(20만원) 경계값")
    class MealAllowanceBoundary {

        @ParameterizedTest(name = "식대 {0}원 → 비과세 {1}원, 과세 대상 {2}원")
        @CsvSource({
                "0,       0,      2000000",
                "199999,  199999, 2000000",
                "200000,  200000, 2000000",
                "200001,  200000, 2000001",
                "300000,  200000, 2100000"
        })
        @DisplayName("식대는 20만원까지만 비과세이고 초과분은 과세된다")
        void mealNonTaxableLimit(long meal, long expectedNonTaxable, long expectedTaxable) {
            PayrollResult r = calculator.calculate(won(2_000_000), won(meal), won(0));

            assertThat(r.nonTaxableAmount()).isEqualByComparingTo(won(expectedNonTaxable));
            assertThat(r.taxableAmount()).isEqualByComparingTo(won(expectedTaxable));
            assertThat(r.grossPay()).isEqualByComparingTo(won(2_000_000 + meal));
        }
    }

    @Nested
    @DisplayName("교육용 누진 소득세 구간 경계값")
    class IncomeTaxBoundary {

        @ParameterizedTest(name = "과세 대상 {0}원 → 소득세 {1}원")
        @CsvSource({
                "0,        0",
                "1060000,  0",       // 0% 구간 상한
                "1060001,  0",       // 0.02원 → 절사
                "1060050,  1",       // 50 × 2% = 1
                "3000000,  38800",   // 1,940,000 × 2%
                "3000001,  38800",   // 0.04원 → 절사
                "3000025,  38801",   // 25 × 4% = 1
                "5000000,  118800",  // 38,800 + 2,000,000 × 4%
                "10000000, 518800",  // 118,800 + 5,000,000 × 8%
                "10000100, 518815"   // 518,800 + 100 × 15%
        })
        @DisplayName("구간별 초과분에만 해당 세율을 적용한다")
        void progressiveIncomeTax(long taxable, long expectedTax) {
            assertThat(calculator.calculateIncomeTax(won(taxable))).isEqualByComparingTo(won(expectedTax));
        }

        @Test
        @DisplayName("지방소득세는 소득세의 10%를 절사한 값이다")
        void localIncomeTaxIsTenPercentOfIncomeTax() {
            PayrollResult r = calculator.calculate(won(10_000_100), won(0), won(0));

            assertThat(r.incomeTax()).isEqualByComparingTo("518815");
            assertThat(r.localIncomeTax()).isEqualByComparingTo("51881"); // 51,881.5 → 절사
        }
    }
}
