# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""vector_generator 시험: 4종 프리셋 생성·무한 루프 이음새·GIF 저장·CLI 를 검증한다."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from sprite_to_gif import converter, vector_generator as vector


class PresetGenerationTest(unittest.TestCase):
    def test_all_presets_generate_frames(self) -> None:
        """4종 프리셋이 전부 기본 프레임 수(6/8/12)로 나온다."""
        for preset in vector.PRESETS:
            with self.subTest(preset=preset):
                frames = vector.generate_vector_frames(preset)
                self.assertEqual(len(frames), vector.PRESET_FRAMES[preset])
                self.assertTrue(2 <= len(frames) <= 12)

    def test_preset_frame_counts(self) -> None:
        self.assertEqual(vector.PRESET_FRAMES["lantern"], 12)
        self.assertEqual(vector.PRESET_FRAMES["crosshair"], 12)
        self.assertEqual(vector.PRESET_FRAMES["pulse_ring"], 8)
        self.assertEqual(vector.PRESET_FRAMES["spin_emblem"], 6)

    def test_six_frame_loop_requested(self) -> None:
        """6프레임(3x2 시트 규격) 요청이면 정확히 6장이 나온다."""
        for preset in vector.PRESETS:
            with self.subTest(preset=preset):
                self.assertEqual(len(vector.generate_vector_frames(preset, frames=6)), 6)

    def test_unknown_preset_rejected(self) -> None:
        with self.assertRaises(ValueError):
            vector.generate_vector_frames("tornado")

    def test_frame_count_must_be_two_or_more(self) -> None:
        with self.assertRaises(ValueError):
            vector.generate_vector_frames("lantern", frames=1)

    def test_frame_size_matches_spec(self) -> None:
        frames = vector.generate_vector_frames("crosshair", spec=vector.VectorSpec(size=128))
        self.assertEqual(frames[0].size, (128, 128))

    def test_frames_are_deterministic(self) -> None:
        first = [f.tobytes() for f in vector.generate_vector_frames("pulse_ring")]
        second = [f.tobytes() for f in vector.generate_vector_frames("pulse_ring")]
        self.assertEqual(first, second)

    def test_frames_differ_from_each_other(self) -> None:
        """프레임이 전부 같으면 GIF 저장기가 중복을 병합해 버린다 — 달라야 한다."""
        for preset in vector.PRESETS:
            with self.subTest(preset=preset):
                frames = vector.generate_vector_frames(preset)
                self.assertNotEqual(frames[0].tobytes(), frames[len(frames) // 2].tobytes())


class LoopSeamTest(unittest.TestCase):
    """무한 루프의 핵심: phase 1.0 의 그림은 phase 0.0 과 같아야 한다."""

    def test_phase_one_equals_phase_zero_for_all_presets(self) -> None:
        for preset in vector.PRESETS:
            with self.subTest(preset=preset):
                spec = vector.VectorSpec(size=48)
                first = vector.render_vector_frame(preset, 0.0, spec)
                wrapped = vector.render_vector_frame(preset, 1.0, spec)
                self.assertEqual(first.tobytes(), wrapped.tobytes())

    def test_half_phase_differs(self) -> None:
        spec = vector.VectorSpec(size=48)
        self.assertNotEqual(
            vector.render_vector_frame("crosshair", 0.0, spec).tobytes(),
            vector.render_vector_frame("crosshair", 0.5, spec).tobytes(),
        )


class VectorSpecTest(unittest.TestCase):
    def test_size_too_small_rejected(self) -> None:
        with self.assertRaises(ValueError):
            vector.VectorSpec(size=4)

    def test_supersample_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            vector.VectorSpec(supersample=0)

    def test_solid_background(self) -> None:
        frames = vector.generate_vector_frames(
            "pulse_ring", spec=vector.VectorSpec(size=48, background=(16, 16, 24))
        )
        self.assertEqual(frames[0].mode, "RGB")
        self.assertEqual(frames[0].getpixel((0, 0)), (16, 16, 24))

    def test_transparent_background_has_alpha(self) -> None:
        frames = vector.generate_vector_frames("pulse_ring", spec=vector.VectorSpec(size=48))
        self.assertEqual(frames[0].mode, "RGBA")
        self.assertEqual(frames[0].getpixel((0, 0))[3], 0)


class VectorGifTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(__file__).parent / "_tmp_vector"
        self.dir.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        for f in self.dir.iterdir():
            f.unlink()
        self.dir.rmdir()

    def test_vector_frames_save_as_looping_gif(self) -> None:
        for preset in vector.PRESETS:
            with self.subTest(preset=preset):
                frames = vector.generate_vector_frames(preset, spec=vector.VectorSpec(size=64))
                out = self.dir / f"{preset}.gif"
                converter.frames_to_gif(frames, out, duration_ms=100)
                with Image.open(out) as gif:
                    self.assertEqual(gif.n_frames, len(frames))
                    self.assertEqual(gif.info["loop"], 0)  # 무한 루프

    def test_cli_vector_mode(self) -> None:
        from sprite_to_gif import cli

        out = self.dir / "lantern_loop.gif"
        code = cli.main(["--mode", "vector", "--preset", "lantern",
                         "--size", "64", "--output", str(out)])
        self.assertEqual(code, 0)
        with Image.open(out) as gif:
            self.assertEqual(gif.n_frames, 12)
            self.assertEqual(gif.info["loop"], 0)

    def test_cli_vector_mode_without_preset_uses_default(self) -> None:
        from sprite_to_gif import cli

        out = self.dir / "default.gif"
        code = cli.main(["--mode", "vector", "--size", "48", "--output", str(out)])
        self.assertEqual(code, 0)
        with Image.open(out) as gif:
            self.assertEqual(gif.n_frames, 12)  # 기본 프리셋 lantern


if __name__ == "__main__":
    unittest.main()
