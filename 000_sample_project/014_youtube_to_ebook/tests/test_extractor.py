"""extractor 시험 — 네트워크·ffmpeg 없이 가짜 주입으로 검증한다."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from youtube_to_ebook import extractor


VTT = """WEBVTT

00:00:00.000 --> 00:00:04.000
< c>옛날 옛적에<00:00:01.000><c> 어느 마을에</c>

00:00:04.000 --> 00:00:08.000
어느 마을에 늙은 나무꾼이 살았다

00:00:08.000 --> 00:01:00.000
그러던 어느 날
"""

SRT = """1
00:00:00,000 --> 00:00:04,000
첫 문장입니다

2
00:00:04,000 --> 00:00:08,000
둘째 문장입니다
"""


class ParseTimestampTest(unittest.TestCase):
    def test_vtt_timestamp(self):
        self.assertEqual(extractor.parse_timestamp("00:01:02.345"), 62.345)

    def test_srt_timestamp_with_comma(self):
        self.assertEqual(extractor.parse_timestamp("01:02,345"), 62.345)

    def test_short_timestamp(self):
        self.assertEqual(extractor.parse_timestamp("01:02.500"), 62.5)

    def test_bad_timestamp_raises(self):
        with self.assertRaises(ValueError):
            extractor.parse_timestamp("몇 분")


class FormatTimestampTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(extractor.format_timestamp(83), "00:01:23")


class ParseSubtitlesTest(unittest.TestCase):
    def test_vtt_tags_and_rolling(self):
        cues = extractor.parse_subtitles(VTT)
        self.assertEqual(len(cues), 3)
        self.assertEqual(cues[0].start, 0.0)
        self.assertEqual(cues[0].text, "옛날 옛적에 어느 마을에")

    def test_srt_comma_separator(self):
        cues = extractor.parse_subtitles(SRT)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1].text, "둘째 문장입니다")

    def test_empty_blocks_ignored(self):
        self.assertEqual(extractor.parse_subtitles(""), [])


class DeduplicateTest(unittest.TestCase):
    def test_rolling_tail_only(self):
        cues = [
            extractor.Cue(0, 4, "옛날 옛적에 어느 마을에"),
            extractor.Cue(2, 6, "어느 마을에 늙은 나무꾼이 살았다"),
        ]
        result = extractor.deduplicate(cues)
        self.assertEqual([c.text for c in result], ["옛날 옛적에 어느 마을에", "늙은 나무꾼이 살았다"])

    def test_exact_repeat_dropped(self):
        cues = [
            extractor.Cue(0, 4, "같은 말"),
            extractor.Cue(4, 8, "같은 말"),
        ]
        self.assertEqual(len(extractor.deduplicate(cues)), 1)

    def test_load_transcript_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.vtt"
            path.write_text(SRT, encoding="utf-8")
            cues = extractor.load_transcript(path)
            self.assertEqual(len(cues), 2)


class ChooseSubtitleTest(unittest.TestCase):
    def test_manual_first(self):
        info = {"subtitles": {"ko": []}, "automatic_captions": {"ko-orig": []}}
        choice = extractor.choose_subtitle(info, ["ko"])
        self.assertEqual((choice.language, choice.automatic), ("ko", False))

    def test_automatic_orig_next(self):
        info = {"automatic_captions": {"ko-orig": [], "ko-en": []}}
        choice = extractor.choose_subtitle(info, ["ko"])
        self.assertEqual((choice.language, choice.automatic), ("ko-orig", True))

    def test_none(self):
        self.assertIsNone(extractor.choose_subtitle({"subtitles": {}}, ["ko"]))


class FakeYdl:
    """네트워크 없이 yt-dlp 를 흉내낸 가짜."""

    calls: list[dict] = []

    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def extract_info(self, url, download=False):
        return {"id": "abc", "title": "시험 영상", "subtitles": {"ko": []}}

    def process_ie_result(self, info, download=True):
        FakeYdl.calls.append(dict(self.options))
        out = Path(self.options["outtmpl"])  # source.%(ext)s
        out.with_suffix(".vtt").write_text(SRT, encoding="utf-8")


class DownloadSubtitleTest(unittest.TestCase):
    def test_writes_subtitle_file(self):
        FakeYdl.calls = []
        with tempfile.TemporaryDirectory() as tmp:
            path = extractor.download_subtitle(
                "https://youtu.be/abc", Path(tmp), ["ko"], ydl_class=FakeYdl
            )
            self.assertIsNotNone(path)
            self.assertEqual(path.suffix, ".vtt")
            self.assertTrue(path.exists())


class FrameTimestampsTest(unittest.TestCase):
    def test_intervals(self):
        self.assertEqual(extractor.frame_timestamps(25, 10), [0.0, 10.0, 20.0])

    def test_exact_duration(self):
        self.assertEqual(extractor.frame_timestamps(20, 10), [0.0, 10.0])

    def test_bad_interval(self):
        with self.assertRaises(ValueError):
            extractor.frame_timestamps(10, 0)


class CaptureFramesTest(unittest.TestCase):
    def test_fake_runner_creates_files(self):
        def fake_runner(command):
            Path(command[-1]).write_bytes(b"\x89PNG\r\n\x1a\nfake")

        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "source.mp4"
            video.write_bytes(b"fake video")
            frames = extractor.capture_frames(
                video, Path(tmp) / "frames", interval=10, duration=25, runner=fake_runner
            )
            self.assertEqual(len(frames), 3)
            self.assertEqual(frames[0].timestamp, 0.0)
            self.assertEqual(frames[0].path.name, "still_0001.png")
            self.assertTrue(frames[2].path.exists())


class LocalTranscribeFallbackTest(unittest.TestCase):
    def test_clear_error_without_faster_whisper(self):
        try:
            import faster_whisper  # noqa: F401

            self.skipTest("faster-whisper 가 설치되어 있어 오류 경로를 시험할 수 없다")
        except ImportError:
            pass
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError) as ctx:
                extractor.local_transcribe(Path(tmp) / "video.mp4", Path(tmp))
            self.assertIn("faster-whisper", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
