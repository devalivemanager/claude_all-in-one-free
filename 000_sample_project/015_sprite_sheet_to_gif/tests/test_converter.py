# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""converter 시험: 가짜 3x2 시트를 만들어 6프레임 슬라이싱과 GIF 생성을 검증한다."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from sprite_to_gif import converter, generator


def make_sheet(size: int = 60, cols: int = 3, rows: int = 2, with_alpha: bool = False) -> Image.Image:
    """프레임마다 다른 단색인 가짜 시트. 순서 검증을 위해 색을 다르게 준다."""
    mode = "RGBA" if with_alpha else "RGB"
    bg = (0, 0, 0, 0) if with_alpha else (255, 255, 255)
    sheet = Image.new(mode, (size * cols, size * rows), bg)
    colors = [(240, 60, 60), (60, 240, 60), (60, 60, 240), (240, 240, 60), (240, 60, 240), (60, 240, 240)]
    for index, color in enumerate(colors):
        cell = Image.new(mode, (size, size), color)
        sheet.paste(cell, ((index % cols) * size, (index // cols) * size))
    return sheet


class SliceTest(unittest.TestCase):
    def test_slice_returns_six_frames(self) -> None:
        frames = converter.slice_sheet(make_sheet())
        self.assertEqual(len(frames), 6)

    def test_slice_order_is_left_to_right_top_to_bottom(self) -> None:
        frames = converter.slice_sheet(make_sheet(size=30))
        self.assertEqual(frames[0].getpixel((0, 0))[:3], (240, 60, 60))
        self.assertEqual(frames[2].getpixel((0, 0))[:3], (60, 60, 240))
        self.assertEqual(frames[3].getpixel((0, 0))[:3], (240, 240, 60))
        self.assertEqual(frames[5].getpixel((0, 0))[:3], (60, 240, 240))

    def test_slice_frame_size(self) -> None:
        frames = converter.slice_sheet(make_sheet(size=60), trim=0)
        self.assertEqual(frames[0].size, (60, 60))

    def test_trim_shrinks_frame(self) -> None:
        frames = converter.slice_sheet(make_sheet(size=60), trim=2)
        self.assertEqual(frames[0].size, (56, 56))

    def test_slice_rejects_uneven_sheet(self) -> None:
        with self.assertRaises(ValueError):
            converter.slice_sheet(Image.new("RGB", (100, 100)))

    def test_slice_rejects_bad_grid(self) -> None:
        with self.assertRaises(ValueError):
            converter.slice_sheet(make_sheet(), cols=0, rows=2)

    def test_trim_rejects_larger_than_frame(self) -> None:
        with self.assertRaises(ValueError):
            converter.slice_sheet(make_sheet(size=8), trim=4)


class DurationTest(unittest.TestCase):
    def test_duration_from_fps(self) -> None:
        self.assertEqual(converter.compute_duration_ms(fps=3, duration_ms=None), 333)

    def test_duration_from_duration_ms(self) -> None:
        self.assertEqual(converter.compute_duration_ms(fps=None, duration_ms=350), 350)

    def test_default_is_three_fps(self) -> None:
        self.assertEqual(converter.compute_duration_ms(None, None), 333)

    def test_speed_half_doubles_duration(self) -> None:
        self.assertEqual(converter.compute_duration_ms(None, 300, speed=0.5), 600)

    def test_speed_two_halves_duration(self) -> None:
        self.assertEqual(converter.compute_duration_ms(None, 300, speed=2.0), 150)

    def test_duration_clamped_to_gif_minimum(self) -> None:
        self.assertEqual(converter.compute_duration_ms(None, 5), converter.MIN_DURATION_MS)

    def test_fps_and_duration_together_rejected(self) -> None:
        with self.assertRaises(ValueError):
            converter.compute_duration_ms(fps=3, duration_ms=300)

    def test_nonpositive_rejected(self) -> None:
        with self.assertRaises(ValueError):
            converter.compute_duration_ms(fps=0, duration_ms=None)
        with self.assertRaises(ValueError):
            converter.compute_duration_ms(None, 300, speed=0)


class ConvertTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(__file__).parent / "_tmp_convert"
        self.dir.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        for f in self.dir.iterdir():
            f.unlink()
        self.dir.rmdir()

    def test_convert_makes_six_frame_gif(self) -> None:
        sheet = self.dir / "sheet.png"
        make_sheet().save(sheet)
        out = self.dir / "motion.gif"
        info = converter.convert(sheet, out, fps=3, trim=0)
        self.assertEqual(info["frames"], 6)
        with Image.open(out) as gif:
            self.assertEqual(gif.n_frames, 6)
            self.assertEqual(gif.info["loop"], 0)  # 무한 루프

    def test_gif_frame_duration_matches(self) -> None:
        sheet = self.dir / "sheet.png"
        make_sheet().save(sheet)
        out = self.dir / "motion.gif"
        converter.convert(sheet, out, duration_ms=350, trim=0)
        with Image.open(out) as gif:
            self.assertEqual(gif.info["duration"], 350)

    def test_convert_reports_bytes(self) -> None:
        sheet = self.dir / "sheet.png"
        make_sheet().save(sheet)
        info = converter.convert(sheet, self.dir / "motion.gif", trim=0)
        self.assertGreater(info["bytes"], 0)

    def test_roundtrip_sheet_to_frames_to_sheet(self) -> None:
        frames = converter.slice_sheet(make_sheet(size=40), trim=0)
        sheet = converter.frames_to_sheet(frames, cols=3, rows=2, background=(255, 255, 255))
        self.assertEqual(sheet.size, (120, 80))
        again = converter.slice_sheet(sheet, trim=0)
        for before, after in zip(frames, again):
            self.assertEqual(before.tobytes(), after.tobytes())

    def test_frames_to_sheet_rejects_wrong_count(self) -> None:
        frames = converter.slice_sheet(make_sheet())
        with self.assertRaises(ValueError):
            converter.frames_to_sheet(frames[:5], cols=3, rows=2)

    def test_alpha_sheet_gif_keeps_transparent_corner(self) -> None:
        spec = generator.PixelSpec(size=60, background=None)  # 투명 배경
        frames = generator.generate_frames("wave", spec=spec)
        out = self.dir / "alpha.gif"
        converter.frames_to_gif(frames, out, duration_ms=100)
        with Image.open(out) as gif:
            self.assertEqual(gif.n_frames, len(frames))
            corner = gif.convert("RGBA").getpixel((0, 0))
        self.assertEqual(corner[3], 0)  # 투명 배경이 살아 있다


if __name__ == "__main__":
    unittest.main()
