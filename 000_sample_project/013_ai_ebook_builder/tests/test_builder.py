"""builder 와 CLI 시험. 네 가지 산출물이 실제로 만들어지고 규격을 지키는지 본다."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from xml.etree import ElementTree

from ebook_builder.builder import (
    BookMeta,
    STYLE_PRESETS,
    build_epub,
    build_html,
    build_print_html,
    build_webbook_zip,
)
from ebook_builder.cli import main
from ebook_builder.toc_generator import split_into_chapters

SAMPLE = """# 첫째 이야기

구한말, 한양의 밤이었다.

> 도깨비불이 밤마다 돌았다.

# 둘째 이야기

흑등은 칼을 갈았다.

- 갈린 칼은 세 자
- 남은 밤은 두 시진
"""


def meta(**kwargs) -> BookMeta:
    defaults = dict(title="밤지기 옛이야기", subtitle="1~2편", author="데브얼라이브", preset="novel")
    defaults.update(kwargs)
    return BookMeta(**defaults)


class HtmlTests(unittest.TestCase):
    def test_single_html_contains_chapters(self):
        html = build_html(meta(), split_into_chapters(SAMPLE))
        self.assertIn("첫째 이야기", html)
        self.assertIn("둘째 이야기", html)
        self.assertIn("<!DOCTYPE html>", html)

    def test_html_has_no_secret_place(self):
        # API 키 같은 비밀값이 문서에 들어갈 자리가 아예 없어야 한다.
        html = build_html(meta(), split_into_chapters(SAMPLE))
        self.assertNotIn("API_KEY", html.replace("API_KEY가 없다", ""))

    def test_escape_in_body(self):
        html = build_html(meta(), split_into_chapters("# 제\n\n본문에 <script> 위험"))
        self.assertNotIn("본문에 <script>", html)  # 본문의 script 는 문자로 보여야 한다
        self.assertIn("본문에 &lt;script&gt; 위험", html)

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            build_html(meta(title=""), split_into_chapters(SAMPLE))

    def test_no_chapters_rejected(self):
        with self.assertRaises(ValueError):
            build_html(meta(), [])


class PrintTests(unittest.TestCase):
    def test_page_break_per_chapter(self):
        html = build_print_html(meta(), split_into_chapters(SAMPLE))
        # CSS 규칙은 한 번이고, 챕터마다 h1 이 그 페이지 나눔을 받는다.
        self.assertIn("h1 { page-break-before: always; break-after: avoid; }", html)
        self.assertIn("break-inside: avoid", html)
        self.assertEqual(html.count('<section class="chapter"'), 2)


class EpubTests(unittest.TestCase):
    def test_epub_structure(self):
        data = build_epub(meta(), split_into_chapters(SAMPLE))
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        self.assertEqual(names[0], "mimetype")
        self.assertEqual(zf.read("mimetype"), b"application/epub+zip")
        info = zf.getinfo("mimetype")
        self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
        package = zf.read("package.opf").decode()
        self.assertIn("<dc:title>밤지기 옛이야기</dc:title>", package)
        nav = zf.read("nav.xhtml").decode()
        self.assertIn("첫째 이야기", nav)
        # 챕터 파일이 챕터 수만큼
        self.assertEqual(sum(1 for n in names if n.startswith("ch") and n.endswith(".xhtml")), 2)

    def test_epub_chapters_are_valid_xml(self):
        data = build_epub(meta(), split_into_chapters(SAMPLE))
        zf = zipfile.ZipFile(io.BytesIO(data))
        for name in zf.namelist():
            if name.endswith(".xhtml"):
                ElementTree.fromstring(zf.read(name))

    def test_style_presets_ten(self):
        self.assertEqual(len(STYLE_PRESETS), 10)
        for key in ("novel", "classic", "night", "tech"):
            self.assertIn(key, STYLE_PRESETS)


class WebbookTests(unittest.TestCase):
    def test_webbook_zip_manifest(self):
        data = build_webbook_zip(meta(), split_into_chapters(SAMPLE))
        zf = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(zf.read("book.json"))
        self.assertEqual(manifest["format"], "devalive-webbook/1")
        self.assertEqual(len(manifest["chapters"]), 2)
        index = zf.read("index.html").decode()
        self.assertIn("밤지기 옛이야기", index)


class CliTests(unittest.TestCase):
    def test_build_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "ep01.txt"
            src.write_text(SAMPLE, encoding="utf-8")
            out = Path(tmp) / "output"
            code = main(
                [
                    "build",
                    str(src),
                    "--title",
                    "단 한 줄 빌드",
                    "--author",
                    "데브얼라이브",
                    "--preset",
                    "classic",
                    "--outdir",
                    str(out),
                ]
            )
            self.assertEqual(code, 0)
            produced = {p.name for p in out.iterdir()}
            self.assertLessEqual(
                {"viewer.html", "print.html", "book.epub", "webbook.zip", "cover.svg", "toc.md"},
                produced,
            )
            self.assertIn("단 한 줄 빌드", (out / "viewer.html").read_text(encoding="utf-8"))
            self.assertTrue((out / "book.epub").read_bytes().startswith(b"PK"))

    def test_presets_command(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["presets"])
        self.assertEqual(code, 0)
        self.assertIn("novel", buffer.getvalue())

    def test_no_inputs_fails_cleanly(self):
        with self.assertRaises(SystemExit):
            main(["build"])


if __name__ == "__main__":
    unittest.main()
