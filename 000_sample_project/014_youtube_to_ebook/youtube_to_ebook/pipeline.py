"""잇기(pipeline) — 자막 대본을 챕터로 나누고, 챕터마다 스틸컷을 맞춰 넣는다.

008 이 뽑아 준 자막 큐와 프레임을 받아 013 의 조판 입력(제목·본문·삽화)으로 바꾸는
가운데 단계다. 여기서도 모델을 쓰지 않으므로 결과가 늘 같고 비용이 0원이다.

- 챕터화 : 시간대별(기본 60초)로 묶거나, 유튜브 챕터(공식 구간 정보)가 있으면 그 경계를 따른다.
- 이미지 매칭 : 스틸컷의 캡처 시점이 어느 챕터 구간에 드는지로 배정한다.
- 오케스트레이션 : `build_book` 이 뽑기 → 잇기 → 묶기를 한 번에 돌린다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import ebook, extractor


@dataclass
class Section:
    """전자책 한 챕터. `images` 는 그 챕터에 배정된 스틸컷."""

    title: str
    body: str
    start: float = 0.0  # 챕터 시작 시점(초)
    end: float = 0.0  # 챕터 끝 시점(초, 0 이면 끝이 정해지지 않음)
    images: list[extractor.Frame] = field(default_factory=list)


def chapters_from_cues(cues: list[extractor.Cue], interval: float = 60.0) -> list[Section]:
    """큐를 interval 초 단위 챕터로 묶는다. 제목은 「제N화 (00:00–01:00)」 형태."""
    if interval <= 0:
        raise ValueError("interval은 0보다 커야 합니다")
    groups: dict[int, list[extractor.Cue]] = {}
    for cue in cues:
        groups.setdefault(int(cue.start // interval), []).append(cue)
    sections: list[Section] = []
    for order, (_, items) in enumerate(sorted(groups.items()), start=1):
        start, end = items[0].start, items[-1].end
        title = (
            f"제{order}화 "
            f"({extractor.format_timestamp(start)}–{extractor.format_timestamp(end)})"
        )
        sections.append(
            Section(title=title, body="\n\n".join(c.text for c in items), start=start, end=end)
        )
    return sections


def chapters_from_youtube_chapters(
    cues: list[extractor.Cue], chapters: list[dict[str, Any]]
) -> list[Section] | None:
    """유튜브 공식 챕터(구간 정보)가 있으면 그 경계로 챕터를 나눈다. 없으면 None.

    `chapters` 는 yt-dlp info 의 `chapters` — {'start_time', 'end_time', 'title'} 목록.
    """
    if not chapters:
        return None
    sections: list[Section] = []
    for chapter in chapters:
        start = float(chapter.get("start_time") or 0)
        end = float(chapter.get("end_time") or 0)
        inside = [c for c in cues if start <= c.start and (end <= start or c.start < end)]
        body = "\n\n".join(c.text for c in inside)
        if not body:
            continue
        sections.append(
            Section(
                title=str(chapter.get("title") or "무제"),
                body=body,
                start=start,
                end=end,
            )
        )
    return sections or None


def match_frames(sections: list[Section], frames: list[extractor.Frame]) -> list[Section]:
    """스틸컷을 캡처 시점이 속한 챕터에 배정한다. 어느 챕터에도 안 드는 컷은 버린다.

    챕터의 `end` 가 0(끝 미정)이면 마지막 챕터로 본다.
    """
    for section in sections:
        section.images = []
    for frame in frames:
        for index, section in enumerate(sections):
            last = index == len(sections) - 1
            in_range = section.start <= frame.timestamp and (
                section.end <= 0 or frame.timestamp < section.end or (last and frame.timestamp >= section.end)
            )
            if in_range:
                section.images.append(frame)
                break
    return sections


@dataclass
class BuildResult:
    """한 번의 빌드로 나온 결과물과 통계."""

    outputs: dict[str, Path] = field(default_factory=dict)
    chapters: int = 0
    cues: int = 0
    frames: int = 0
    warnings: list[str] = field(default_factory=list)


def build_book(
    url: str,
    out_dir: Path,
    formats: tuple[str, ...] = ("html", "epub"),
    languages: list[str] | None = None,
    subtitle_interval: float = 60.0,
    capture_interval: float = 10.0,
    max_width: int = 1280,
    title: str = "",
    author: str = "",
    fetch_info: Callable[[str], dict[str, Any]] | None = None,
    download_subtitle: Callable[[str, Path, list[str]], Path | None] | None = None,
    download_video: Callable[[str, Path], Path | None] | None = None,
    capture: Callable[[Path, Path, float, int], list[extractor.Frame]] | None = None,
) -> BuildResult:
    """원클릭 빌드 — 유튜브 URL 하나를 넣으면 삽화 전자책이 나온다.

    외부 연결(정보 조회·자막·영상·캡처)은 전부 주입 가능하다. 기본값은 extractor 의
    실제 구현(yt-dlp·ffmpeg)이고, 테스트에서는 가짜를 넣어 네트워크 없이 검증한다.
    """
    languages = languages or ["ko", "en"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = BuildResult()

    get_info = fetch_info or extractor.fetch_info
    get_subtitle = download_subtitle or extractor.download_subtitle
    get_video = download_video or extractor.download_video
    capture_frames = capture or (
        lambda video, frames_dir, interval, width: extractor.capture_frames(
            video, frames_dir, interval=interval, width=width
        )
    )

    info = get_info(url)
    title = title or str(info.get("title") or "무제")
    author = author or str(info.get("channel") or info.get("uploader") or "")

    subtitle = get_subtitle(url, out_dir / "source", languages)
    if subtitle is None:
        result.warnings.append(
            "자막을 찾지 못했습니다. 자막이 있는 영상을 쓰거나 local_transcribe 폴백을 쓰세요."
        )
        return result

    cues = extractor.load_transcript(subtitle)
    result.cues = len(cues)
    if not cues:
        result.warnings.append("자막 파일은 있지만 읽을 문장이 없습니다.")
        return result

    youtube_chapters = list(info.get("chapters") or [])
    sections = chapters_from_youtube_chapters(cues, youtube_chapters)
    if sections is None:
        sections = chapters_from_cues(cues, subtitle_interval)

    video = get_video(url, out_dir / "source")
    if video is not None:
        frames = capture_frames(video, out_dir / "frames", capture_interval, max_width)
        result.frames = len(frames)
        sections = match_frames(sections, frames)
    else:
        result.warnings.append(
            "영상을 내려받지 못해 스틸컷 없이 글만 조판합니다(자막만으로도 전자책은 나옵니다)."
        )

    meta = ebook.BookMeta(title=title, author=author)
    written = ebook.write_outputs(meta, sections, out_dir, formats)
    result.outputs = written
    result.chapters = len(sections)
    return result
