"""ebook 시험 — 삽화 HTML 뷰어와 EPUB 이미지 번들링을 검증한다."""

from __future__ import annotations

import base64
import tempfile
import unittest
import zipfile
from pathlib import Path

from youtube_to_ebook import ebook, extractor, pipeline


def make_section(title: str, body: str, frames: list[extractor.Frame]) -> pipeline.Section:
    return pipeline.Section(title=title, body=body, images=frames)


def make_frame(directory: Path, timestamp: float, index: int) -> extractor.Frame:
    path = directory / f"still_{index:04d}.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake image data " + str(index).encode())
    return extractor.Frame(timestamp, path)


class BookMetaTest(unittest.TestCase):
    def test_defaults(self):
        meta = ebook.BookMeta(title="책")
        self.assertEqual(meta.author, "")
        self.assertEqual(meta.subtitle, "")


class ValidateTest(unittest.TestCase):
    def test_empty_title_raises(self):
        with self.assertRaises(ValueError):
            ebook.build_html(ebook.BookMeta(title="  "), [])

    def test_empty_sections_raises(self):
        with self.assertRaises(ValueError):
            ebook.build_html(ebook.BookMeta(title="책"), [])


class BuildHtmlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_images_embedded_as_data_uri(self):
        frame = make_frame(self.tmp_path, 10.0, 1)
        meta = ebook.BookMeta(title="시험 책", author="데브얼라이브")
        html = ebook.build_html(meta, [make_section("제1화", "첫 문단\n\n둘째 문단", [frame])])
        self.assertIn("data:image/png;base64,", html)
        encoded = base64.b64encode(b"\x89PNG\r\n\x1a\nfake image data 1").decode("ascii")
        self.assertIn(encoded, html)

    def test_caption_shown(self):
        frame = make_frame(self.tmp_path, 83.0, 1)
        html = ebook.build_html(ebook.BookMeta(title="책"), [make_section("제1화", "본문", [frame])])
        self.assertIn("00:01:23 장면", html)

    def test_single_file_no_external_refs(self):
        frame = make_frame(self.tmp_path, 0.0, 1)
        html = ebook.build_html(ebook.BookMeta(title="책"), [make_section("제1화", "본문", [frame])])
        self.assertNotIn('src="images/', html)  # 외부 파일 참조가 아닌 데이터 URI 로만
        self.assertIn("<!DOCTYPE html>", html)

    def test_toc_and_chapters(self):
        html = ebook.build_html(
            ebook.BookMeta(title="책"),
            [make_section("제1화", "본문1", []), make_section("제2화", "본문2", [])],
        )
        self.assertIn('href="#ch-0"', html)
        self.assertIn("제2화", html)

    def test_text_escaped(self):
        html = ebook.build_html(
            ebook.BookMeta(title="책"), [make_section("제1화", "<script>alert(1)</script>", [])]
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class BuildEpubTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def epub_of(self, sections):
        return ebook.build_epub(ebook.BookMeta(title="시험 책"), sections)

    def test_mimetype_first_and_stored(self):
        data = self.epub_of([make_section("제1화", "본문", [])])
        zf = zipfile.ZipFile(__import__("io").BytesIO(data))
        first = zf.infolist()[0]
        self.assertEqual(first.filename, "mimetype")
        self.assertEqual(first.compress_type, zipfile.ZIP_STORED)
        self.assertEqual(zf.read("mimetype"), b"application/epub+zip")

    def test_images_bundled_and_manifest_registered(self):
        frames = [make_frame(self.tmp_path, 0.0, 1), make_frame(self.tmp_path, 70.0, 2)]
        sections = [make_section("제1화", "본문", frames)]
        data = self.epub_of(sections)
        zf = zipfile.ZipFile(__import__("io").BytesIO(data))
        images = [n for n in zf.namelist() if n.startswith("images/")]
        self.assertEqual(len(images), 2)
        package = zf.read("package.opf").decode("utf-8")
        for name in images:
            self.assertIn(f'href="{name}"', package)

    def test_xhtml_references_bundled_image(self):
        frame = make_frame(self.tmp_path, 0.0, 1)
        data = self.epub_of([make_section("제1화", "본문", [frame])])
        zf = zipfile.ZipFile(__import__("io").BytesIO(data))
        chapter = zf.read("ch0.xhtml").decode("utf-8")
        self.assertIn('src="images/img_0000.png"', chapter)
        self.assertIn("00:00:00 장면", chapter)

    def test_nav_and_spine(self):
        sections = [make_section("제1화", "본문1", []), make_section("제2화", "본문2", [])]
        data = self.epub_of(sections)
        zf = zipfile.ZipFile(__import__("io").BytesIO(data))
        nav = zf.read("nav.xhtml").decode("utf-8")
        self.assertIn("제2화", nav)
        package = zf.read("package.opf").decode("utf-8")
        self.assertIn('<itemref idref="ch0"/>', package)
        self.assertIn('<itemref idref="ch1"/>', package)

    def test_missing_image_file_skipped(self):
        frame = extractor.Frame(timestamp=0.0, path=self.tmp_path / "없는_파일.png")
        data = self.epub_of([make_section("제1화", "본문", [frame])])
        zf = zipfile.ZipFile(__import__("io").BytesIO(data))
        self.assertEqual([n for n in zf.namelist() if n.startswith("images/")], [])


class WriteOutputsTest(unittest.TestCase):
    def test_writes_requested_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            written = ebook.write_outputs(
                ebook.BookMeta(title="책"),
                [make_section("제1화", "본문", [])],
                out,
                ("html", "epub"),
            )
            self.assertEqual(set(written), {"html", "epub"})
            self.assertTrue(written["html"].exists())
            self.assertTrue(written["epub"].exists())

    def test_html_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = ebook.write_outputs(
                ebook.BookMeta(title="책"), [make_section("제1화", "본문", [])], Path(tmp), ("html",)
            )
            self.assertEqual(set(written), {"html"})


if __name__ == "__main__":
    unittest.main()
