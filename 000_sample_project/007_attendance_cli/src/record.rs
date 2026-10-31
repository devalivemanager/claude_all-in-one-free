//! CSV 한 줄을 근태 기록(`Record`)으로 바꾸는 파싱 모듈.
//!
//! 외부 크레이트 없이 날짜·시각을 직접 파싱한다.

use std::fmt;

/// 날짜(연, 월, 일).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Date {
    pub year: i32,
    pub month: u32,
    pub day: u32,
}

impl Date {
    /// 1970-01-01 기준 경과 일수 (Howard Hinnant 의 days_from_civil 알고리즘).
    fn days_since_epoch(self) -> i64 {
        let y = if self.month <= 2 {
            self.year - 1
        } else {
            self.year
        } as i64;
        let m = self.month as i64;
        let d = self.day as i64;
        let era = if y >= 0 { y } else { y - 399 } / 400;
        let yoe = y - era * 400;
        let mp = (m + 9) % 12; // 3월=0 ... 2월=11
        let doy = (153 * mp + 2) / 5 + d - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        era * 146_097 + doe - 719_468
    }

    /// 요일 번호. 0=월요일 ... 6=일요일.
    pub fn weekday(self) -> u32 {
        // 1970-01-01 은 목요일(3)이다.
        ((self.days_since_epoch() + 3).rem_euclid(7)) as u32
    }

    /// 토요일 또는 일요일이면 true.
    pub fn is_weekend(self) -> bool {
        self.weekday() >= 5
    }
}

impl fmt::Display for Date {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:04}-{:02}-{:02}", self.year, self.month, self.day)
    }
}

/// 근태 기록 한 건. 시각은 자정 기준 분(0~1439)으로 저장한다.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Record {
    pub employee_id: String,
    pub date: Date,
    pub clock_in: u32,
    pub clock_out: u32,
}

/// 파싱 오류 종류.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    ColumnCount(usize),
    EmptyEmployeeId,
    InvalidDate(String),
    InvalidTime(String),
    SameInOut,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::ColumnCount(n) => write!(f, "열 개수가 4개가 아닙니다 ({n}개)"),
            ParseError::EmptyEmployeeId => write!(f, "사번이 비어 있습니다"),
            ParseError::InvalidDate(s) => write!(f, "날짜 형식이 잘못되었습니다: '{s}'"),
            ParseError::InvalidTime(s) => write!(f, "시각 형식이 잘못되었습니다: '{s}'"),
            ParseError::SameInOut => write!(f, "출근시각과 퇴근시각이 같습니다"),
        }
    }
}

fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn days_in_month(year: i32, month: u32) -> u32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap_year(year) => 29,
        2 => 28,
        _ => 0,
    }
}

/// "YYYY-MM-DD" 형식의 날짜를 파싱한다. 존재하지 않는 날짜(2월 30일 등)는 오류.
pub fn parse_date(text: &str) -> Result<Date, ParseError> {
    let err = || ParseError::InvalidDate(text.to_string());
    let parts: Vec<&str> = text.split('-').collect();
    if parts.len() != 3 || parts[0].len() != 4 || parts[1].len() != 2 || parts[2].len() != 2 {
        return Err(err());
    }
    let year: i32 = parts[0].parse().map_err(|_| err())?;
    let month: u32 = parts[1].parse().map_err(|_| err())?;
    let day: u32 = parts[2].parse().map_err(|_| err())?;
    if !(1..=12).contains(&month) || day == 0 || day > days_in_month(year, month) {
        return Err(err());
    }
    Ok(Date { year, month, day })
}

/// "HH:MM" (또는 "H:MM") 형식의 시각을 자정 기준 분으로 파싱한다.
pub fn parse_time(text: &str) -> Result<u32, ParseError> {
    let err = || ParseError::InvalidTime(text.to_string());
    let (h, m) = text.split_once(':').ok_or_else(err)?;
    let all_digits = |s: &str| !s.is_empty() && s.chars().all(|c| c.is_ascii_digit());
    if !all_digits(h) || h.len() > 2 || !all_digits(m) || m.len() != 2 {
        return Err(err());
    }
    let hour: u32 = h.parse().map_err(|_| err())?;
    let minute: u32 = m.parse().map_err(|_| err())?;
    if hour > 23 || minute > 59 {
        return Err(err());
    }
    Ok(hour * 60 + minute)
}

