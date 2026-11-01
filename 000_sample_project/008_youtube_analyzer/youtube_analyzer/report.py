"""분석 결과를 Claude가 읽기 좋은 Markdown 보고서로 만든다.

보고서 구성: 영상 정보 → 챕터 → 시간대별 대본 + 같은 시간대의 장면 이미지.
대본과 장면을 같은 구간에 나란히 두어, 말한 내용과 화면(코드·슬라이드)을 함께 볼 수 있게 한다.
"""

from __future__ import annotations

from pathlib import Path

from .downloader import VideoInfo
from .frames import Frame
from .subtitles import Cue, format_timestamp


def _section_index(timestamp: float, interval: float) -> int:
    return int(timestamp // interval)


def build_report(
    info: VideoInfo,
    transcript: list[Cue],
    frames: list[Frame],
    out_dir: Path,
    section_seconds: float = 60.0,
    cuts: list[float] | None = None,
) -> str:
    """cuts: 컷 전환 시점(초). None이면 컷 분석을 하지 않은 것으로 보고 섹션을 생략한다."""
    lines = [f"# {info.title or '(제목 없음)'}", ""]
    meta = [
        ("영상 ID", info.video_id),
        ("채널", info.channel),
        ("길이", format_timestamp(info.duration) if info.duration else ""),
        ("업로드", info.upload_date),
        ("URL", info.url),
    ]
    lines += [f"- **{k}**: {v}" for k, v in meta if v]
    lines += ["", f"- **대본 구간 수**: {len(transcript)}", f"- **장면 캡처 수**: {len(frames)}", ""]

    if info.description:
        lines += ["## 영상 설명", "", info.description.strip(), ""]

    if info.chapters:
        lines += ["## 챕터", ""]
        lines += [
            f"- `{format_timestamp(float(ch.get('start_time', 0)))}` {ch.get('title', '')}"
            for ch in info.chapters
        ]
        lines.append("")

    if cuts is not None:
        lines += ["## 컷 전환", "", *cut_summary(cuts, info.duration), ""]

    if not transcript:
        lines += ["> 자막을 찾지 못했습니다. 장면 캡처만 포함되어 있습니다.", ""]

    # 대본과 장면을 같은 구간(section_seconds)별로 묶는다
    sections: dict[int, tuple[list[Cue], list[Frame], list[float]]] = {}
    for cue in transcript:
        sections.setdefault(_section_index(cue.start, section_seconds), ([], [], []))[0].append(cue)
    for frame in sorted(frames, key=lambda f: f.timestamp):
        sections.setdefault(_section_index(frame.timestamp, section_seconds), ([], [], []))[1].append(frame)
    for cut in cuts or []:
        sections.setdefault(_section_index(cut, section_seconds), ([], [], []))[2].append(cut)

    lines += ["## 시간대별 내용", ""]
    for index in sorted(sections):
        cues, section_frames, section_cuts = sections[index]
        start = index * section_seconds
        lines += [f"### {format_timestamp(start)} ~ {format_timestamp(start + section_seconds)}", ""]
        if section_cuts:
            stamps = ", ".join(f"`{_precise(c)}`" for c in section_cuts)
            lines += [f"✂ 컷 전환 {len(section_cuts)}회: {stamps}", ""]
        for cue in cues:
            lines.append(f"`{format_timestamp(cue.start)}` {cue.text}  ")
        if cues:
            lines.append("")
        for frame in section_frames:
            rel = frame.path.relative_to(out_dir).as_posix()
            lines.append(f"![{format_timestamp(frame.timestamp)} 장면]({rel})")
        if section_frames:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _precise(seconds: float) -> str:
    """컷 위치처럼 1초 미만이 중요한 값은 소수 첫째 자리까지 표시한다."""
    tenths = round(seconds * 10)  # 1.96초 → 20 → "00:00:02.0" (반올림 후 자리 올림까지 처리)
    return f"{format_timestamp(tenths // 10)}.{tenths % 10}"


def cut_summary(cuts: list[float], duration: float) -> list[str]:
    """컷 전환 통계. 컷 길이(장면 하나가 유지되는 시간)로 편집 속도를 가늠할 수 있다."""
    if not cuts:
        return ["- 컷 전환이 감지되지 않았습니다(한 장면으로 이어지는 영상이거나 임계값이 높음)."]
    bounds = [0.0, *sorted(cuts)] + ([duration] if duration > max(cuts) else [])
    shots = [b - a for a, b in zip(bounds, bounds[1:]) if b > a]
    return [
        f"- **컷 전환 수**: {len(cuts)}회 (장면 {len(shots)}개)",
        f"- **평균 컷 길이**: {sum(shots) / len(shots):.1f}초 (최단 {min(shots):.1f}초, 최장 {max(shots):.1f}초)",
        f"- **분당 컷 수**: {len(cuts) / duration * 60:.1f}회" if duration else "- **분당 컷 수**: (영상 길이 모름)",
    ]


def build_transcript_text(transcript: list[Cue]) -> str:
    """타임스탬프가 붙은 순수 대본 텍스트(검색·요약용)."""
    return "".join(f"[{format_timestamp(c.start)}] {c.text}\n" for c in transcript)
