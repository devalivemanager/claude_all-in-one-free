"""장면 캡처 테스트. ffmpeg로 짧은 테스트 영상을 만들어 실제로 캡처한다."""

import shutil
import subprocess

import pytest

from youtube_analyzer.frames import extract_frames, frame_timestamps, probe_duration

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 필요")


@pytest.mark.parametrize(
    ("duration", "interval", "expected"),
    [
        (30, 10, [0, 10, 20]),
        (25, 10, [0, 10, 20]),
        (5, 10, [0]),
        (0, 10, []),
    ],
)
def test_frame_timestamps(duration, interval, expected):
    assert frame_timestamps(duration, interval) == expected


def test_frame_timestamps_rejects_zero_interval():
    with pytest.raises(ValueError):
        frame_timestamps(10, 0)


@pytest.fixture
def sample_video(tmp_path):
    """5초짜리 테스트 영상(색 막대 + 음성 없음)."""
    path = tmp_path / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=10",
         "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )
    return path


@needs_ffmpeg
def test_probe_duration(sample_video):
    assert probe_duration(sample_video) == pytest.approx(5.0, abs=0.2)


@needs_ffmpeg
def test_extract_frames_creates_png_per_interval(sample_video, tmp_path):
    frames = extract_frames(sample_video, tmp_path / "frames", interval=2)
    assert [f.timestamp for f in frames] == [0, 2, 4]
    assert [f.path.name for f in frames] == ["frame_0001.png", "frame_0002.png", "frame_0003.png"]
    for frame in frames:
        assert frame.path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
