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


# ---- 컷 전환 감지 ----

from youtube_analyzer.frames import detect_scenes, extract_frames_at, parse_scene_times  # noqa: E402

SHOWINFO_LOG = """
[Parsed_showinfo_1 @ 0x1] n:   0 pts:  50 pts_time:2       duration:1 fmt:yuv420p
[Parsed_showinfo_1 @ 0x1] n:   1 pts: 100 pts_time:4.04    duration:1 fmt:yuv420p
frame=    2 fps=0.0 q=-0.0 Lsize=N/A time=00:00:05.96
"""


def test_parse_scene_times():
    assert parse_scene_times(SHOWINFO_LOG) == [2.0, 4.04]
    assert parse_scene_times("컷 없음") == []


@pytest.mark.parametrize("threshold", [0, 1, -0.1, 1.5])
def test_detect_scenes_rejects_bad_threshold(tmp_path, threshold):
    with pytest.raises(ValueError):
        detect_scenes(tmp_path / "x.mp4", threshold)


@pytest.fixture
def three_cut_video(tmp_path):
    """빨강(2초) → 파랑(2초) → 테스트 화면(2초): 컷 전환은 2초, 4초."""
    path = tmp_path / "cuts.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", "color=red:s=320x240:d=2:r=25",
         "-f", "lavfi", "-i", "color=blue:s=320x240:d=2:r=25",
         "-f", "lavfi", "-i", "testsrc=size=320x240:duration=2:rate=25",
         "-filter_complex", "[0][1][2]concat=n=3:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )
    return path


@needs_ffmpeg
def test_detect_scenes_finds_cuts(three_cut_video):
    assert detect_scenes(three_cut_video) == pytest.approx([2.0, 4.0], abs=0.05)


@needs_ffmpeg
def test_detect_scenes_high_threshold_finds_nothing(sample_video):
    """한 장면이 이어지는 영상(테스트 패턴)에서는 컷이 없다."""
    assert detect_scenes(sample_video, threshold=0.9) == []


@needs_ffmpeg
def test_extract_frames_at_uses_prefix(three_cut_video, tmp_path):
    frames = extract_frames_at(three_cut_video, tmp_path / "f", [2.1, 4.1], prefix="cut")
    assert [f.path.name for f in frames] == ["cut_0001.png", "cut_0002.png"]
