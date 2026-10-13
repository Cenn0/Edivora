"""Subject effects and process-contract tests; not a model-quality benchmark."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from local_ai_photo_editor.ai.background import NoSubjectError, apply_mask
from local_ai_photo_editor.core.recipes import RenderCancelled
from local_ai_photo_editor.core.selection_io import SubjectJobError, read_subject_result, write_subject_result
from local_ai_photo_editor.core.subject import (
    SUBJECT_MODES, SubjectEdit, effective_subject_mask, render_subject,
    selection_overlay, subject_bounds, validate_subject_mask,
)
from local_ai_photo_editor.worker import run_job


def fixture(size=(80, 60), alpha=False):
    image = Image.new("RGBA" if alpha else "RGB", size, (30, 60, 150, 128) if alpha else (30, 60, 150))
    image.paste((100, 160, 40, 255) if alpha else (100, 160, 40),
                (size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4))
    mask = Image.new("L", size)
    mask.paste(255, (size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4))
    return image, mask


class SubjectEffectTests(unittest.TestCase):
    def test_settings_are_strict_and_bounded(self):
        for field in ("strength", "feather", "padding"):
            for bad in (-1, 101, True, 1.0, "3", None, float("nan")):
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    SubjectEdit(**{field: bad})
        for mode in ([], "unknown", None, True):
            with self.assertRaises(ValueError):
                SubjectEdit(mode=mode)
        with self.assertRaises(ValueError):
            SubjectEdit(padding=41)

    def test_mask_requires_exact_size_and_grayscale(self):
        image, mask = fixture()
        for invalid in (mask.convert("RGB"), mask.resize((4, 4)), None):
            with self.assertRaises(ValueError):
                validate_subject_mask(invalid, image.size)
        with self.assertRaises(ValueError):
            validate_subject_mask(mask, (40_000_001, 1))

    def test_zero_strength_is_owned_identity_for_color_effects(self):
        image, mask = fixture(alpha=True)
        for mode in ("blur", "color_pop", "light", "dim"):
            result = render_subject(image, mask, SubjectEdit(mode, strength=0))
            self.assertEqual(result.tobytes(), image.tobytes())
            self.assertIsNot(result, image)
            self.assertFalse(SubjectEdit(mode, strength=0).has_effect)

    def test_color_effects_preserve_alpha_and_hidden_rgb(self):
        image, mask = fixture(alpha=True)
        image.putpixel((0, 0), (242, 7, 99, 0))
        original, original_mask = image.tobytes(), mask.tobytes()
        for mode in ("blur", "color_pop", "light", "dim"):
            with self.subTest(mode=mode):
                result = render_subject(image, mask, SubjectEdit(mode, strength=90))
                self.assertEqual(result.getchannel("A").tobytes(), image.getchannel("A").tobytes())
                self.assertEqual(result.getpixel((0, 0)), image.getpixel((0, 0)))
                self.assertEqual(image.tobytes(), original)
                self.assertEqual(mask.tobytes(), original_mask)

    def test_opaque_subject_colors_stay_exact_in_background_effects(self):
        image, mask = fixture()
        for mode in ("blur", "dim", "color_pop"):
            result = render_subject(image, mask, SubjectEdit(mode, strength=100))
            self.assertEqual(result.crop((20, 15, 60, 45)).tobytes(), image.crop((20, 15, 60, 45)).tobytes())

    def test_color_pop_removes_only_background_color(self):
        image, mask = fixture()
        result = render_subject(image, mask, SubjectEdit("color_pop", strength=100))
        red, green, blue = result.getpixel((0, 0))
        self.assertEqual((red, green), (green, blue))
        self.assertEqual(result.getpixel((40, 30)), image.getpixel((40, 30)))

    def test_subject_light_does_not_modify_background(self):
        image, mask = fixture()
        result = render_subject(image, mask, SubjectEdit("light", strength=100))
        self.assertEqual(result.getpixel((0, 0)), image.getpixel((0, 0)))
        self.assertEqual(result.getpixel((40, 30)), (200, 255, 80))

    def test_background_dim_has_expected_strength(self):
        image, mask = fixture()
        result = render_subject(image, mask, SubjectEdit("dim", strength=100))
        self.assertEqual(result.getpixel((0, 0)), (6, 12, 30))
        self.assertEqual(result.getpixel((40, 30)), image.getpixel((40, 30)))

    def test_cutout_matches_existing_alpha_adapter_without_redrawing_rgb(self):
        image, mask = fixture(alpha=True)
        mask.putpixel((0, 0), 128)
        result = render_subject(image, mask, SubjectEdit("cutout"))
        self.assertEqual(result.tobytes(), apply_mask(image, mask).tobytes())
        self.assertEqual(result.convert("RGB").tobytes(), image.convert("RGB").tobytes())
        self.assertEqual(result.getpixel((0, 0))[3], 64)

    def test_crop_margin_and_edge_clamping(self):
        image, mask = fixture()
        self.assertEqual(subject_bounds(mask, 0), (20, 15, 60, 45))
        self.assertEqual(subject_bounds(mask, 10), (16, 11, 64, 49))
        result = render_subject(image, mask, SubjectEdit("crop", padding=10))
        self.assertEqual(result.tobytes(), image.crop((16, 11, 64, 49)).tobytes())
        mask.paste(255, (0, 0, 10, 10))
        self.assertEqual(subject_bounds(mask, 40)[:2], (0, 0))

    def test_crop_excludes_fully_transparent_selected_pixels(self):
        image, mask = fixture(alpha=True)
        mask.putpixel((0, 0), 255)
        image.putpixel((0, 0), (1, 2, 3, 0))
        self.assertEqual(subject_bounds(mask, 0, image.getchannel("A")), (20, 15, 60, 45))

    def test_empty_crop_fails_without_changing_image(self):
        image, mask = fixture()
        with self.assertRaises(ValueError):
            render_subject(image, Image.new("L", mask.size), SubjectEdit("crop"))

    def test_softening_is_optional_and_does_not_modify_the_inferred_mask(self):
        _, mask = fixture((300, 200))
        original = mask.tobytes()
        self.assertEqual(effective_subject_mask(mask, 0).tobytes(), original)
        softened = effective_subject_mask(mask, 100)
        self.assertNotEqual(softened.tobytes(), original)
        self.assertEqual(mask.tobytes(), original)
        self.assertEqual(softened.getpixel((150, 100)), 255)

    def test_overlay_is_a_separate_preview_and_preserves_alpha(self):
        image, mask = fixture(alpha=True)
        before = image.tobytes()
        overlay = selection_overlay(image, mask)
        self.assertEqual(overlay.getpixel((0, 0)), image.getpixel((0, 0)))
        self.assertNotEqual(overlay.getpixel((40, 30)), image.getpixel((40, 30)))
        self.assertEqual(overlay.getchannel("A").tobytes(), image.getchannel("A").tobytes())
        self.assertEqual(image.tobytes(), before)

    def test_background_blur_changes_texture_but_not_selected_subject(self):
        image, mask = fixture((200, 120))
        for x in range(0, 200, 2):
            image.paste((200, 200, 200), (x, 0, x + 1, 20))
        result = render_subject(image, mask, SubjectEdit("blur", strength=100))
        self.assertNotEqual(result.crop((0, 0, 200, 15)).tobytes(), image.crop((0, 0, 200, 15)).tobytes())
        self.assertEqual(result.getpixel((100, 60)), image.getpixel((100, 60)))

    def test_subject_colors_do_not_bleed_into_background_blur(self):
        image = Image.new("RGB", (200, 120), (0, 0, 240))
        mask = Image.new("L", image.size)
        image.paste((255, 0, 0), (80, 30, 120, 90))
        mask.paste(255, (80, 30, 120, 90))
        result = render_subject(image, mask, SubjectEdit("blur", strength=100))
        self.assertEqual(result.getpixel((79, 60))[0], 0)
        self.assertEqual(result.getpixel((80, 60)), (255, 0, 0))

    def test_blur_tiles_match_a_whole_image_tile(self):
        rng = np.random.default_rng(21)
        image = Image.fromarray(rng.integers(0, 256, (270, 1040, 3), dtype=np.uint8))
        _, mask = fixture(image.size)
        edit = SubjectEdit("blur", strength=90)
        tiled = render_subject(image, mask, edit)
        with patch("local_ai_photo_editor.core.subject._tiles", return_value=[(0, 0, 1040, 270)]):
            whole = render_subject(image, mask, edit)
        np.testing.assert_array_equal(np.asarray(tiled), np.asarray(whole))

    def test_cancellation_before_and_between_tiles_preserves_inputs(self):
        image, mask = fixture((1100, 300))
        original = image.tobytes()
        with self.assertRaises(RenderCancelled):
            render_subject(image, mask, SubjectEdit("blur"), cancelled=lambda: True)
        count = 0
        def cancel():
            nonlocal count
            count += 1
            return count >= 4
        with self.assertRaises(RenderCancelled):
            render_subject(image, mask, SubjectEdit("blur"), cancelled=cancel)
        self.assertEqual(image.tobytes(), original)


class SubjectProtocolTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.directory = Path(self.root.name)
        self.image, self.mask = fixture()
        self.status = write_subject_result(self.mask, self.directory)
        self.write_status(self.status)

    def write_status(self, value):
        (self.directory / "result.json").write_text(json.dumps(value), encoding="utf-8")

    def test_round_trip_is_owned_exact_and_metadata_free(self):
        result = read_subject_result(self.directory, self.mask.size, 0)
        self.assertEqual(result.tobytes(), self.mask.tobytes())
        self.assertEqual(result.info, {})
        self.assertIsNot(result, self.mask)
        self.assertEqual(set(p.name for p in self.directory.iterdir()), {"mask.png", "result.json"})

    def test_success_requires_exact_contract_and_successful_exit(self):
        for changes in ({"version": True}, {"operation": "other"}, {"width": 81}, {"height": True},
                        {"sha256": "bad"}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.write_status({**self.status, **changes})
                read_subject_result(self.directory, self.mask.size, 0)
        self.write_status(self.status)
        with self.assertRaises(ValueError):
            read_subject_result(self.directory, self.mask.size, 1)

    def test_corrupt_and_wrong_format_mask_bytes_are_rejected(self):
        path = self.directory / "mask.png"
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            read_subject_result(self.directory, self.mask.size, 0)
        self.image.save(path, format="PNG")
        self.write_status({**self.status, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        with self.assertRaises(ValueError):
            read_subject_result(self.directory, self.mask.size, 0)

    def test_error_codes_are_sanitized_without_worker_message_leaks(self):
        for code in ("MODEL_MISSING", "MODEL_INVALID", "NO_SUBJECT", "private/path", []):
            self.write_status({"status": "error", "code": code, "message": "private/photo.png"})
            with self.assertRaises(SubjectJobError) as error:
                read_subject_result(self.directory, self.mask.size, 1)
            self.assertNotIn("private", str(error.exception))

    def test_oversized_status_and_symlinks_are_rejected(self):
        (self.directory / "result.json").write_bytes(b" " * 4097)
        with self.assertRaises(ValueError):
            read_subject_result(self.directory, self.mask.size, 0)
        self.write_status(self.status)
        with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(ValueError):
            read_subject_result(self.directory, self.mask.size, 0)

    def test_failed_mask_write_preserves_previous_result_and_cleans_temporary_file(self):
        before = (self.directory / "mask.png").read_bytes()
        with patch.object(Image.Image, "save", side_effect=OSError("disk full")), self.assertRaises(OSError):
            write_subject_result(self.mask, self.directory)
        self.assertEqual((self.directory / "mask.png").read_bytes(), before)
        self.assertEqual(set(p.name for p in self.directory.iterdir()), {"mask.png", "result.json"})

    def test_worker_selection_is_independent_of_alpha_and_does_not_overwrite_input(self):
        self.image.save(self.directory / "input.png")
        original = (self.directory / "input.png").read_bytes()
        (self.directory / "request.json").write_text('{"version":1,"operation":"select_subject"}')
        with patch("local_ai_photo_editor.ai.background.predict_subject", return_value=self.mask) as predictor:
            self.assertEqual(run_job(self.directory), 0)
            predictor.assert_called_once()
        self.assertEqual(read_subject_result(self.directory, self.image.size, 0).tobytes(), self.mask.tobytes())
        self.assertEqual((self.directory / "input.png").read_bytes(), original)
        self.assertFalse((self.directory / "output.png").exists())

    def test_invalid_requests_are_rejected_before_any_inference(self):
        self.image.save(self.directory / "input.png")
        for request in ({"version": True, "operation": "select_subject"},
                        {"version": 1, "operation": "select_subject", "url": "ignored"},
                        {"version": 1, "operation": []}, {"version": 1, "operation": "unknown"}, []):
            (self.directory / "request.json").write_text(json.dumps(request))
            with patch("local_ai_photo_editor.ai.background.predict_subject") as predictor:
                self.assertEqual(run_job(self.directory), 1)
                predictor.assert_not_called()

    def test_uniform_prediction_reports_no_subject(self):
        self.image.save(self.directory / "input.png")
        (self.directory / "request.json").write_text('{"version":1,"operation":"select_subject"}')
        with patch("local_ai_photo_editor.ai.background.predict_subject", side_effect=NoSubjectError()):
            self.assertEqual(run_job(self.directory), 1)
        self.assertEqual(json.loads((self.directory / "result.json").read_text())["code"], "NO_SUBJECT")


if __name__ == "__main__":
    unittest.main()
