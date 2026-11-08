"""pipeline 시험 — 챕터화·이미지 매칭·원클릭 오케스트레이션을 가짜 주입으로 검증한다."""

from __future__ import annotations

import io
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from youtube_to_ebook import extractor, pipeline


def cue(start: float, end: float, text: str) -> extractor.Cue:
    return extractor.Cue(start, end, text)


def make_frame(directory: Path, timestamp: float, index: int) -> extractor.Frame:
    # epubcheck 이 깨진 이미지(PKG-021)로 보지 않도록 진짜 PNG 를 쓴다.
    path = directory / f"still_{index:04d}.png"
    path.write_bytes(tiny_png(index))
    return extractor.Frame(timestamp, path)


def tiny_png(index: int) -> bytes:
    """1×1 짜리 진짜 PNG. index 로 색을 바꿔 파일마다 내용이 다르게 한다."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    pixel = bytes([0, index % 256, (index * 7) % 256, (index * 13) % 256])  # 필터 0 + RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixel))
        + chunk(b"IEND", b"")
    )


class ChaptersFromCuesTest(unittest.TestCase):
    def test_grouped_by_interval(self):
        cues = [cue(0, 10, "첫"), cue(30, 40, "둘"), cue(70, 80, "셋")]
        sections = pipeline.chapters_from_cues(cues, interval=60)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].body, "첫\n\n둘")
        self.assertEqual(sections[1].body, "셋")

    def test_title_has_timestamps(self):
        sections = pipeline.chapters_from_cues([cue(0, 30, "본문")], interval=60)
        self.assertEqual(sections[0].title, "제1화 (00:00:00–00:00:30)")

    def test_section_time_bounds(self):
        cues = [cue(0, 10, "첫"), cue(60, 70, "둘")]
        sections = pipeline.chapters_from_cues(cues, interval=60)
        self.assertEqual(sections[0].start, 0.0)
        self.assertEqual(sections[1].start, 60.0)

    def test_bad_interval(self):
        with self.assertRaises(ValueError):
            pipeline.chapters_from_cues([cue(0, 1, "x")], interval=0)

    def test_empty(self):
        self.assertEqual(pipeline.chapters_from_cues([], interval=60), [])


class ChaptersFromYoutubeChaptersTest(unittest.TestCase):
    def test_uses_official_chapters(self):
        cues = [cue(0, 10, "첫"), cue(60, 70, "둘"), cue(120, 130, "셋")]
        chapters = [
            {"start_time": 0, "end_time": 60, "title": "서장"},
            {"start_time": 60, "end_time": 0, "title": "본문"},
        ]
        sections = pipeline.chapters_from_youtube_chapters(cues, chapters)
        self.assertEqual([s.title for s in sections], ["서장", "본문"])
        self.assertEqual(sections[0].body, "첫")
        self.assertEqual(sections[1].body, "둘\n\n셋")

    def test_none_when_absent(self):
        self.assertIsNone(pipeline.chapters_from_youtube_chapters([cue(0, 1, "x")], []))


class MatchFramesTest(unittest.TestCase):
    def test_frames_assigned_to_right_chapter(self):
        sections = pipeline.chapters_from_cues(
            [cue(0, 30, "첫"), cue(60, 90, "둘")], interval=60
        )
        # 챕터 end 는 마지막 큐 끝(30·90)이므로 0초 컷은 1챕터, 60초 컷은 2챕터로 간다.
        with tempfile.TemporaryDirectory() as tmp:
            frames = [
                make_frame(Path(tmp), 0.0, 1),
                make_frame(Path(tmp), 60.0, 2),
                make_frame(Path(tmp), 200.0, 3),  # 마지막 챕터 end 넘어도 마지막 챕터로 본다
            ]
            result = pipeline.match_frames(sections, frames)
            self.assertEqual(len(result[0].images), 1)
            self.assertEqual(len(result[1].images), 2)

    def test_no_frames(self):
        sections = pipeline.chapters_from_cues([cue(0, 30, "첫")], interval=60)
        result = pipeline.match_frames(sections, [])
        self.assertEqual(result[0].images, [])


class BuildBookTest(unittest.TestCase):
    """가짜 외부 연결을 주입해 원클릭 흐름 전체를 네트워크 없이 검증한다."""

    INFO = {"title": "밤지기 옛이야기 1화", "channel": "밤지기 옛이야기", "chapters": []}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "out"
        self.subtitle = Path(self.tmp.name) / "source.vtt"
        self.subtitle.write_text(
            "00:00:00.000 --> 00:00:30.000\n첫 문장\n\n"
            "00:01:00.000 --> 00:01:30.000\n둘째 문장\n",
            encoding="utf-8",
        )
        self.video = Path(self.tmp.name) / "source.mp4"
        self.video.write_bytes(b"fake video")
        self.frames_dir = Path(self.tmp.name) / "frames"

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, formats=("html", "epub"), video=True):
        def fake_subtitle(url, out_dir, langs):
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / "source.vtt"
            target.write_text(self.subtitle.read_text(encoding="utf-8"), encoding="utf-8")
            return target

        def fake_capture(video_path, frames_dir, interval, width):
            frames_dir.mkdir(parents=True, exist_ok=True)
            return [make_frame(frames_dir, 10.0, 1), make_frame(frames_dir, 70.0, 2)]

        return pipeline.build_book(
            url="https://youtu.be/abc",
            out_dir=self.out,
            formats=formats,
            fetch_info=lambda url: dict(self.INFO),
            download_subtitle=fake_subtitle,
            download_video=lambda url, out_dir: self.video if video else None,
            capture=fake_capture,
        )

    def test_full_flow_html_and_epub(self):
        # download_subtitle 주입이 out_dir 를 그대로 돌려주므로 파일을 옮겨 둔다
        def fake_subtitle(url, out_dir, langs):
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / "source.vtt"
            target.write_text(self.subtitle.read_text(encoding="utf-8"), encoding="utf-8")
            return target

        result = pipeline.build_book(
            url="https://youtu.be/abc",
            out_dir=self.out,
            fetch_info=lambda url: dict(self.INFO),
            download_subtitle=fake_subtitle,
            download_video=lambda url, out_dir: self.video,
            capture=lambda video, frames_dir, interval, width: (
                frames_dir.mkdir(parents=True, exist_ok=True),
                [make_frame(frames_dir, 10.0, 1), make_frame(frames_dir, 70.0, 2)],
            )[1],
        )
        self.assertEqual(result.chapters, 2)
        self.assertEqual(result.frames, 2)
        self.assertEqual(result.warnings, [])
        self.assertIn("html", result.outputs)
        self.assertIn("epub", result.outputs)
        self.assertTrue(result.outputs["html"].exists())
        self.assertTrue(result.outputs["epub"].exists())
        # 스틸컷 2장이 EPUB 에 실제로 들어가고, 리더가 여는 길잡이(container.xml)도 있다.
        zf = zipfile.ZipFile(io.BytesIO(result.outputs["epub"].read_bytes()))
        self.assertIn("META-INF/container.xml", zf.namelist())
        self.assertEqual(len([n for n in zf.namelist() if n.startswith("images/")]), 2)

    def test_html_only(self):
        result = self.build(formats=("html",))
        self.assertIn("html", result.outputs)
        self.assertNotIn("epub", result.outputs)

    def test_no_video_still_builds_text_only(self):
        def fake_subtitle(url, out_dir, langs):
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / "source.vtt"
            target.write_text(self.subtitle.read_text(encoding="utf-8"), encoding="utf-8")
            return target

        result = pipeline.build_book(
            url="https://youtu.be/abc",
            out_dir=self.out,
            fetch_info=lambda url: dict(self.INFO),
            download_subtitle=fake_subtitle,
            download_video=lambda url, out_dir: None,
        )
        self.assertEqual(result.frames, 0)
        self.assertTrue(any("스틸컷" in w for w in result.warnings))
        self.assertTrue(result.outputs["epub"].exists())

    def test_no_subtitle_stops_with_warning(self):
        result = pipeline.build_book(
            url="https://youtu.be/abc",
            out_dir=self.out,
            fetch_info=lambda url: dict(self.INFO),
            download_subtitle=lambda url, out_dir, langs: None,
            download_video=lambda url, out_dir: self.video,
        )
        self.assertEqual(result.outputs, {})
        self.assertTrue(any("자막" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
