"""yt-dlp 연동 테스트. 네트워크 없이 가짜 YoutubeDL 클래스로 검증한다."""

from youtube_analyzer.downloader import VideoInfo, build_options, download

FAKE_INFO = {
    "id": "abc123",
    "title": "테스트 영상",
    "uploader": "테스트 채널",
    "duration": 125,
    "upload_date": "20261101",
    "webpage_url": "https://www.youtube.com/watch?v=abc123",
    "description": "설명",
    "chapters": [{"start_time": 0, "title": "소개"}],
}


class FakeYoutubeDL:
    """yt-dlp를 흉내 내어 out_dir에 자막·영상 파일을 만든다."""

    last_options: dict = {}
    files = ("source.en.vtt", "source.ko.vtt", "source.mp4")

    def __init__(self, options):
        FakeYoutubeDL.last_options = options
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        out_dir = __import__("pathlib").Path(self.options["outtmpl"]).parent
        for name in self.files:
            if name.endswith(".mp4") and self.options["skip_download"]:
                continue
            (out_dir / name).write_text("x")
        return FAKE_INFO


def test_video_info_from_ytdlp_falls_back_to_uploader():
    info = VideoInfo.from_ytdlp(FAKE_INFO)
    assert info.channel == "테스트 채널"
    assert info.duration == 125.0
    assert info.chapters == [{"start_time": 0, "title": "소개"}]


def test_video_info_handles_missing_fields():
    info = VideoInfo.from_ytdlp({"id": "x"})
    assert (info.title, info.duration, info.chapters) == ("", 0.0, [])


def test_build_options():
    options = build_options(__import__("pathlib").Path("/tmp/o"), ["ko", "en"], with_video=False, max_height=480)
    assert options["subtitleslangs"] == ["ko", "en"]
    assert options["writeautomaticsub"] is True
    assert options["skip_download"] is True
    assert "height<=480" in options["format"]
    assert options["noplaylist"] is True


def test_download_prefers_requested_language(tmp_path):
    result = download("https://youtu.be/abc123", tmp_path, ["ko", "en"], ydl_class=FakeYoutubeDL)
    assert result.info.title == "테스트 영상"
    assert result.subtitle.name == "source.ko.vtt"
    assert result.video.name == "source.mp4"


def test_download_without_video(tmp_path):
    result = download("https://youtu.be/abc123", tmp_path, ["en"], with_video=False, ydl_class=FakeYoutubeDL)
    assert result.subtitle.name == "source.en.vtt"
    assert result.video is None
    assert FakeYoutubeDL.last_options["skip_download"] is True


def test_download_no_subtitles(tmp_path, monkeypatch):
    monkeypatch.setattr(FakeYoutubeDL, "files", ("source.mp4",))
    result = download("https://youtu.be/abc123", tmp_path, ["ko"], ydl_class=FakeYoutubeDL)
    assert result.subtitle is None
