"""뽑개(extractor) — 유튜브 영상에서 자막 대본과 핵심 장면 스틸컷을 뽑아 낸다.

008_youtube_analyzer 의 다운로더·자막·프레임 모듈을 전자책 조판에 맞게 줄인 모듈이다.

- 자막 : yt-dlp 로 수동 자막을 먼저 찾고, 없으면 자동 생성 자막을 하나만 받는다.
  (여러 언어를 한꺼번에 받으면 유튜브 요청 과다(429)에 걸리기 쉽다)
- 스틸컷 : ffmpeg 로 일정 간격마다 프레임을 PNG 로 저장한다.
- 폴백 : 자막이 아예 없는 영상은 로컬 받아쓰기(faster-whisper 등)로 메운다.

외부 연결(yt-dlp, ffmpeg)은 클래스·함수를 바깥에서 주입받을 수 있게 해서,
테스트에서는 네트워크·설치 없이 가짜로 검증한다.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SUBTITLE_EXTENSIONS = (".vtt", ".srt")

# 00:01:02.345 또는 01:02.345 (SRT 는 쉼표 구분자)
_TIME = r"(?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{1,3}"
_TIMING_LINE = re.compile(rf"^\s*({_TIME})\s*-->\s*({_TIME})")
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    """자막 한 구간. `start`·`end` 는 초 단위."""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Frame:
    """캡처한 장면 한 장."""

    timestamp: float  # 영상 내 위치(초)
    path: Path


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
    """초를 '00:01:23' 형식으로 바꾼다(전자책 캡션 표시용, 소수점 버림)."""
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
    """previous 의 끝과 current 의 앞이 단어 단위로 겹치는 길이(단어 수)."""
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


def load_transcript(path: Path) -> list[Cue]:
    """자막 파일을 읽어 중복 제거된 큐 목록을 돌려준다."""
    return deduplicate(parse_subtitles(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class SubtitleChoice:
    """내려받을 자막 하나. `automatic` 이 참이면 자동 생성 자막이다."""

    language: str
    automatic: bool


def choose_subtitle(info: dict[str, Any], languages: list[str]) -> SubtitleChoice | None:
    """실제로 있는 자막 중 가장 우선인 하나를 고른다.

    우선순위 : 요청 언어 순서 × (수동 자막 → 자동 자막 원어). 기계 번역본('ko-en')은 쓰지 않는다.
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


