//! 하루치 근태 기록으로 근무시간을 계산하는 모듈 (교육용 단순화 규칙).
//!
//! 모든 시간 값은 "분" 단위 정수로 다룬다.

use crate::record::Record;

/// 정상근무 기준 시간: 하루 8시간.
pub const REGULAR_LIMIT: u32 = 8 * 60;
/// 지각 기준 시각: 09:00 (이 시각을 넘겨 출근하면 지각).
pub const LATE_AFTER: u32 = 9 * 60;
/// 야간근무 시작 시각: 22:00.
const NIGHT_START: u32 = 22 * 60;
/// 야간근무 종료 시각: 06:00.
const NIGHT_END: u32 = 6 * 60;
/// 하루의 분 수.
const DAY: u32 = 24 * 60;

/// 하루치 계산 결과.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct DailyResult {
    /// 휴게시간을 뺀 실근무 시간.
    pub worked: u32,
    /// 연장근무(평일 8시간 초과분).
    pub overtime: u32,
    /// 야간근무(22:00~06:00 구간에 걸친 시간).
    pub night: u32,
    /// 휴일근무(토·일 실근무 시간 전체).
    pub holiday: u32,
    /// 지각 여부.
    pub late: bool,
}

/// 퇴근시각이 출근시각보다 이르면 다음 날 퇴근(자정 넘김)으로 보고
/// 출근 시점부터 퇴근 시점까지의 체류 시간(분)을 돌려준다.
pub fn stay_minutes(clock_in: u32, clock_out: u32) -> u32 {
    if clock_out > clock_in {
        clock_out - clock_in
    } else {
        clock_out + DAY - clock_in
    }
}

/// 체류 시간에 따른 휴게시간: 4시간 이상 30분, 8시간 이상 1시간.
pub fn break_minutes(stay: u32) -> u32 {
    if stay >= 8 * 60 {
        60
    } else if stay >= 4 * 60 {
        30
    } else {
        0
    }
}

/// 두 구간 [a_start, a_end) 와 [b_start, b_end) 가 겹치는 길이.
fn overlap(a_start: u32, a_end: u32, b_start: u32, b_end: u32) -> u32 {
    let start = a_start.max(b_start);
    let end = a_end.min(b_end);
    end.saturating_sub(start)
}

/// 출근~퇴근 구간 중 22:00~06:00 에 속하는 시간(분).
///
/// 출근일 0시를 기준으로 시간축을 펴서 계산한다. 퇴근은 최대 다음 날이므로
/// 야간 구간은 [0:00,06:00), [22:00,다음날 06:00), [다음날 22:00,24:00) 세 개면 충분하다.
pub fn night_minutes(clock_in: u32, clock_out: u32) -> u32 {
    let start = clock_in;
    let end = clock_in + stay_minutes(clock_in, clock_out);
    let windows = [
        (0, NIGHT_END),
        (NIGHT_START, DAY + NIGHT_END),
        (DAY + NIGHT_START, 2 * DAY),
    ];
    windows
        .iter()
        .map(|&(w_start, w_end)| overlap(start, end, w_start, w_end))
        .sum()
}

