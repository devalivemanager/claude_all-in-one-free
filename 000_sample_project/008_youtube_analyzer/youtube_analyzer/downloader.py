"""yt-dlp로 유튜브 영상 정보·자막·영상 파일을 내려받는다.

yt-dlp 호출은 YoutubeDL 클래스를 바깥에서 주입받을 수 있게 해서,
테스트에서는 네트워크 없이 가짜 클래스로 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SUBTITLE_EXTENSIONS = (".vtt", ".srt")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv")


@dataclass
class VideoInfo:
    """분석에 필요한 영상 메타데이터."""

    video_id: str
    title: str
    channel: str = ""
    duration: float = 0.0
    upload_date: str = ""
    url: str = ""
    description: str = ""
    chapters: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_ytdlp(cls, info: dict[str, Any]) -> "VideoInfo":
        return cls(
            video_id=info.get("id", ""),
            title=info.get("title", ""),
            channel=info.get("channel") or info.get("uploader") or "",
            duration=float(info.get("duration") or 0),
            upload_date=info.get("upload_date") or "",
            url=info.get("webpage_url") or "",
            description=info.get("description") or "",
            chapters=list(info.get("chapters") or []),
        )


@dataclass
class DownloadResult:
    info: VideoInfo
    subtitle: Path | None
    video: Path | None


def _default_ydl_class() -> Callable[..., Any]:
    from yt_dlp import YoutubeDL  # 실제 사용 시에만 import

    return YoutubeDL


def build_options(out_dir: Path, languages: list[str], with_video: bool, max_height: int) -> dict[str, Any]:
    """yt-dlp 옵션. 자막은 수동 자막 우선, 없으면 자동 생성 자막."""
    return {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": languages,
        "subtitlesformat": "vtt/srt/best",
        "skip_download": not with_video,
        # 장면 캡처용이므로 가벼운 단일 파일(영상+음성 합본 mp4) 우선
        "format": f"best[height<={max_height}][ext=mp4]/best[height<={max_height}]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }


def _find_first(out_dir: Path, extensions: tuple[str, ...], languages: list[str]) -> Path | None:
    candidates = sorted(p for p in out_dir.glob("source*") if p.suffix in extensions)
    for lang in languages:  # 요청한 언어 순서대로 우선
        for path in candidates:
            if f".{lang}." in path.name:
                return path
    return candidates[0] if candidates else None


def download(
    url: str,
    out_dir: Path,
    languages: list[str],
    with_video: bool = True,
    max_height: int = 720,
    ydl_class: Callable[..., Any] | None = None,
) -> DownloadResult:
    """URL의 메타데이터를 얻고 자막(·영상)을 out_dir에 저장한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ydl_cls = ydl_class or _default_ydl_class()
    with ydl_cls(build_options(out_dir, languages, with_video, max_height)) as ydl:
        info = ydl.extract_info(url, download=True)
    return DownloadResult(
        info=VideoInfo.from_ytdlp(info),
        subtitle=_find_first(out_dir, SUBTITLE_EXTENSIONS, languages),
        video=_find_first(out_dir, VIDEO_EXTENSIONS, []) if with_video else None,
    )
