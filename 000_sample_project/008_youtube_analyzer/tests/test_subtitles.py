"""자막 파싱·중복 제거 테스트."""

import pytest

from youtube_analyzer.subtitles import (
    Cue,
    deduplicate,
    format_timestamp,
    group_by_interval,
    parse_subtitles,
    parse_timestamp,
)

# 유튜브 자동 생성 자막 형태: 단어별 타이밍 태그 + 앞 큐 문장 반복
AUTO_VTT = """WEBVTT
Kind: captions
Language: ko

00:00:00.000 --> 00:00:02.000 align:start position:0%
안녕하세요<00:00:00.500><c> 오늘은</c>

00:00:02.000 --> 00:00:02.010 align:start position:0%
안녕하세요 오늘은

00:00:02.010 --> 00:00:04.000 align:start position:0%
안녕하세요 오늘은
유튜브<00:00:02.500><c> 분석을</c><00:00:03.000><c> 해봅니다</c>

00:00:04.000 --> 00:00:06.000
유튜브 분석을 해봅니다
"""

SRT = """1
00:00:01,000 --> 00:00:03,500
첫 번째 줄
두 번째 줄

2
00:01:05,250 --> 00:01:07,000
<i>기울임</i> &amp; 기호
"""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00:00:01.500", 1.5),
        ("01:02.250", 62.25),
        ("01:00:00,000", 3600.0),
        ("1:02:03.4", 3723.4),
    ],
)
def test_parse_timestamp(value, expected):
    assert parse_timestamp(value) == pytest.approx(expected)


def test_parse_timestamp_invalid():
    with pytest.raises(ValueError):
        parse_timestamp("12")


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "00:00:00"), (59.9, "00:00:59"), (61, "00:01:01"), (3723.4, "01:02:03")],
)
def test_format_timestamp(seconds, expected):
    assert format_timestamp(seconds) == expected


def test_parse_vtt_removes_header_and_tags():
    cues = parse_subtitles(AUTO_VTT)
    assert cues[0] == Cue(0.0, 2.0, "안녕하세요 오늘은")
    assert all("<" not in c.text for c in cues)
    assert len(cues) == 4


def test_parse_srt_with_numbers_and_entities():
    cues = parse_subtitles(SRT)
    assert cues == [
        Cue(1.0, 3.5, "첫 번째 줄 두 번째 줄"),
        Cue(65.25, 67.0, "기울임 & 기호"),
    ]


def test_parse_handles_crlf_and_empty_text():
    content = "WEBVTT\r\n\r\n00:00:00.000 --> 00:00:01.000\r\n\r\n00:00:01.000 --> 00:00:02.000\r\n말\r\n"
    assert parse_subtitles(content) == [Cue(1.0, 2.0, "말")]


def test_deduplicate_rolling_auto_captions():
    """자동 자막의 반복이 제거되어 문장이 한 번씩만 남는다."""
    cues = deduplicate(parse_subtitles(AUTO_VTT))
    assert [c.text for c in cues] == ["안녕하세요 오늘은", "유튜브 분석을 해봅니다"]
    assert cues[1].start == pytest.approx(2.01)


def test_deduplicate_keeps_distinct_sentences():
    cues = [Cue(0, 1, "가 나"), Cue(1, 2, "다 라"), Cue(2, 3, "가 나")]
    assert [c.text for c in deduplicate(cues)] == ["가 나", "다 라", "가 나"]


def test_group_by_interval():
    cues = [Cue(0, 1, "a"), Cue(5, 6, "b"), Cue(12, 13, "c")]
    grouped = group_by_interval(cues, 10)
    assert grouped == [Cue(0, 6, "a b"), Cue(12, 13, "c")]


def test_group_by_interval_rejects_zero():
    with pytest.raises(ValueError):
        group_by_interval([], 0)