/// 근태 기록 한 건을 계산한다.
///
/// - 실근무 = 체류 시간 - 휴게시간
/// - 평일: 실근무 중 8시간 초과분을 연장근무로 본다.
/// - 주말(출근일 기준 토·일): 실근무 전체를 휴일근무로 보고 연장·지각은 따지지 않는다.
/// - 야간근무는 요일과 상관없이 22:00~06:00 체류 시간으로 계산한다(휴게 공제 없음).
pub fn calculate(record: &Record) -> DailyResult {
    let stay = stay_minutes(record.clock_in, record.clock_out);
    let worked = stay - break_minutes(stay);
    let night = night_minutes(record.clock_in, record.clock_out);

    if record.date.is_weekend() {
        DailyResult {
            worked,
            overtime: 0,
            night,
            holiday: worked,
            late: false,
        }
    } else {
        DailyResult {
            worked,
            overtime: worked.saturating_sub(REGULAR_LIMIT),
            night,
            holiday: 0,
            late: record.clock_in > LATE_AFTER,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::record::parse_line;

    fn calc(line: &str) -> DailyResult {
        calculate(&parse_line(line).unwrap())
    }

    const H: u32 = 60;

    /// 휴게시간 경계값
    #[test]
    fn break_time_boundaries() {
        assert_eq!(break_minutes(4 * H - 1), 0);
        assert_eq!(break_minutes(4 * H), 30);
        assert_eq!(break_minutes(8 * H - 1), 30);
        assert_eq!(break_minutes(8 * H), 60);
        assert_eq!(break_minutes(12 * H), 60);
    }

    /// 평일 정시 근무는 연장 없음
    #[test]
    fn regular_weekday_has_no_overtime() {
        // 09:00~18:00 체류 9시간 - 휴게 1시간 = 8시간
        let r = calc("E1,2026-10-26,09:00,18:00");
        assert_eq!(r.worked, 8 * H);
        assert_eq!(r.overtime, 0);
        assert_eq!(r.night, 0);
        assert_eq!(r.holiday, 0);
        assert!(!r.late);
    }

    /// 연장근무 경계값
    #[test]
    fn overtime_boundary() {
        // 실근무 8시간 1분 → 연장 1분
        let r = calc("E1,2026-10-26,09:00,18:01");
        assert_eq!(r.worked, 8 * H + 1);
        assert_eq!(r.overtime, 1);
    }

    /// 지각 경계값
    #[test]
    fn late_boundary() {
        assert!(!calc("E1,2026-10-26,08:59,18:00").late);
        assert!(!calc("E1,2026-10-26,09:00,18:00").late);
        assert!(calc("E1,2026-10-26,09:01,18:00").late);
    }

    /// 야간근무 경계값
    #[test]
    fn night_boundaries() {
        // 22:00 정각 퇴근이면 야간 0분, 22:01 퇴근이면 1분
        assert_eq!(calc("E1,2026-10-26,13:00,22:00").night, 0);
        assert_eq!(calc("E1,2026-10-26,13:00,22:01").night, 1);
        // 새벽 출근: 05:00~14:00 중 05:00~06:00 1시간이 야간
        assert_eq!(calc("E1,2026-10-26,05:00,14:00").night, H);
    }

    /// 자정을 넘긴 퇴근
    #[test]
    fn clock_out_after_midnight() {
        // 22:00~다음날 07:00: 체류 9시간, 실근무 8시간, 야간 8시간(22~06시)
        let r = calc("E1,2026-10-27,22:00,07:00");
        assert_eq!(stay_minutes(22 * H, 7 * H), 9 * H);
        assert_eq!(r.worked, 8 * H);
        assert_eq!(r.overtime, 0);
        assert_eq!(r.night, 8 * H);
        assert!(r.late, "22시 출근도 09:00 이후이므로 지각으로 센다");
    }

    /// 자정 정각 퇴근
    #[test]
    fn clock_out_at_midnight() {
        // 18:00~00:00 → 체류 6시간, 야간 2시간
        let r = calc("E1,2026-10-26,18:00,00:00");
        assert_eq!(r.worked, 6 * H - 30);
        assert_eq!(r.night, 2 * H);
    }

    /// 거의 하루 종일 근무
    #[test]
    fn almost_full_day_shift() {
        // 06:00~다음날 05:59 → 체류 23시간 59분, 야간은 22:00~05:59 = 7시간 59분
        let r = calc("E1,2026-10-26,06:00,05:59");
        assert_eq!(r.worked, 23 * H + 59 - 60);
        assert_eq!(r.night, 7 * H + 59);
    }

    /// 주말은 휴일근무
    #[test]
    fn night_window_on_next_evening() {
        // 22:30 출근 → 다음 날 22:10 퇴근. 첫 밤 7:30 + 다음 날 22:00~22:10 의 10분.
        // 세 번째 야간 구간 [다음날 22:00, 24:00) 이 없으면 10분이 빠진다.
        assert_eq!(calc("E1,2026-10-26,22:30,22:10").night, 7 * H + 40);
    }

    #[test]
    fn long_weekend_shift_has_no_overtime() {
        // 주말 10시간 근무: 휴일근무로만 세고 연장은 0 이어야 한다(중복 집계 방지).
        let r = calc("E1,2026-10-31,08:00,19:00");
        assert_eq!(r.worked, 10 * H);
        assert_eq!(r.holiday, 10 * H);
        assert_eq!(r.overtime, 0);
    }

    #[test]
    fn weekend_is_holiday_work() {
        // 2026-10-31 토요일 10:00~15:00 → 체류 5시간, 실근무 4시간 30분
        let r = calc("E1,2026-10-31,10:00,15:00");
        assert_eq!(r.worked, 4 * H + 30);
        assert_eq!(r.holiday, 4 * H + 30);
        assert_eq!(r.overtime, 0);
        assert!(!r.late, "주말에는 지각을 세지 않는다");
    }

    /// 일요일 밤 자정 넘김
    #[test]
    fn sunday_night_over_midnight() {
        // 2026-11-01 일요일 20:00~02:00 → 체류 6시간, 실근무 5시간 30분, 야간 4시간
        let r = calc("E1,2026-11-01,20:00,02:00");
        assert_eq!(r.worked, 5 * H + 30);
        assert_eq!(r.holiday, 5 * H + 30);
        assert_eq!(r.night, 4 * H);
    }

    /// 금요일 밤에 시작해 토요일에 끝나면 평일로 본다
    #[test]
    fn friday_night_into_saturday_counts_as_weekday() {
        // 출근일 기준으로 요일을 판단한다.
        let r = calc("E1,2026-10-30,20:00,04:00");
        assert_eq!(r.holiday, 0);
        assert_eq!(r.worked, 7 * H);
    }
}
