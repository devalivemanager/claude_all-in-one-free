//! 사원별 집계와 표 출력 모듈.

use std::collections::BTreeMap;

use crate::calc::DailyResult;

/// 사원 한 명의 집계 결과.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Summary {
    pub work_days: u32,
    pub worked: u32,
    pub overtime: u32,
    pub night: u32,
    pub holiday: u32,
    pub late_count: u32,
}

impl Summary {
    /// 하루치 결과를 누적한다.
    pub fn add(&mut self, day: &DailyResult) {
        self.work_days += 1;
        self.worked += day.worked;
        self.overtime += day.overtime;
        self.night += day.night;
        self.holiday += day.holiday;
        if day.late {
            self.late_count += 1;
        }
    }
}

/// 분을 "시간:분" 문자열로 바꾼다. 예: 90 → "1:30".
pub fn format_minutes(minutes: u32) -> String {
    format!("{}:{:02}", minutes / 60, minutes % 60)
}

/// 터미널 표시 폭. 한글 등 넓은 문자는 2칸으로 센다(단순화).
fn display_width(text: &str) -> usize {
    text.chars().map(|c| if c.is_ascii() { 1 } else { 2 }).sum()
}

/// 표시 폭 기준으로 오른쪽 정렬한다.
fn pad_left(text: &str, width: usize) -> String {
    let pad = width.saturating_sub(display_width(text));
    format!("{}{}", " ".repeat(pad), text)
}

/// 사원별 집계 표를 문자열로 만든다. 사번 순으로 정렬된다.
pub fn render_table(summaries: &BTreeMap<String, Summary>) -> String {
    let headers = ["사번", "근무일수", "총근무", "연장", "야간", "휴일", "지각"];
    let mut rows: Vec<[String; 7]> = Vec::new();
    for (id, s) in summaries {
        rows.push([
            id.clone(),
            format!("{}일", s.work_days),
            format_minutes(s.worked),
            format_minutes(s.overtime),
            format_minutes(s.night),
            format_minutes(s.holiday),
            format!("{}회", s.late_count),
        ]);
    }

    // 각 열의 폭 = 헤더와 값 중 가장 넓은 것
    let mut widths: Vec<usize> = headers.iter().map(|h| display_width(h)).collect();
    for row in &rows {
        for (i, cell) in row.iter().enumerate() {
            widths[i] = widths[i].max(display_width(cell));
        }
    }

    let format_row = |cells: Vec<&str>| -> String {
        cells
            .iter()
            .zip(&widths)
            .map(|(c, &w)| pad_left(c, w))
            .collect::<Vec<_>>()
            .join("  ")
    };

    let mut out = String::new();
    out.push_str(&format_row(headers.to_vec()));
    out.push('\n');
    let total_width: usize = widths.iter().sum::<usize>() + 2 * (widths.len() - 1);
    out.push_str(&"-".repeat(total_width));
    out.push('\n');
    for row in &rows {
        out.push_str(&format_row(row.iter().map(String::as_str).collect()));
        out.push('\n');
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 분을 시간 분으로 표시한다
    #[test]
    fn formats_minutes() {
        assert_eq!(format_minutes(0), "0:00");
        assert_eq!(format_minutes(90), "1:30");
        assert_eq!(format_minutes(2475), "41:15");
    }

    /// 하루치 결과를 누적한다
    #[test]
    fn accumulates_daily_results() {
        let mut s = Summary::default();
        s.add(&DailyResult {
            worked: 480,
            overtime: 0,
            night: 0,
            holiday: 0,
            late: true,
        });
        s.add(&DailyResult {
            worked: 540,
            overtime: 60,
            night: 30,
            holiday: 0,
            late: false,
        });
        assert_eq!(s.work_days, 2);
        assert_eq!(s.worked, 1020);
        assert_eq!(s.overtime, 60);
        assert_eq!(s.night, 30);
        assert_eq!(s.late_count, 1);
    }

    /// 표에 사원이 사번 순으로 나온다
    #[test]
    fn table_is_sorted_by_employee_id() {
        let mut map = BTreeMap::new();
        map.insert("E002".to_string(), Summary::default());
        map.insert(
            "E001".to_string(),
            Summary {
                work_days: 1,
                worked: 480,
                ..Default::default()
            },
        );
        let table = render_table(&map);
        let lines: Vec<&str> = table.lines().collect();
        assert_eq!(lines.len(), 4);
        assert!(lines[0].contains("근무일수"));
        assert!(lines[2].trim_start().starts_with("E001"));
        assert!(lines[2].contains("8:00"));
        assert!(lines[3].trim_start().starts_with("E002"));
    }
}
