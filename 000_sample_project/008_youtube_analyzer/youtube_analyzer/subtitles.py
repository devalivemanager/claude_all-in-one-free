"""자막 파일(WebVTT, SRT)을 읽어 깨끗한 대본으로 바꾼다.

유튜브 자동 생성 자막은 같은 문장이 여러 큐(cue)에 걸쳐 반복되고,
<00:00:01.000><c>단어</c> 같은 단어별 타이밍 태그가 섞여 있다.
여기서는 태그를 지우고, 앞 큐와 겹치는 부분을 잘라 중복 없는 대본을 만든다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# 00:01:02.345 또는 01:02.345 (SRT는 쉼표 구분자 사용)
_TIME = r"(?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{1,3}"
_TIMING_LINE = re.compile(rf"^\s*({_TIME})\s*-->\s*({_TIME})")
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    """자막 한 구간."""

    start: float  # 초
    end: float  # 초
    text: str


def parse_timestamp(value: str) -> float:
    """'00:01:02.345' / '01:02,345' 형식을 초 단위 실수로 바꾼다."""
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        parts.insert(0, "0")
    if len(parts) != 3:
        raise ValueError(f"잘못된 타임스탬프: {value!r}")
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def format_timestamp(seconds: float) -> str:
    """초를 '00:01:02' 형식으로 바꾼다(보고서 표시용, 소수점 버림)."""
    total = int(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _clean_text(lines: list[str]) -> str:
    text = " ".join(_TAG.sub("", line).strip() for line in lines)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def parse_subtitles(content: str) -> list[Cue]:
    """VTT/SRT 문자열을 큐 목록으로 파싱한다. 헤더·번호·스타일 블록은 무시한다."""
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())
    for block in blocks:
        lines = block.split("\n")
        for i, line in enumerate(lines):
            match = _TIMING_LINE.match(line)
            if match:
                text = _clean_text(lines[i + 1 :])
                if text:
                    cues.append(
                        Cue(parse_timestamp(match.group(1)), parse_timestamp(match.group(2)), text)
                    )
                break
    return cues


def _overlap_length(previous: str, current: str) -> int:
    """previous의 끝과 current의 앞이 단어 단위로 겹치는 길이(단어 수)."""
    prev_words = previous.split()
    curr_words = current.split()
    for size in range(min(len(prev_words), len(curr_words)), 0, -1):
        if prev_words[-size:] == curr_words[:size]:
            return size
    return 0


def deduplicate(cues: list[Cue]) -> list[Cue]:
    """자동 자막의 반복(롤링) 문장을 제거한다.

    - 앞 큐와 완전히 같은 텍스트 → 버림
    - 앞 큐 텍스트를 포함 → 새로 추가된 꼬리 부분만 남김
    - 앞 큐 끝과 겹치는 앞부분 → 겹치는 부분 잘라냄
    """
    result: list[Cue] = []
    previous = ""
    for cue in cues:
        text = cue.text
        if text == previous:
            continue
        overlap = _overlap_length(previous, text)
        new_text = " ".join(text.split()[overlap:])
        previous = text
        if new_text:
            result.append(Cue(cue.start, cue.end, new_text))
    return result


def group_by_interval(cues: list[Cue], interval: float) -> list[Cue]:
    """큐를 interval초 단위 문단으로 묶는다(긴 영상 대본을 읽기 쉽게)."""
    if interval <= 0:
        raise ValueError("interval은 0보다 커야 합니다")
    groups: dict[int, list[Cue]] = {}
    for cue in cues:
        groups.setdefault(int(cue.start // interval), []).append(cue)
    return [
        Cue(items[0].start, items[-1].end, " ".join(c.text for c in items))
        for _, items in sorted(groups.items())
    ]


def load_transcript(path: Path) -> list[Cue]:
    """자막 파일을 읽어 중복 제거된 큐 목록을 돌려준다."""
    return deduplicate(parse_subtitles(path.read_text(encoding="utf-8")))
