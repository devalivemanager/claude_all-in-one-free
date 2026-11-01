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
    warnings: list[str] = field(default_factory=list)


def _default_ydl_class() -> Callable[..., Any]:
    from yt_dlp import YoutubeDL  # 실제 사용 시에만 import

    return YoutubeDL


def video_format(max_height: int) -> str:
    """장면 캡처용 영상 포맷 선택식.

    장면 캡처에는 음성이 필요 없고, 요즘 유튜브는 영상+음성 합본 포맷을 주지 않는 경우가 많다.
    그래서 영상 전용 스트림을 먼저 고른다. ffmpeg 호환성이 가장 좋은 H.264(avc1)를 우선하고,
    없으면 다른 코덱, 그래도 없으면 합본 포맷으로 물러선다.
    """
    h = f"[height<={max_height}]"
    return "/".join([
        f"bestvideo{h}[vcodec^=avc1]",
        f"bestvideo{h}",
        f"best{h}",
        "bestvideo",
        "best",
    ])


@dataclass(frozen=True)
class SubtitleChoice:
    """내려받을 자막 하나."""

    language: str  # 유튜브 자막 키 (예: 'ko', 'en-orig')
    automatic: bool  # True = 자동 생성 자막


def choose_subtitle(info: dict[str, Any], languages: list[str]) -> SubtitleChoice | None:
    """실제로 있는 자막 중 가장 우선인 하나를 고른다.

    우선순위: 요청 언어 순서 × (수동 자막 → 자동 자막).
    자동 자막은 원어 자막('ko', 'ko-orig')만 쓰고, 기계 번역본('ko-en' 등)은 쓰지 않는다.
    모든 언어를 한꺼번에 받으면 유튜브 요청 제한(429)에 걸리기 쉬워서 하나만 받는다.
    """
    manual = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}
    for lang in languages:
        if lang in manual:
            return SubtitleChoice(lang, automatic=False)
        for key in (f"{lang}-orig", lang):
            if key in automatic:
                return SubtitleChoice(key, automatic=True)
    return None


def build_options(
    out_dir: Path, subtitle: SubtitleChoice | None, with_video: bool, max_height: int
) -> dict[str, Any]:
    """yt-dlp 옵션. 고른 자막 하나만 내려받는다."""
    return {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "writesubtitles": subtitle is not None and not subtitle.automatic,
        "writeautomaticsub": subtitle is not None and subtitle.automatic,
        "subtitleslangs": [subtitle.language] if subtitle else [],
        "subtitlesformat": "vtt/srt/best",
        "skip_download": not with_video,
        "format": video_format(max_height),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }


def _find_first(out_dir: Path, extensions: tuple[str, ...]) -> Path | None:
    candidates = sorted(p for p in out_dir.glob("source*") if p.suffix in extensions)
    return candidates[0] if candidates else None


def download(
    url: str,
    out_dir: Path,
    languages: list[str],
    with_video: bool = True,
    max_height: int = 720,
    ydl_class: Callable[..., Any] | None = None,
) -> DownloadResult:
    """URL의 메타데이터를 얻고 자막(·영상)을 out_dir에 저장한다.

    1단계: 정보만 조회해 어떤 자막이 있는지 확인한다.
    2단계: 고른 자막 하나와 (필요하면) 영상을 내려받는다. 페이지를 다시 요청하지 않고 1단계 정보를 재사용한다.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ydl_cls = ydl_class or _default_ydl_class()
    with ydl_cls({"quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    subtitle = choose_subtitle(info, languages)
    warnings: list[str] = []
    if subtitle is None:
        warnings.append(f"요청한 언어({', '.join(languages)})의 자막이 없습니다.")
    if subtitle or with_video:
        try:
            with ydl_cls(build_options(out_dir, subtitle, with_video, max_height)) as ydl:
                ydl.process_ie_result(info, download=True)
        except Exception as error:
            if not with_video:
                raise
            # 유튜브가 서버(클라우드) IP의 영상 다운로드를 막는 경우가 있다(HTTP 403).
            # 영상 없이도 자막 분석은 의미가 있으므로, 자막만 다시 받아 계속 진행한다.
            warnings.append(f"영상을 내려받지 못해 장면 캡처를 생략합니다: {error}")
            with_video = False
            if subtitle and _find_first(out_dir, SUBTITLE_EXTENSIONS) is None:
                with ydl_cls(build_options(out_dir, subtitle, False, max_height)) as ydl:
                    ydl.process_ie_result(info, download=True)
    return DownloadResult(
        info=VideoInfo.from_ytdlp(info),
        subtitle=_find_first(out_dir, SUBTITLE_EXTENSIONS) if subtitle else None,
        video=_find_first(out_dir, VIDEO_EXTENSIONS) if with_video else None,
        warnings=warnings,
    )