def fetch_info(url: str, ydl_class: Callable[..., Any] | None = None) -> dict[str, Any]:
    """yt-dlp 로 영상 메타데이터(제목·자막 목록)만 가볍게 조회한다."""
    ydl_cls = ydl_class or _default_ydl_class()
    with ydl_cls({"quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
        return ydl.extract_info(url, download=False)


def download_subtitle(
    url: str,
    out_dir: Path,
    languages: list[str] = ("ko", "en"),
    ydl_class: Callable[..., Any] | None = None,
) -> Path | None:
    """유튜브 자막 하나를 out_dir 에 내려받고 파일 경로를 돌려준다. 없으면 None."""
    out_dir.mkdir(parents=True, exist_ok=True)
    info = fetch_info(url, ydl_class)
    choice = choose_subtitle(info, list(languages))
    if choice is None:
        return None
    ydl_cls = ydl_class or _default_ydl_class()
    options = {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "writesubtitles": not choice.automatic,
        "writeautomaticsub": choice.automatic,
        "subtitleslangs": [choice.language],
        "subtitlesformat": "vtt/srt/best",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }
    with ydl_cls(options) as ydl:
        ydl.process_ie_result(info, download=True)
    found = sorted(p for p in out_dir.glob("source*") if p.suffix in SUBTITLE_EXTENSIONS)
    return found[0] if found else None


def download_video(
    url: str,
    out_dir: Path,
    max_height: int = 720,
    ydl_class: Callable[..., Any] | None = None,
) -> Path | None:
    """장면 캡처용 영상(음성 없는 영상 전용 스트림 포함)을 내려받는다. 실패하면 None."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ydl_cls = ydl_class or _default_ydl_class()
    h = f"[height<={max_height}]"
    options = {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "format": "/".join([f"bestvideo{h}[vcodec^=avc1]", f"bestvideo{h}", f"best{h}", "best"]),
        "skip_download": False,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }
    try:
        with ydl_cls(options) as ydl:
            ydl.process_ie_result(fetch_info(url, ydl_class), download=True)
    except Exception:
        return None
    video_exts = (".mp4", ".webm", ".mkv")
    found = sorted(p for p in out_dir.glob("source*") if p.suffix in video_exts)
    return found[0] if found else None


def _default_ydl_class() -> Callable[..., Any]:
    from yt_dlp import YoutubeDL  # 실제 사용 시에만 import

    return YoutubeDL


def frame_timestamps(duration: float, interval: float) -> list[float]:
    """0초부터 interval 간격의 캡처 시점 목록(영상 길이 미만)."""
    if interval <= 0:
        raise ValueError("interval은 0보다 커야 합니다")
    count = int(duration // interval) + (1 if duration % interval else 0)
    return [i * interval for i in range(count)]


def _require(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        raise RuntimeError(f"{tool}을(를) 찾을 수 없습니다. ffmpeg를 설치하세요.")
    return found


def capture_frames(
    video: Path,
    out_dir: Path,
    interval: float = 10.0,
    width: int = 1280,
    duration: float | None = None,
    runner: Callable[[list[str]], Any] | None = None,
) -> list[Frame]:
    """interval 초마다 스틸컷 PNG를 저장한다. 파일명은 still_0001.png 형식.

    `runner` 를 넣으면 ffmpeg 대신 그 함수를 호출하므로, 테스트에서는
    가짜 러너로 파일만 만들어 검증할 수 있다.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if duration is None:
        duration = _probe_duration(video)
    run = runner or _default_runner
    frames: list[Frame] = []
    for index, ts in enumerate(frame_timestamps(duration, interval), start=1):
        path = out_dir / f"still_{index:04d}.png"
        run([
            "ffmpeg", "-v", "error", "-y", "-ss", f"{ts:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", f"scale='min({width},iw)':-2", "-q:v", "3", str(path),
        ])
        if path.exists():  # 영상 끝 근처에서는 프레임이 없을 수 있음
            frames.append(Frame(ts, path))
    return frames


def _default_runner(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


def _probe_duration(video: Path) -> float:
    output = subprocess.run(
        [_require("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(video)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(__import__("json").loads(output)["format"]["duration"])


def local_transcribe(video: Path, out_dir: Path, language: str = "ko") -> Path:
    """자막이 아예 없는 영상의 폴백 — 로컬 받아쓰기로 자막을 만든다.

    클라우드 API 키 없이 돌게 faster-whisper(로컬 SLM)를 쓴다. 설치가 안 되어 있으면
    설치 안내로 명확히 알리고 끝난다(조용히 빈 책을 만들지 않는다).
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "자막이 없는 영상입니다. 로컬 받아쓰기 폴백을 쓰려면 "
            "`.venv/bin/pip install faster-whisper` 로 설치하세요(모델 다운로드에 네트워크 필요, "
            "받아쓰기 자체는 로컬에서 돌아갑니다)."
        ) from error
    out_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel("small", compute_type="int8")
    segments, _info = model.transcribe(str(video), language=language, vad_filter=True)
    lines = []
    for seg in segments:
        start = format_timestamp(seg.start)
        end = format_timestamp(seg.end)
        lines.append(f"{start} --> {end}\n{seg.text.strip()}\n")
    path = out_dir / "source.vtt"
    path.write_text("WEBVTT\n\n" + "\n".join(lines), encoding="utf-8")
    return path
