"""Regression coverage for photo integrity, colour handling and edit history."""

from __future__ import annotations

import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageCms, PngImagePlugin

from local_ai_photo_editor.core import (
    DEFAULT_HISTORY_BUDGET_BYTES,
    ImageDocument,
    adjust_image,
    crop_image,
    export_image,
    load_image,
    resize_image,
    rotate_image,
)


class ImageOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = Image.new("RGBA", (3, 2))
        self.image.putdata(
            [
                (20, 40, 60, 0), (40, 60, 80, 50), (60, 80, 100, 100),
                (80, 100, 120, 150), (100, 120, 140, 200), (120, 140, 160, 255),
            ]
        )

    def test_adjustments_preserve_alpha_and_do_not_mutate_input(self) -> None:
        before = self.image.tobytes()
        adjusted = adjust_image(self.image, brightness=0.5, contrast=1.4, saturation=0)
        self.assertEqual(adjusted.getchannel("A").tobytes(), self.image.getchannel("A").tobytes())
        self.assertEqual(self.image.tobytes(), before)
        red, green, blue = adjusted.getpixel((1, 1))[:3]
        self.assertEqual(red, green)
        self.assertEqual(green, blue)
        self.assertLess(red, self.image.getpixel((1, 1))[0])

    def test_identity_adjustment_is_a_pixel_exact_defensive_copy(self) -> None:
        adjusted = adjust_image(self.image)
        self.assertEqual(adjusted.tobytes(), self.image.tobytes())
        adjusted.putpixel((0, 0), (255, 255, 255, 255))
        self.assertEqual(self.image.getpixel((0, 0)), (20, 40, 60, 0))

    def test_invalid_adjustment_factors_are_rejected(self) -> None:
        for invalid in (float("nan"), float("inf"), -1, True, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    adjust_image(self.image, brightness=invalid)

    def test_clockwise_rotation_preserves_exact_pixels(self) -> None:
        rotated = rotate_image(self.image)
        self.assertEqual(rotated.size, (2, 3))
        self.assertEqual(rotated.getpixel((1, 0)), self.image.getpixel((0, 0)))
        self.assertEqual(rotated.getpixel((0, 2)), self.image.getpixel((2, 1)))
        restored = rotate_image(rotated, -1)
        self.assertEqual(restored.tobytes(), self.image.tobytes())
        self.assertEqual(rotate_image(self.image, 4).tobytes(), self.image.tobytes())

    def test_crop_returns_the_requested_rectangle(self) -> None:
        cropped = crop_image(self.image, (1, 0, 3, 2))
        self.assertEqual(cropped.size, (2, 2))
        self.assertEqual(cropped.getpixel((0, 1)), self.image.getpixel((1, 1)))
        self.assertEqual(cropped.mode, "RGBA")

    def test_crop_rejects_outside_empty_and_fractional_rectangles(self) -> None:
        for box in ((-1, 0, 3, 2), (0, 0, 4, 2), (1, 0, 1, 2), (0, 0.5, 3, 2), (0, 0, 3)):
            with self.subTest(box=box):
                with self.assertRaises(ValueError):
                    crop_image(self.image, box)

    def test_resize_changes_dimensions_and_preserves_transparency(self) -> None:
        source = Image.new("RGBA", (4, 4), (10, 30, 50, 77))
        resized = resize_image(source, 8, 6)
        self.assertEqual(resized.size, (8, 6))
        self.assertEqual(resized.mode, "RGBA")
        self.assertEqual(resized.getchannel("A").getextrema(), (77, 77))
        self.assertEqual(source.size, (4, 4))

    def test_resize_rejects_invalid_and_excessive_dimensions(self) -> None:
        for size in ((0, 2), (-1, 2), (2.5, 2), (True, 2), (40_000_001, 1)):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    resize_image(self.image, *size)


class ImageFileTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / "source.png"
        self.image = Image.new("RGB", (6, 4), (30, 90, 150))
        self.image.save(self.source)

    def test_load_applies_exif_orientation_and_strips_private_metadata(self) -> None:
        source = Image.new("RGB", (2, 3), "black")
        source.putpixel((0, 0), (255, 0, 0))
        source.putpixel((1, 2), (0, 0, 255))
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "Private owner"
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Description", "Private location")
        source.save(self.source, exif=exif, pnginfo=pnginfo)
        original_bytes = self.source.read_bytes()

        loaded = load_image(self.source)

        self.assertEqual(loaded.size, (3, 2))
        self.assertEqual(loaded.getpixel((2, 0)), (255, 0, 0))
        self.assertEqual(loaded.getpixel((0, 1)), (0, 0, 255))
        self.assertEqual(loaded.info, {})
        self.assertEqual(len(loaded.getexif()), 0)
        self.assertEqual(self.source.read_bytes(), original_bytes)

    def test_load_preserves_palette_transparency(self) -> None:
        source = Image.new("P", (2, 1))
        source.putpalette([255, 0, 0, 0, 255, 0] + [0] * (768 - 6))
        source.putdata([0, 1])
        source.save(self.source, transparency=0)
        loaded = load_image(self.source)
        self.assertEqual(loaded.mode, "RGBA")
        self.assertEqual(loaded.getpixel((0, 0)), (255, 0, 0, 0))
        self.assertEqual(loaded.getpixel((1, 0)), (0, 255, 0, 255))

    def test_load_converts_tagged_lab_pixels_to_srgb(self) -> None:
        source = Image.new("LAB", (2, 2), (128, 128, 128))
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()
        path = self.directory / "lab.tiff"
        source.save(path, icc_profile=profile)
        loaded = load_image(path)
        self.assertEqual(loaded.mode, "RGB")
        red, green, blue = loaded.getpixel((0, 0))
        self.assertLessEqual(max(red, green, blue) - min(red, green, blue), 2)
        self.assertGreater(red, 100)
        self.assertLess(red, 150)
        self.assertEqual(loaded.info, {})

    def test_load_accepts_valid_srgb_profile_without_losing_alpha(self) -> None:
        source = Image.new("RGBA", (2, 2), (30, 90, 150, 100))
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        source.save(self.source, icc_profile=profile)
        loaded = load_image(self.source)
        self.assertEqual(loaded.tobytes(), source.tobytes())
        self.assertEqual(loaded.info, {})

    def test_invalid_icc_profile_is_rejected_instead_of_ignored(self) -> None:
        self.image.save(self.source, icc_profile=b"not an ICC profile")
        with self.assertRaisesRegex(ValueError, "ICC"):
            load_image(self.source)

    def test_untagged_cmyk_is_rejected_instead_of_guessing_colours(self) -> None:
        source = Image.new("CMYK", (2, 2), (0, 50, 100, 10))
        path = self.directory / "cmyk.jpg"
        source.save(path)
        with self.assertRaisesRegex(ValueError, "ICC"):
            load_image(path)

    def test_pixel_limit_is_checked_before_pixel_decode(self) -> None:
        with patch("local_ai_photo_editor.core.editing.MAX_IMAGE_PIXELS", 8):
            with patch.object(Image.Image, "load") as decode:
                with self.assertRaisesRegex(ValueError, "limited"):
                    load_image(self.source)
                decode.assert_not_called()

    def test_animated_images_are_not_silently_flattened(self) -> None:
        path = self.directory / "animation.gif"
        Image.new("RGB", (2, 2), "red").save(
            path, save_all=True, append_images=[Image.new("RGB", (2, 2), "blue")]
        )
        with self.assertRaisesRegex(ValueError, "still image"):
            load_image(path)

    def test_export_rejects_original_path_and_normalised_alias(self) -> None:
        original_bytes = self.source.read_bytes()
        (self.directory / "nested").mkdir()
        for target in (self.source, self.directory / "nested" / ".." / "source.png"):
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, "original"):
                    export_image(self.image, target, source_path=self.source)
        self.assertEqual(self.source.read_bytes(), original_bytes)

    def test_export_rejects_hard_link_to_original(self) -> None:
        alias = self.directory / "hardlink.png"
        try:
            os.link(self.source, alias)
        except OSError as exc:
            self.skipTest(f"Hard links are unavailable: {exc}")
        original_bytes = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "original"):
            export_image(self.image, alias, source_path=self.source)
        self.assertEqual(self.source.read_bytes(), original_bytes)
        self.assertEqual(alias.read_bytes(), original_bytes)

    def test_export_rejects_symbolic_link_to_original(self) -> None:
        alias = self.directory / "symlink.png"
        try:
            alias.symlink_to(self.source)
        except OSError as exc:
            self.skipTest(f"Symbolic links are unavailable: {exc}")
        original_bytes = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "original"):
            export_image(self.image, alias, source_path=self.source)
        self.assertEqual(self.source.read_bytes(), original_bytes)

    def test_lossless_exports_roundtrip_pixels_and_only_include_srgb_metadata(self) -> None:
        source = Image.new("RGBA", (2, 2), (30, 90, 150, 100))
        source.putpixel((0, 0), (255, 10, 20, 0))
        exif = Image.Exif()
        exif[315] = "Private owner"
        source.info.update(exif=exif.tobytes(), xmp=b"Private location", comment=b"Private")
        for suffix in (".PNG", ".webp"):
            with self.subTest(suffix=suffix):
                target = self.directory / f"export{suffix}"
                returned = export_image(source, target, source_path=self.source)
                self.assertEqual(returned, target)
                with Image.open(target) as encoded:
                    self.assertEqual(encoded.tobytes(), source.tobytes())
                    self.assertNotIn("exif", encoded.info)
                    self.assertNotIn("xmp", encoded.info)
                    self.assertNotIn("comment", encoded.info)
                    profile = ImageCms.ImageCmsProfile(BytesIO(encoded.info["icc_profile"]))
                    self.assertIn("sRGB", ImageCms.getProfileDescription(profile))
                self.assertEqual(load_image(target).tobytes(), source.tobytes())

    def test_jpeg_transparency_is_composited_onto_white(self) -> None:
        source = Image.new("RGBA", (8, 8), (20, 80, 160, 0))
        for suffix in (".jpg", ".jpeg"):
            with self.subTest(suffix=suffix):
                target = self.directory / f"export{suffix}"
                export_image(source, target, source_path=self.source)
                with Image.open(target) as encoded:
                    self.assertEqual(encoded.mode, "RGB")
                    self.assertEqual(encoded.getextrema(), ((255, 255),) * 3)

    def test_failed_export_preserves_existing_destination_and_cleans_temporary_file(self) -> None:
        target = self.directory / "export.png"
        target.write_bytes(b"previous export")

        def fail_after_partial_write(_image, stream, **_options):
            stream.write(b"incomplete replacement")
            raise OSError("Simulated encoding failure")

        with patch.object(Image.Image, "save", fail_after_partial_write):
            with self.assertRaisesRegex(OSError, "Simulated"):
                export_image(self.image, target, source_path=self.source)
        self.assertEqual(target.read_bytes(), b"previous export")
        self.assertEqual(list(self.directory.glob(".local-ai-photo-editor-*")), [])

    def test_successful_export_replaces_only_the_chosen_destination(self) -> None:
        target = self.directory / "export.png"
        target.write_bytes(b"previous export")
        original_bytes = self.source.read_bytes()
        replacement = Image.new("RGB", (5, 3), "green")
        export_image(replacement, target, source_path=self.source)
        self.assertEqual(load_image(target).tobytes(), replacement.tobytes())
        self.assertEqual(self.source.read_bytes(), original_bytes)
        self.assertEqual(list(self.directory.glob(".local-ai-photo-editor-*")), [])

    def test_unsupported_export_format_is_rejected_before_writing(self) -> None:
        target = self.directory / "export.tiff"
        with self.assertRaisesRegex(ValueError, "PNG, JPEG and WebP"):
            export_image(self.image, target, source_path=self.source)
        self.assertFalse(target.exists())


class ImageDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = Image.new("RGB", (2, 2), "black")
        self.red = Image.new("RGB", (2, 2), "red")
        self.green = Image.new("RGB", (2, 2), "green")
        self.blue = Image.new("RGB", (2, 2), "blue")

    def test_source_and_returned_images_cannot_mutate_document_pixels(self) -> None:
        document = ImageDocument(self.original)
        self.original.putpixel((0, 0), (255, 255, 255))
        document.original.putpixel((0, 0), (255, 0, 0))
        document.current.putpixel((0, 0), (0, 255, 0))
        self.assertEqual(document.original.getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(document.current.getpixel((0, 0)), (0, 0, 0))
        document.apply(self.red, "Red")
        self.red.putpixel((0, 0), (255, 255, 255))
        self.assertEqual(document.current.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(document.original.getpixel((0, 0)), (0, 0, 0))

    def test_undo_redo_restores_pixels_and_labels(self) -> None:
        document = ImageDocument(self.original)
        self.assertFalse(document.undo())
        self.assertFalse(document.redo())
        document.apply(self.red, "Red")
        document.apply(self.green, "Green")
        self.assertEqual(document.history, ("Red", "Green"))
        self.assertTrue(document.undo())
        self.assertEqual(document.current.tobytes(), self.red.tobytes())
        self.assertEqual(document.history, ("Red",))
        self.assertTrue(document.can_redo)
        self.assertTrue(document.redo())
        self.assertEqual(document.current.tobytes(), self.green.tobytes())
        self.assertEqual(document.history, ("Red", "Green"))
        self.assertFalse(document.can_redo)

    def test_new_edit_clears_redo_without_mutating_original(self) -> None:
        document = ImageDocument(self.original)
        document.apply(self.red, "Red")
        document.apply(self.green, "Green")
        document.undo()
        document.apply(self.blue, "Blue")
        self.assertFalse(document.redo())
        self.assertEqual(document.history, ("Red", "Blue"))
        self.assertEqual(document.current.tobytes(), self.blue.tobytes())
        self.assertEqual(document.original.tobytes(), self.original.tobytes())

    def test_reset_is_itself_undoable(self) -> None:
        document = ImageDocument(self.original)
        document.apply(self.red, "Red")
        document.reset(label="Original wiederherstellen")
        self.assertEqual(document.current.tobytes(), self.original.tobytes())
        self.assertEqual(document.history[-1], "Original wiederherstellen")
        self.assertTrue(document.undo())
        self.assertEqual(document.current.tobytes(), self.red.tobytes())
        self.assertTrue(document.redo())
        self.assertEqual(document.current.tobytes(), self.original.tobytes())

    def test_byte_budget_drops_oldest_undo_states(self) -> None:
        document = ImageDocument(self.original, history_budget_bytes=24)
        document.apply(self.red, "Red")
        document.apply(self.green, "Green")
        document.apply(self.blue, "Blue")
        self.assertEqual(document.history_memory_bytes, 24)
        self.assertEqual(document.undo_memory_bytes, 24)
        self.assertTrue(document.undo())
        self.assertLessEqual(document.history_memory_bytes, 24)
        self.assertTrue(document.undo())
        self.assertEqual(document.current.tobytes(), self.red.tobytes())
        self.assertFalse(document.undo())
        self.assertEqual(document.history, ("Red",))
        self.assertEqual(document.original.tobytes(), self.original.tobytes())
        self.assertTrue(document.redo())
        self.assertTrue(document.redo())
        self.assertEqual(document.current.tobytes(), self.blue.tobytes())
        self.assertLessEqual(document.history_memory_bytes, 24)

    def test_redo_cannot_exceed_budget_after_undoing_a_large_resize(self) -> None:
        document = ImageDocument(self.original, history_budget_bytes=16)
        document.apply(Image.new("RGB", (5, 5), "red"), "Resize")
        self.assertTrue(document.undo())
        self.assertEqual(document.current.size, (2, 2))
        self.assertLessEqual(document.history_memory_bytes, 16)
        self.assertFalse(document.can_redo)

    def test_zero_budget_keeps_original_but_no_pixel_history(self) -> None:
        document = ImageDocument(self.original, history_budget_bytes=0)
        document.apply(self.red, "Red")
        self.assertEqual(document.history_memory_bytes, 0)
        self.assertFalse(document.undo())
        document.reset()
        self.assertEqual(document.current.tobytes(), self.original.tobytes())

    def test_failed_edit_does_not_destroy_existing_redo(self) -> None:
        document = ImageDocument(self.original)
        document.apply(self.red, "Red")
        document.undo()
        with self.assertRaises(ValueError):
            document.apply(self.green, " ")
        with self.assertRaises(ValueError):
            document.apply(Image.new("RGB", (0, 0)), "Empty image")
        self.assertTrue(document.can_redo)
        self.assertEqual(document.history, ())
        self.assertTrue(document.redo())
        self.assertEqual(document.current.tobytes(), self.red.tobytes())

    def test_history_budget_validation_and_default_capacity(self) -> None:
        self.assertGreaterEqual(DEFAULT_HISTORY_BUDGET_BYTES, 40_000_000 * 4)
        for invalid in (-1, 1.5, True, None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    ImageDocument(self.original, history_budget_bytes=invalid)


if __name__ == "__main__":
    unittest.main()