/// CSV 한 줄(사번,날짜,출근시각,퇴근시각)을 파싱한다.
pub fn parse_line(line: &str) -> Result<Record, ParseError> {
    let fields: Vec<&str> = line.split(',').map(str::trim).collect();
    if fields.len() != 4 {
        return Err(ParseError::ColumnCount(fields.len()));
    }
    if fields[0].is_empty() {
        return Err(ParseError::EmptyEmployeeId);
    }
    let date = parse_date(fields[1])?;
    let clock_in = parse_time(fields[2])?;
    let clock_out = parse_time(fields[3])?;
    if clock_in == clock_out {
        return Err(ParseError::SameInOut);
    }
    Ok(Record {
        employee_id: fields[0].to_string(),
        date,
        clock_in,
        clock_out,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 정상 행을 파싱한다
    #[test]
    fn parses_valid_line() {
        let r = parse_line("E001, 2026-10-26, 08:55, 18:00").unwrap();
        assert_eq!(r.employee_id, "E001");
        assert_eq!(
            r.date,
            Date {
                year: 2026,
                month: 10,
                day: 26
            }
        );
        assert_eq!(r.clock_in, 8 * 60 + 55);
        assert_eq!(r.clock_out, 18 * 60);
    }

    /// 한 자리 시도 허용한다
    #[test]
    fn accepts_single_digit_hour() {
        assert_eq!(parse_time("9:30"), Ok(570));
    }

    /// 열 개수가 틀리면 오류
    #[test]
    fn rejects_wrong_column_count() {
        assert_eq!(
            parse_line("E001,2026-10-26,08:00"),
            Err(ParseError::ColumnCount(3))
        );
        assert_eq!(
            parse_line("E001,2026-10-26,08:00,18:00,extra"),
            Err(ParseError::ColumnCount(5))
        );
    }

    /// 사번이 비면 오류
    #[test]
    fn rejects_empty_employee_id() {
        assert_eq!(
            parse_line(",2026-10-26,08:00,18:00"),
            Err(ParseError::EmptyEmployeeId)
        );
    }

    /// 잘못된 날짜는 오류
    #[test]
    fn rejects_invalid_date() {
        assert!(matches!(
            parse_date("2026-02-30"),
            Err(ParseError::InvalidDate(_))
        ));
        assert!(matches!(
            parse_date("2026-13-01"),
            Err(ParseError::InvalidDate(_))
        ));
        assert!(matches!(
            parse_date("2026/10/26"),
            Err(ParseError::InvalidDate(_))
        ));
        assert!(matches!(
            parse_date("26-10-26"),
            Err(ParseError::InvalidDate(_))
        ));
        assert!(matches!(
            parse_date("2026-1x-26"),
            Err(ParseError::InvalidDate(_))
        ));
    }

    /// 윤년 2월 29일은 허용한다
    #[test]
    fn accepts_leap_day_only_in_leap_year() {
        assert!(parse_date("2024-02-29").is_ok());
        assert!(parse_date("2026-02-29").is_err());
        assert!(parse_date("2000-02-29").is_ok());
        assert!(parse_date("1900-02-29").is_err());
    }

    /// 잘못된 시각은 오류
    #[test]
    fn rejects_invalid_time() {
        for bad in [
            "24:00", "25:00", "08:60", "0800", "08:5", "ab:cd", "", "-1:00", "123:00",
        ] {
            assert!(
                matches!(parse_time(bad), Err(ParseError::InvalidTime(_))),
                "'{bad}' 는 오류여야 함"
            );
        }
    }

    /// 출퇴근 시각이 같으면 오류
    #[test]
    fn rejects_same_in_and_out() {
        assert_eq!(
            parse_line("E001,2026-10-26,09:00,09:00"),
            Err(ParseError::SameInOut)
        );
    }

    /// 요일을 계산한다
    #[test]
    fn computes_weekday() {
        // 2026-10-26 은 월요일, 2026-10-31 은 토요일, 2026-11-01 은 일요일.
        assert_eq!(parse_date("2026-10-26").unwrap().weekday(), 0);
        assert!(!parse_date("2026-10-30").unwrap().is_weekend());
        assert!(parse_date("2026-10-31").unwrap().is_weekend());
        assert!(parse_date("2026-11-01").unwrap().is_weekend());
        // 1970-01-01 은 목요일, 2000-01-01 은 토요일.
        assert_eq!(parse_date("1970-01-01").unwrap().weekday(), 3);
        assert_eq!(parse_date("2000-01-01").unwrap().weekday(), 5);
    }
}
