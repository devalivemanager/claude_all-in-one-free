"""보고서 생성과 CLI 전체 흐름 테스트."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from youtube_analyzer import cli, downloader
from youtube_analyzer.frames import Frame
from youtube_analyzer.report import build_report, build_transcript_text
from youtube_analyzer.subtitles import Cue

from .test_downloader import FakeYoutubeDL


def test_build_report_groups_transcript_and_frames_by_section(tmp_path):
    info = downloader.VideoInfo(
        video_id="abc", title="강의", channel="채널", duration=130, url="https://youtu.be/abc",
        chapters=[{"start_time": 60, "title": "본론"}],
    )
    transcript = [Cue(5, 8, "도입"), Cue(65, 70, "본론 시작")]
    frames = [Frame(0, tmp_path / "frames" / "frame_0001.png"), Frame(60, tmp_path / "frames" / "frame_0002.png")]

    text = build_report(info, transcript, frames, tmp_path, section_seconds=60)

    assert text.startswith("# 강의\n")
    assert "- **길이**: 00:02:10" in text
    assert "- `00:01:00` 본론" in text
    first = text.index("### 00:00:00 ~ 00:01:00")
    second = text.index("### 00:01:00 ~ 00:02:00")
    assert first < text.index("`00:00:05` 도입") < text.index("frames/frame_0001.png") < second
    assert second < text.index("`00:01:05` 본론 시작") < text.index("frames/frame_0002.png")


def test_build_report_without_transcript_shows_notice(tmp_path):
    text = build_report(downloader.VideoInfo("x", ""), [], [], tmp_path)
    assert "# (제목 없음)" in text
    assert "자막을 찾지 못했습니다" in text


def test_build_transcript_text():
    assert build_transcript_text([Cue(61, 62, "안녕")]) == "[00:01:01] 안녕\n"


def test_cli_requires_input(capsys):
    with pytest.raises(SystemExit):
        cli.main([])
    assert "필요합니다" in capsys.readouterr().err


def test_cli_rejects_url_with_local_file(tmp_path, capsys):
    sub = tmp_path / "a.vtt"
    sub.write_text("WEBVTT")
    with pytest.raises(SystemExit):
        cli.main(["https://youtu.be/x", "--subtitle", str(sub)])
    assert "함께 쓸 수 없습니다" in capsys.readouterr().err


def test_cli_rejects_missing_file(tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli.main(["--video", str(tmp_path / "none.mp4")])
    assert "파일이 없습니다" in capsys.readouterr().err


def test_cli_url_flow_with_fake_downloader(tmp_path, monkeypatch):
    """URL 경로: 내려받기 → 자막 파싱 → 보고서. 장면은 생략."""
    monkeypatch.setattr(downloader, "_default_ydl_class", lambda: FakeYoutubeDL)

    def process_with_subtitle(self, info, download):
        out = Path(self.options["outtmpl"]).parent
        (out / "source.ko.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n안녕하세요\n", encoding="utf-8")
        return info

    monkeypatch.setattr(FakeYoutubeDL, "process_ie_result", process_with_subtitle)

    assert cli.main(["https://youtu.be/abc123", "-o", str(tmp_path), "--no-frames"]) == 0
    assert "[00:00:01] 안녕하세요" in (tmp_path / "transcript.txt").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "info.json").read_text(encoding="utf-8"))["title"] == "테스트 영상"
    assert "# 테스트 영상" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_cli_reports_download_error(tmp_path, monkeypatch, capsys):
    class BrokenYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url, download):
            raise OSError("Tunnel connection failed: 403 Forbidden")

    monkeypatch.setattr(downloader, "_default_ydl_class", lambda: BrokenYoutubeDL)
    assert cli.main(["https://youtu.be/x", "-o", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "403 Forbidden" in err
    assert "www.youtube.com" in err  # 네트워크 허용 안내


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 필요")
def test_cli_local_files_end_to_end(tmp_path):
    """로컬 영상 + 자막으로 전체 흐름을 실제 실행한다."""
    video = tmp_path / "lecture.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=10",
         "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    subtitle = tmp_path / "lecture.srt"
    subtitle.write_text("1\n00:00:00,500 --> 00:00:02,000\n첫 장면 설명\n", encoding="utf-8")
    out = tmp_path / "out"

    code = cli.main(["--video", str(video), "--subtitle", str(subtitle), "--title", "로컬 강의",
                     "-o", str(out), "--interval", "2"])

    assert code == 0
    report_md = (out / "report.md").read_text(encoding="utf-8")
    assert "# 로컬 강의" in report_md
    assert "`00:00:00` 첫 장면 설명" in report_md
    assert "![00:00:02 장면](frames/frame_0002.png)" in report_md
    assert sorted(p.name for p in (out / "frames").iterdir()) == ["frame_0001.png", "frame_0002.png"]
