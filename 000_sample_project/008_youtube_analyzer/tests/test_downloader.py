"""yt-dlp 연동 테스트. 네트워크 없이 가짜 YoutubeDL 클래스로 검증한다."""

from pathlib import Path

import pytest

from youtube_analyzer.downloader import (
    SubtitleChoice,
    VideoInfo,
    build_options,
    choose_subtitle,
    download,
    video_format,
)

FAKE_INFO = {
    "id": "abc123",
    "title": "테스트 영상",
    "uploader": "테스트 채널",
    "duration": 125,
    "upload_date": "20261101",
    "webpage_url": "https://www.youtube.com/watch?v=abc123",
    "description": "설명",
    "chapters": [{"start_time": 0, "title": "소개"}],
    "subtitles": {},
    "automatic_captions": {"ko": [{}], "en": [{}], "ko-en": [{}]},
}


class FakeYoutubeDL:
    """yt-dlp를 흉내 낸다.

    - extract_info(download=False): FAKE_INFO 반환
    - process_ie_result(download=True): 옵션에 맞춰 자막·영상 파일 생성
    """

    instances: list[dict] = []
    info: dict = FAKE_INFO

    def __init__(self, options):
        FakeYoutubeDL.instances.append(options)
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        assert download is False, "정보 조회 단계에서는 내려받지 않아야 함"
        return dict(self.info)

    def process_ie_result(self, info, download):
        out_dir = Path(self.options["outtmpl"]).parent
        for lang in self.options["subtitleslangs"]:
            (out_dir / f"source.{lang}.vtt").write_text("WEBVTT\n", encoding="utf-8")
        if not self.options["skip_download"]:
            (out_dir / "source.mp4").write_text("x")
        return info


@pytest.fixture(autouse=True)
def reset_fake():
    FakeYoutubeDL.instances = []
    yield


def test_video_info_from_ytdlp_falls_back_to_uploader():
    info = VideoInfo.from_ytdlp(FAKE_INFO)
    assert info.channel == "테스트 채널"
    assert info.duration == 125.0
    assert info.chapters == [{"start_time": 0, "title": "소개"}]


def test_video_info_handles_missing_fields():
    info = VideoInfo.from_ytdlp({"id": "x"})
    assert (info.title, info.duration, info.chapters) == ("", 0.0, [])


@pytest.mark.parametrize(
    ("info", "languages", "expected"),
    [
        # 수동 자막이 자동 자막보다 우선
        ({"subtitles": {"en": []}, "automatic_captions": {"en": []}}, ["en"], SubtitleChoice("en", False)),
        # 요청 언어 순서가 수동/자동 구분보다 우선
        ({"subtitles": {"en": []}, "automatic_captions": {"ko": []}}, ["ko", "en"], SubtitleChoice("ko", True)),
        # 자동 자막은 원어(-orig) 우선
        ({"automatic_captions": {"en": [], "en-orig": []}}, ["en"], SubtitleChoice("en-orig", True)),
        # 기계 번역본(ko-en)은 쓰지 않음
        ({"automatic_captions": {"ko-en": []}}, ["ko"], None),
        # 자막 없음
        ({}, ["ko", "en"], None),
    ],
)
def test_choose_subtitle(info, languages, expected):
    assert choose_subtitle(info, languages) == expected


def test_build_options_downloads_single_subtitle():
    options = build_options(Path("/tmp/o"), SubtitleChoice("ko", True), with_video=False, max_height=480)
    assert options["subtitleslangs"] == ["ko"]
    assert (options["writesubtitles"], options["writeautomaticsub"]) == (False, True)
    assert options["skip_download"] is True
    assert options["format"] == video_format(480)
    assert options["noplaylist"] is True


def test_build_options_without_subtitle():
    options = build_options(Path("/tmp/o"), None, with_video=True, max_height=720)
    assert options["subtitleslangs"] == []
    assert (options["writesubtitles"], options["writeautomaticsub"]) == (False, False)


def test_video_format_prefers_video_only_h264():
    """합본 포맷이 없는 영상도 받을 수 있도록 영상 전용 H.264를 먼저 고른다."""
    choices = video_format(480).split("/")
    assert choices[0] == "bestvideo[height<=480][vcodec^=avc1]"
    assert choices[-1] == "best"


def test_download_fetches_only_preferred_language(tmp_path):
    result = download("https://youtu.be/abc123", tmp_path, ["ko", "en"], ydl_class=FakeYoutubeDL)
    assert result.info.title == "테스트 영상"
    assert result.subtitle.name == "source.ko.vtt"
    assert result.video.name == "source.mp4"
    assert not (tmp_path / "source.en.vtt").exists()  # 요청 제한(429) 회피: 하나만 받음
    assert FakeYoutubeDL.instances[1]["subtitleslangs"] == ["ko"]


def test_download_without_video(tmp_path):
    result = download("https://youtu.be/abc123", tmp_path, ["en"], with_video=False, ydl_class=FakeYoutubeDL)
    assert result.subtitle.name == "source.en.vtt"
    assert result.video is None
    assert FakeYoutubeDL.instances[1]["skip_download"] is True


def test_download_no_subtitles_and_no_video_skips_second_step(tmp_path, monkeypatch):
    monkeypatch.setattr(FakeYoutubeDL, "info", {"id": "x", "title": "자막 없음"})
    result = download("https://youtu.be/x", tmp_path, ["ko"], with_video=False, ydl_class=FakeYoutubeDL)
    assert (result.subtitle, result.video) == (None, None)
    assert len(FakeYoutubeDL.instances) == 1  # 정보 조회만 하고 끝


class VideoBlockedYoutubeDL(FakeYoutubeDL):
    """영상 다운로드만 403으로 실패하는 상황(유튜브가 서버 IP를 막는 경우)."""

    def process_ie_result(self, info, download):
        if not self.options["skip_download"]:
            raise OSError("unable to download video data: HTTP Error 403: Forbidden")
        return super().process_ie_result(info, download)


def test_download_continues_with_subtitle_when_video_blocked(tmp_path):
    result = download("https://youtu.be/abc123", tmp_path, ["ko"], ydl_class=VideoBlockedYoutubeDL)
    assert result.subtitle.name == "source.ko.vtt"
    assert result.video is None
    assert any("장면 캡처를 생략" in w for w in result.warnings)


def test_download_raises_when_subtitle_only_download_fails(tmp_path):
    class Broken(FakeYoutubeDL):
        def process_ie_result(self, info, download):
            raise OSError("subtitle error")

    with pytest.raises(OSError):
        download("https://youtu.be/abc123", tmp_path, ["ko"], with_video=False, ydl_class=Broken)


def test_download_warns_when_no_subtitle(tmp_path, monkeypatch):
    monkeypatch.setattr(FakeYoutubeDL, "info", {"id": "x"})
    result = download("https://youtu.be/x", tmp_path, ["ko"], ydl_class=FakeYoutubeDL)
    assert result.subtitle is None
    assert result.video.name == "source.mp4"
    assert any("자막이 없습니다" in w for w in result.warnings)
