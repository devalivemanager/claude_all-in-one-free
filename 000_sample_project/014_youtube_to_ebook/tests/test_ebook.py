"""ebook 시험 — 삽화 HTML 뷰어와 EPUB 이미지 번들링을 검증한다."""

from __future__ import annotations

import base64
import io
import re
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree

from youtube_to_ebook import ebook, extractor, pipeline

OPF_NS = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
UUID4 = re.compile(r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def make_section(title: str, body: str, frames: list[extractor.Frame]) -> pipeline.Section:
    return pipeline.Section(title=title, body=body, images=frames)


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
        encoded = base64.b64encode(tiny_png(1)).decode("ascii")
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
        # 없는 이미지는 매니페스트·본문에서도 빠져야 한다(없는 파일 참조는 epubcheck ERROR).
        self.assertNotIn("images/", zf.read("package.opf").decode("utf-8"))
        self.assertNotIn("<img", zf.read("ch0.xhtml").decode("utf-8"))

    def test_corrupt_image_skipped(self):
        # PNG 가 아닌(깨진) 캡처는 넣지 않는다(epubcheck PKG-021 ERROR). 멀쩡한 컷은 남긴다.
        broken = self.tmp_path / "broken.png"
        broken.write_bytes(b"\x89PNG\r\n\x1a\nfake image data")
        good = make_frame(self.tmp_path, 70.0, 2)
        sections = [make_section("제1화", "본문", [extractor.Frame(0.0, broken), good])]
        zf = zipfile.ZipFile(io.BytesIO(self.epub_of(sections)))
        self.assertEqual([n for n in zf.namelist() if n.startswith("images/")], ["images/img_0000.png"])
        self.assertEqual(zf.read("images/img_0000.png"), tiny_png(2))
        self.assertEqual(zf.read("ch0.xhtml").decode("utf-8").count("<img"), 1)
        html = ebook.build_html(ebook.BookMeta(title="책"), sections)
        self.assertEqual(html.count("<img"), 1)
        self.assertNotIn("00:00:00 장면", html)

    def test_has_container_xml(self):
        # container.xml 이 없으면 리더가 package.opf 를 못 찾는다(epubcheck RSC-002 FATAL).
        zf = zipfile.ZipFile(io.BytesIO(self.epub_of([make_section("제1화", "본문", [])])))
        names = zf.namelist()
        self.assertEqual(names[0], "mimetype")
        self.assertIn("META-INF/container.xml", names)
        root = ElementTree.fromstring(zf.read("META-INF/container.xml"))
        rootfiles = root.findall("c:rootfiles/c:rootfile", CONTAINER_NS)
        self.assertEqual(len(rootfiles), 1)
        self.assertEqual(rootfiles[0].get("full-path"), "package.opf")
        self.assertEqual(rootfiles[0].get("media-type"), "application/oebps-package+xml")
        self.assertIn("package.opf", names)

    def test_no_empty_metadata(self):
        # 저자·부제가 비면 dc:creator·dc:description 을 쓰지 않는다(빈 태그는 RSC-005 ERROR).
        data = ebook.build_epub(ebook.BookMeta(title="책"), [make_section("제1화", "본문", [])])
        package = ElementTree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("package.opf"))
        for tag in ("dc:creator", "dc:description"):
            self.assertEqual(package.findall(f"opf:metadata/{tag}", OPF_NS), [], tag)
        for element in package.find("opf:metadata", OPF_NS):
            if element.tag.startswith("{" + OPF_NS["dc"]):
                self.assertTrue((element.text or "").strip(), element.tag)

    def test_filled_metadata_kept(self):
        meta = ebook.BookMeta(title="책", subtitle="1화", author="데브얼라이브")
        data = ebook.build_epub(meta, [make_section("제1화", "본문", [])])
        package = ElementTree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("package.opf"))
        self.assertEqual(package.find("opf:metadata/dc:creator", OPF_NS).text, "데브얼라이브")
        self.assertEqual(package.find("opf:metadata/dc:description", OPF_NS).text, "1화")

    def test_identifier_is_uuid(self):
        data = self.epub_of([make_section("제1화", "본문", [])])
        package = ElementTree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("package.opf"))
        uid = package.find("opf:metadata/dc:identifier", OPF_NS).text
        self.assertRegex(uid, UUID4)
        again = self.epub_of([make_section("제1화", "본문", [])])
        self.assertIn(uid, zipfile.ZipFile(io.BytesIO(again)).read("package.opf").decode("utf-8"))


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
