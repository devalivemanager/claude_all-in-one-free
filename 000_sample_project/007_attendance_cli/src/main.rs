//! ERP 인사 근태 집계 CLI.
//!
//! 사용법: `cargo run -- data/sample.csv`

mod calc;
mod record;
mod report;

use std::collections::{BTreeMap, HashSet};
use std::env;
use std::fs;
use std::process::ExitCode;

use report::Summary;

/// 경고 한 건(줄 번호와 사유).
#[derive(Debug, Clone, PartialEq, Eq)]
struct Warning {
    line_no: usize,
    message: String,
}

/// CSV 전체 내용을 읽어 사원별로 집계한다.
///
/// - 첫 줄이 "사번"으로 시작하면 헤더로 보고 건너뛴다.
/// - 빈 줄과 `#` 으로 시작하는 주석 줄은 건너뛴다.
/// - 잘못된 행이나 같은 사원·같은 날짜의 중복 행은 경고로 모으고 건너뛴다.
fn aggregate(content: &str) -> (BTreeMap<String, Summary>, Vec<Warning>) {
    let mut summaries: BTreeMap<String, Summary> = BTreeMap::new();
    let mut warnings = Vec::new();
    let mut seen = HashSet::new();

    for (index, raw) in content.lines().enumerate() {
        let line_no = index + 1;
        let line = raw.trim().trim_start_matches('\u{feff}'); // UTF-8 BOM 제거
        if line.is_empty() || line.starts_with('#') || (line_no == 1 && line.starts_with("사번"))
        {
            continue;
        }

        let record = match record::parse_line(line) {
            Ok(r) => r,
            Err(e) => {
                warnings.push(Warning {
                    line_no,
                    message: e.to_string(),
                });
                continue;
            }
        };

        if !seen.insert((record.employee_id.clone(), record.date)) {
            warnings.push(Warning {
                line_no,
                message: format!("중복 기록입니다 ({} {})", record.employee_id, record.date),
            });
            continue;
        }

        let day = calc::calculate(&record);
        summaries.entry(record.employee_id).or_default().add(&day);
    }

    (summaries, warnings)
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("사용법: attendance_cli <CSV 파일 경로>");
        eprintln!("예시:   cargo run -- data/sample.csv");
        return ExitCode::from(2);
    }

    let path = &args[1];
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("오류: 파일을 읽을 수 없습니다 '{path}': {e}");
            return ExitCode::FAILURE;
        }
    };

    let (summaries, warnings) = aggregate(&content);

    for w in &warnings {
        eprintln!("경고: {}번째 줄을 건너뜁니다 - {}", w.line_no, w.message);
    }
    if !warnings.is_empty() {
        eprintln!();
    }

    if summaries.is_empty() {
        println!("집계할 유효한 근태 기록이 없습니다.");
        return ExitCode::SUCCESS;
    }

    println!("근태 집계 결과 (시간 표기는 시간:분)");
    println!();
    print!("{}", report::render_table(&summaries));
    println!();
    println!("사원 {}명, 경고 {}건", summaries.len(), warnings.len());
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 헤더 주석 빈줄은 건너뛴다
    #[test]
    fn skips_header_comments_and_blank_lines() {
        let csv = "사번,날짜,출근시각,퇴근시각\n# 주석\n\nE001,2026-10-26,09:00,18:00\n";
        let (map, warnings) = aggregate(csv);
        assert!(warnings.is_empty());
        assert_eq!(map["E001"].work_days, 1);
        assert_eq!(map["E001"].worked, 480);
    }

    /// 잘못된 행은 줄번호와 함께 경고하고 건너뛴다
    #[test]
    fn warns_with_line_number_and_skips_bad_rows() {
        let csv = "사번,날짜,출근시각,퇴근시각\n\
                   E001,2026-10-26,09:00,18:00\n\
                   E001,2026-10-27,25:00,18:00\n\
                   E001,2026-02-30,09:00,18:00\n\
                   E001,2026-10-28,09:00\n\
                   E002,2026-10-26,09:30,18:30\n";
        let (map, warnings) = aggregate(csv);
        let lines: Vec<usize> = warnings.iter().map(|w| w.line_no).collect();
        assert_eq!(lines, vec![3, 4, 5]);
        assert!(warnings[0].message.contains("시각"));
        assert!(warnings[1].message.contains("날짜"));
        assert!(warnings[2].message.contains("열 개수"));
        assert_eq!(map["E001"].work_days, 1);
        assert_eq!(map["E002"].late_count, 1);
    }

    /// 중복 기록은 경고한다
    #[test]
    fn warns_on_duplicate_record() {
        let csv = "E001,2026-10-26,09:00,18:00\nE001,2026-10-26,10:00,19:00\n";
        let (map, warnings) = aggregate(csv);
        assert_eq!(warnings.len(), 1);
        assert_eq!(warnings[0].line_no, 2);
        assert!(warnings[0].message.contains("중복"));
        assert_eq!(map["E001"].work_days, 1);
    }

    /// 샘플 파일을 집계한다
    #[test]
    fn aggregates_sample_file() {
        let csv = include_str!("../data/sample.csv");
        let (map, warnings) = aggregate(csv);
        assert_eq!(map.len(), 3);
        assert_eq!(warnings.len(), 4);

        // E001: 평일 5일 + 토요일 1일
        let e1 = &map["E001"];
        assert_eq!(e1.work_days, 6);
        assert_eq!(e1.late_count, 1);
        assert_eq!(e1.holiday, 4 * 60 + 30);
        assert!(e1.night > 0);

        // E002: 야간 교대 3일 + 일요일 자정 넘김
        let e2 = &map["E002"];
        assert_eq!(e2.work_days, 6);
        assert!(e2.night >= 3 * 8 * 60);
        assert_eq!(e2.holiday, 5 * 60 + 30);
    }
}
