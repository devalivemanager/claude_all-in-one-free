"""cover_generator 시험. 결정론성(같은 입력 → 같은 표지)과 한글 제목을 본다."""

from __future__ import annotations

import unittest
from xml.etree import ElementTree

from ebook_builder.cover_generator import CoverSpec, generate_cover_svg


class CoverTests(unittest.TestCase):
    def test_valid_svg(self):
        svg = generate_cover_svg(CoverSpec(title="밤지기", subtitle="흑등의 기록", author="데브얼라이브"))
        ElementTree.fromstring(svg)  # XML 로 잘 들어가는지

    def test_deterministic(self):
        spec = CoverSpec(title="밤지기", seed="고정씨앗")
        self.assertEqual(generate_cover_svg(spec), generate_cover_svg(spec))

    def test_seed_changes_picture(self):
        a = generate_cover_svg(CoverSpec(title="같은 책", seed="하나"))
        b = generate_cover_svg(CoverSpec(title="같은 책", seed="둘"))
        self.assertNotEqual(a, b)

    def test_long_title_wraps_and_truncates(self):
        svg = generate_cover_svg(CoverSpec(title="너무 길어서 세 줄을 넘는 제목 " * 5))
        ElementTree.fromstring(svg)
        self.assertNotIn("……", svg)  # 줄임표는 한 번만

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            generate_cover_svg(CoverSpec(title="  "))

    def test_unknown_preset_falls_back(self):
        a = generate_cover_svg(CoverSpec(title="책", preset="없는것"))
        b = generate_cover_svg(CoverSpec(title="책", preset="novel"))
        self.assertEqual(a, b)

    def test_special_chars_escaped(self):
        svg = generate_cover_svg(CoverSpec(title="<출간> & \"판형\""))
        self.assertIn("&lt;출간&gt;", svg)
        ElementTree.fromstring(svg)


if __name__ == "__main__":
    unittest.main()
