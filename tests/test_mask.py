"""Regression tests for local, alpha-only manual foreground correction."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from local_ai_photo_editor.core import (
    ImageDocument, MaskStroke, load_project, paint_alpha_strokes, save_project,
)


def stroke(
    mode: str, *points: tuple[float, float], size: float = 0.12, feather: float = 0.0,
) -> MaskStroke:
    return MaskStroke(points=tuple(points), mode=mode, diameter=size, feather=feather)


class MaskBrushTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = Image.new("RGBA", (100, 80), (35, 110, 175, 0))
        self.image.putpixel((0, 0), (255, 25, 65, 0))

    def test_restore_is_local_and_preserves_existing_rgb_and_input(self) -> None:
        before = self.image.tobytes()
        edited = paint_alpha_strokes(self.image, [stroke("restore", (0.5, 0.5))])
        self.assertEqual(edited.mode, "RGBA")
        self.assertEqual(edited.getpixel((50, 40)), (35, 110, 175, 255))
        self.assertEqual(edited.getpixel((0, 0)), (255, 25, 65, 0))
        self.assertEqual(self.image.tobytes(), before)
        self.assertEqual(edited.convert("RGB").tobytes(), self.image.convert("RGB").tobytes())
        self.assertEqual(edited.info, {})

    def test_erase_clears_alpha_without_erasing_rgb(self) -> None:
        opaque = Image.new("RGBA", (100, 80), (40, 90, 140, 255))
        edited = paint_alpha_strokes(opaque, [stroke("erase", (0.5, 0.5))])
        self.assertEqual(edited.getpixel((50, 40)), (40, 90, 140, 0))
        self.assertEqual(edited.getpixel((0, 0)), (40, 90, 140, 255))
        self.assertEqual(opaque.getpixel((50, 40)), (40, 90, 140, 255))

    def test_drag_interpolates_continuously_not_only_endpoint_dabs(self) -> None:
        painted = paint_alpha_strokes(self.image, [
            stroke("restore", (0.2, 0.5), (0.8, 0.5), size=0.08)
        ])
        for x in (20, 30, 40, 50, 60, 70, 80):
            with self.subTest(x=x):
                self.assertEqual(painted.getpixel((x, 40))[3], 255)
        self.assertEqual(painted.getpixel((50, 10))[3], 0)

    def test_soft_brush_preserves_partial_alpha_on_edge(self) -> None:
        painted = paint_alpha_strokes(self.image, [
            stroke("restore", (0.5, 0.5), size=0.3 / 2, feather=1)
        ])
        alpha = list(painted.getchannel("A").getdata())
        self.assertTrue(any(0 < value < 255 for value in alpha))
        self.assertGreater(painted.getpixel((50, 40))[3], 200)
        self.assertEqual(painted.getpixel((0, 0))[3], 0)

    def test_order_matters_and_modes_can_revisit_an_edited_area(self) -> None:
        center = (0.5, 0.5)
        painted = paint_alpha_strokes(self.image, [
            stroke("restore", center),
            stroke("erase", center, size=0.05),
        ])
        self.assertEqual(painted.getpixel((50, 40))[3], 0)
        self.assertEqual(painted.getpixel((53, 40))[3], 255)
        again = paint_alpha_strokes(painted, [stroke("restore", center, size=0.05)])
        self.assertEqual(again.getpixel((50, 40))[3], 255)

    def test_corner_and_end_of_image_are_clipped_not_wrapped(self) -> None:
        painted = paint_alpha_strokes(self.image, [
            stroke("restore", (0.0, 0.0)), stroke("restore", (1.0, 1.0)),
        ])
        self.assertEqual(painted.getpixel((0, 0))[3], 255)
        self.assertEqual(painted.getpixel((99, 79))[3], 255)
        self.assertEqual(painted.getpixel((50, 40))[3], 0)

    def test_returns_defensive_copy_for_empty_strokes(self) -> None:
        edited = paint_alpha_strokes(self.image, [])
        edited.putpixel((0, 0), (1, 2, 3, 4))
        self.assertEqual(self.image.getpixel((0, 0)), (255, 25, 65, 0))

    def test_rgb_images_require_existing_alpha(self) -> None:
        with self.assertRaisesRegex(ValueError, "alpha"):
            paint_alpha_strokes(Image.new("RGB", (20, 20)), [stroke("erase", (0.5, 0.5))])

    def test_rejects_invalid_stroke_settings_before_modifying_pixels(self) -> None:
        valid_point = ((0.5, 0.5),)
        invalid = [
            MaskStroke(points=valid_point, mode="delete", diameter=0.05),
            MaskStroke(points=(), mode="erase", diameter=0.05),
            MaskStroke(points=valid_point, mode="erase", diameter=0),
            MaskStroke(points=valid_point, mode="erase", diameter=0.25),
            MaskStroke(points=valid_point, mode="erase", diameter=float("inf")),
            MaskStroke(points=valid_point, mode="erase", diameter=True),
            MaskStroke(points=valid_point, mode="erase", diameter=0.05, feather=-1),
            MaskStroke(points=valid_point, mode="erase", diameter=0.05, feather=float("nan")),
            MaskStroke(points=((float("nan"), 0.5),), mode="erase", diameter=0.05),
            MaskStroke(points=((1.1, 0.5),), mode="erase", diameter=0.05),
            MaskStroke(points=((True, 0.5),), mode="erase", diameter=0.05),
            MaskStroke(points=((0.5,),), mode="erase", diameter=0.05),
            MaskStroke(points=((0.5, 0.5),) * 2049, mode="erase", diameter=0.05),
        ]
        before = self.image.tobytes()
        for bad in invalid:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    paint_alpha_strokes(self.image, [bad])
        self.assertEqual(self.image.tobytes(), before)
        with self.assertRaises(ValueError):
            paint_alpha_strokes(self.image, [stroke("erase", (0.5, 0.5))] * 129)

    def test_project_roundtrip_and_undo_recover_baked_mask_pixels(self) -> None:
        masked = paint_alpha_strokes(self.image, [stroke("restore", (0.5, 0.5))])
        document = ImageDocument(self.image)
        document.apply(masked, "Correct mask")
        self.assertTrue(document.undo())
        self.assertTrue(document.redo())
        self.assertEqual(document.current.tobytes(), masked.tobytes())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrected.laip"
            save_project(document, path)
            reloaded = load_project(path)
            self.assertEqual(reloaded.current.tobytes(), masked.tobytes())
            self.assertTrue(reloaded.can_undo)
            self.assertTrue(reloaded.undo())
            self.assertEqual(reloaded.current.tobytes(), self.image.tobytes())
            self.assertTrue(reloaded.redo())
            self.assertEqual(reloaded.current.tobytes(), masked.tobytes())


if __name__ == "__main__":
    unittest.main()
