"""ffmpeg로 영상에서 일정 간격마다 장면(프레임)을 캡처한다."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FfmpegNotFoundError(RuntimeError):
    """ffmpeg/ffprobe가 설치되어 있지 않을 때."""


@dataclass(frozen=True)
class Frame:
    """캡처한 장면 한 장."""

    timestamp: float  # 영상 내 위치(초)
    path: Path


def _require(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        raise FfmpegNotFoundError(f"{tool}을(를) 찾을 수 없습니다. ffmpeg를 설치하세요.")
    return found


def probe_duration(video: Path) -> float:
    """ffprobe로 영상 길이(초)를 구한다."""
    output = subprocess.run(
        [_require("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return float(json.loads(output)["format"]["duration"])


def frame_timestamps(duration: float, interval: float) -> list[float]:
    """0초부터 interval 간격의 캡처 시점 목록(영상 길이 미만)."""
    if interval <= 0:
        raise ValueError("interval은 0보다 커야 합니다")
    count = int(duration // interval) + (1 if duration % interval else 0)
    return [i * interval for i in range(count)]


def extract_frames(video: Path, out_dir: Path, interval: float = 10.0, width: int = 1280) -> list[Frame]:
    """interval초마다 PNG를 저장한다. 파일명은 frame_0001.png 형식.

    시점마다 ffmpeg를 따로 호출(-ss 앞쪽 탐색)하므로 긴 영상도 빠르다.
    """
    ffmpeg = _require("ffmpeg")
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Frame] = []
    for index, ts in enumerate(frame_timestamps(probe_duration(video), interval), start=1):
        path = out_dir / f"frame_{index:04d}.png"
        subprocess.run(
            [ffmpeg, "-v", "error", "-y", "-ss", f"{ts:.3f}", "-i", str(video),
             "-frames:v", "1", "-vf", f"scale='min({width},iw)':-2", str(path)],
            check=True,
            capture_output=True,
        )
        if path.exists():  # 영상 끝 근처에서는 프레임이 없을 수 있음
            frames.append(Frame(ts, path))
    return frames
