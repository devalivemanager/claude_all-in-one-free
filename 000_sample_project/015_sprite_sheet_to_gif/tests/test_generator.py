"""generator 시험: 절차적 프레임 생성의 결정론·모션·시트 왕복을 검증한다."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from sprite_to_gif import converter, generator


class GenerateFramesTest(unittest.TestCase):
    def test_all_motions_generate_six_frames(self) -> None:
        for motion in generator.MOTIONS:
            with self.subTest(motion=motion):
                frames = generator.generate_frames(motion)
                self.assertEqual(len(frames), 6)

    def test_unknown_motion_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generator.generate_frames("fly")

    def test_frame_count_must_be_two_or_more(self) -> None:
        with self.assertRaises(ValueError):
            generator.generate_frames("walk", frames=1)

    def test_frame_size_matches_spec(self) -> None:
        frames = generator.generate_frames("walk", spec=generator.PixelSpec(size=96))
        self.assertEqual(frames[0].size, (96, 96))

    def test_size_smaller_than_dot_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generator.PixelSpec(size=8, dot=16)

    def test_frames_are_deterministic(self) -> None:
        first = [f.tobytes() for f in generator.generate_frames("walk")]
        second = [f.tobytes() for f in generator.generate_frames("walk")]
        self.assertEqual(first, second)

    def test_walk_frames_differ_from_each_other(self) -> None:
        frames = generator.generate_frames("walk")
        self.assertNotEqual(frames[0].tobytes(), frames[2].tobytes())  # 다리 위치가 바뀐다

    def test_bounce_touches_ground_and_rises(self) -> None:
        frames = generator.generate_frames("bounce")
        accent = generator.PixelSpec().palette["accent"][:3]

        def ball_top(image: Image.Image) -> int:
            for y in range(image.height):
                for x in range(image.width):
                    if image.getpixel((x, y))[:3] == accent:
                        return y
            raise AssertionError("공을 찾지 못했다")

        self.assertLess(ball_top(frames[1]), ball_top(frames[0]))  # 첫 프레임보다 위에 있다
        self.assertGreaterEqual(ball_top(frames[0]), ball_top(frames[1]))  # 착지 프레임이 가장 낮다

    def test_pulse_keeps_lantern_body_fixed(self) -> None:
        """등불 몸통(고정 소품)은 프레마다 같은 자리에 있다(빛만 움직인다)."""
        accent = generator.PixelSpec().palette["accent"][:3]
        centers = []
        for frame in generator.generate_frames("pulse"):
            xs = [x for x in range(frame.width) for y in (frame.height // 2,)
                  if frame.getpixel((x, y))[:3] == accent]
            centers.append(min(xs))
        self.assertEqual(len(set(centers)), 1)

    def test_transparent_background_has_alpha(self) -> None:
        frames = generator.generate_frames("wave", spec=generator.PixelSpec(background=None))
        self.assertEqual(frames[0].mode, "RGBA")
        self.assertEqual(frames[0].getpixel((0, 0))[3], 0)

    def test_solid_background(self) -> None:
        frames = generator.generate_frames("wave", spec=generator.PixelSpec(background=(20, 20, 28)))
        self.assertEqual(frames[0].mode, "RGB")
        self.assertEqual(frames[0].getpixel((0, 0)), (20, 20, 28))

    def test_custom_palette(self) -> None:
        spec = generator.PixelSpec()
        spec.palette["accent"] = (0, 255, 0, 255)
        frames = generator.generate_frames("pulse", spec=spec)
        colors = {c for f in frames for _, c in f.getcolors() for c in [c]}
        self.assertIn((0, 255, 0, 255), colors)


class SheetRoundTripTest(unittest.TestCase):
    def test_generate_sheet_convert_to_gif(self) -> None:
        """전체 파이프라인: 절차 생성 → 3x2 시트 → 슬라이싱 → 6프레임 GIF."""
        dir = Path(__file__).parent / "_tmp_generate"
        dir.mkdir(exist_ok=True)
        try:
            frames = generator.generate_frames("walk")
            sheet = converter.frames_to_sheet(frames, cols=3, rows=2)
            self.assertEqual(sheet.size, (192, 128))
            sheet_path = dir / "walk_sheet.png"
            sheet.save(sheet_path)
            out = dir / "walk.gif"
            info = converter.convert(sheet_path, out, fps=3, trim=1)
            self.assertEqual(info["frames"], 6)
            with Image.open(out) as gif:
                self.assertEqual(gif.n_frames, 6)
                self.assertEqual(gif.info["loop"], 0)
        finally:
            for f in dir.iterdir():
                f.unlink()
            dir.rmdir()


if __name__ == "__main__":
    unittest.main()
