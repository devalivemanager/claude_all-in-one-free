"""toc_generator 시험. 성희 님 대본에서 흔한 형식(제N장, N., 마크다운 #)을 그대로 본다."""

from __future__ import annotations

import unittest

from ebook_builder.toc_generator import (
    Chapter,
    chunk_by_length,
    detect_title,
    looks_like_heading,
    split_into_chapters,
)


class SplitTests(unittest.TestCase):
    def test_markdown_heading_splits(self):
        text = "# 첫째 이야기\n\n내용이다.\n\n# 둘째 이야기\n\n이어진다."
        chapters = split_into_chapters(text)
        self.assertEqual([ch.title for ch in chapters], ["첫째 이야기", "둘째 이야기"])

    def test_jang_style_heading(self):
        text = "제1장 쌀 서 말\n\n구한말 어느 겨울이었다.\n\n제2장 장승\n\n장승이 눈을 떴다."
        chapters = split_into_chapters(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "쌀 서 말")
        self.assertEqual(chapters[1].title, "장승")

    def test_number_dot_heading(self):
        text = "1. 병사의 하루\n\n새벽이었다.\n\n2. 유배길\n\n길이 멀었다."
        chapters = split_into_chapters(text)
        self.assertEqual([ch.title for ch in chapters], ["병사의 하루", "유배길"])

    def test_no_heading_becomes_one_preface(self):
        text = "제목이라 쓸 만한 줄이 없는\n그냥 이야기 원문이다.\n\n계속된다."
        chapters = split_into_chapters(text)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "서문")

    def test_shell_heading_merges_into_previous(self):
        # 본문이 너무 짧은 껍데기 제목(가운데 낀)은 앞 챕터에 합쳐진다.
        text = "# 첫 챕터\n\n" + ("본문이 충분히 길다. " * 10) \
            + "\n\n# 껍데기\n\n짧음\n\n# 끝 챕터\n\n" + ("끝까지 가는 본문이다. " * 10)
        chapters = split_into_chapters(text, min_chapter_chars=40)
        self.assertEqual(len(chapters), 2)
        self.assertIn("껍데기", chapters[0].body)
        self.assertEqual(chapters[1].title, "끝 챕터")

    def test_last_short_chapter_is_kept(self):
        # 마지막 챕터가 짧아도 합쳐서 잃어버리지 않는다.
        text = "# 첫 챕터\n\n" + ("본문이 충분히 길다. " * 10) + "\n\n# 끝\n\n짧다"
        chapters = split_into_chapters(text, min_chapter_chars=40)
        self.assertEqual([ch.title for ch in chapters], ["첫 챕터", "끝"])

    def test_empty_text_returns_empty(self):
        self.assertEqual(split_into_chapters("   \n  "), [])

    def test_table_line_is_not_heading(self):
        self.assertFalse(looks_like_heading("| 제1장 | 이런 표 줄은 |"))

    def test_source_recorded(self):
        chapters = split_into_chapters("# 가\n\n내용", source="data/ep01.txt")
        self.assertEqual(chapters[0].source, "data/ep01.txt")


class ChunkTests(unittest.TestCase):
    def test_chunk_respects_paragraph(self):
        paragraphs = "\n\n".join(f"문단 {i} " + "가" * 30 for i in range(10))
        chunks = chunk_by_length(paragraphs, max_chars=120)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 120)

    def test_long_paragraph_split_by_sentence(self):
        long_text = "첫 문장이다. " * 100  # 약 720자
        chunks = chunk_by_length(long_text, max_chars=100)
        self.assertGreater(len(chunks), 5)
        self.assertTrue(all(len(c) <= 110 for c in chunks))

    def test_invalid_max_chars(self):
        with self.assertRaises(ValueError):
            chunk_by_length("내용", max_chars=0)

    def test_chapter_with_chunks(self):
        body = "\n\n".join(["문단 " + "나" * 50] * 5)
        ch = Chapter(title="시험", body=body).with_chunks(max_chars=100)
        self.assertGreaterEqual(len(ch.chunks), 2)


class TitleTests(unittest.TestCase):
    def test_detect_h1(self):
        self.assertEqual(detect_title("머리말\n\n# 밤지기\n\n본문"), "밤지기")

    def test_detect_fallback(self):
        self.assertEqual(detect_title("제목이 없다", fallback="무제"), "무제")


if __name__ == "__main__":
    unittest.main()
