"""Deterministic pixel/invariant tests; these are not an image-quality benchmark."""
from __future__ import annotations

from dataclasses import fields, replace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from local_ai_photo_editor.core.recipes import (
    ASPECTS, LOOKS, EditRecipe, RenderCancelled, _tiles, auto_levels,
    crop_box, output_size, render_recipe,
)


def fixture(width=85, height=61, alpha=True):
    rng = np.random.default_rng(42)
    pixels = rng.integers(20, 236, (height, width, 4 if alpha else 3), dtype=np.uint8)
    if alpha:
        pixels[..., 3] = np.linspace(0, 255, width, dtype=np.uint8)[None, :]
    return Image.fromarray(pixels)


class RecipeValidationTests(unittest.TestCase):
    def test_defaults_and_inactive_settings_have_no_effect(self):
        self.assertFalse(EditRecipe().has_effect)
        self.assertFalse(EditRecipe(look_strength=20, focus_x=0, focus_y=100,
                                    background_color=(1, 2, 3), background_blur=40).has_effect)
        self.assertFalse(EditRecipe(look="mono", look_strength=0).has_effect)

    def test_every_integer_field_rejects_bool_float_nonfinite_and_out_of_range(self):
        for field in fields(EditRecipe):
            default = getattr(EditRecipe(), field.name)
            if type(default) is not int:
                continue
            for bad in (True, 1.0, float("nan"), float("inf"), "1", None, -101, 101):
                with self.subTest(field=field.name, value=bad), self.assertRaises(ValueError):
                    EditRecipe(**{field.name: bad})
        for field in ("automatic", "shadows", "highlights", "sharpness", "vignette", "look_strength", "focus_x", "focus_y", "background_blur"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                EditRecipe(**{field: -1})
        with self.assertRaises(ValueError):
            EditRecipe(quarter_turns=4)

    def test_identifiers_flags_and_colors_are_strict(self):
        cases = [{"look": "unknown"}, {"look": []}, {"aspect": []}, {"aspect": "1:0"},
                 {"background": "unknown"}, {"mirror": 1}, {"flip": "yes"},
                 {"background_color": [0, 0, 0]}, {"background_color": (0, 0)},
                 {"background_color": (True, 0, 0)}, {"background_color": (-1, 0, 0)},
                 {"background_color": (256, 0, 0)}]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                EditRecipe(**kwargs)

    def test_resets_follow_visible_sections_and_preserve_other_settings(self):
        recipe = EditRecipe(exposure=20, vignette=25, look="warm", mirror=True, background="solid")
        self.assertEqual(recipe.reset_section("light"), replace(recipe, exposure=0))
        self.assertEqual(recipe.reset_section("look"), replace(recipe, look="none", vignette=0))
        self.assertEqual(recipe.reset_section("shape"), replace(recipe, mirror=False))
        self.assertEqual(recipe.reset_section("background"), replace(recipe, background="keep"))
        with self.assertRaises(ValueError):
            recipe.reset_section("unknown")

    def test_auto_levels_are_validated_even_for_neutral_recipe(self):
        for levels in ((0, 0), (256, 257), (-1, 200), (0, True), [0, 255], (0, 1, 2)):
            with self.subTest(levels=levels), self.assertRaises(ValueError):
                render_recipe(fixture(), EditRecipe(), levels=levels)


class RecipePixelTests(unittest.TestCase):
    def test_neutral_is_an_owned_exact_copy_and_clears_only_output_metadata(self):
        for alpha in (True, False):
            image = fixture(alpha=alpha)
            image.info["comment"] = "private"
            original = image.tobytes()
            result = render_recipe(image, EditRecipe())
            self.assertEqual(result.tobytes(), original)
            self.assertIsNot(result, image)
            self.assertEqual(result.info, {})
            self.assertEqual(image.info["comment"], "private")
            result.putpixel((0, 0), (0,) * len(result.getbands()))
            self.assertEqual(image.tobytes(), original)

    def test_every_correction_and_look_preserves_alpha_and_input(self):
        image = fixture()
        original, alpha = image.tobytes(), image.getchannel("A").tobytes()
        recipes = [EditRecipe(**{key: 65}) for key in
                   ("exposure", "contrast", "automatic", "shadows", "highlights", "warmth", "saturation", "sharpness", "vignette")]
        recipes += [EditRecipe(look=look) for look in LOOKS if look != "none"]
        for recipe in recipes:
            with self.subTest(recipe=recipe):
                result = render_recipe(image, recipe)
                self.assertEqual(result.getchannel("A").tobytes(), alpha)
                self.assertEqual(result.size, image.size)
                self.assertNotEqual(result.convert("RGB").tobytes(), image.convert("RGB").tobytes())
                self.assertEqual(image.tobytes(), original)

    def test_shadow_lift_and_highlight_reduction_are_selective(self):
        image = Image.new("RGB", (2, 1))
        image.putdata([(30, 30, 30), (220, 220, 220)])
        shadows = render_recipe(image, EditRecipe(shadows=100))
        highlights = render_recipe(image, EditRecipe(highlights=100))
        self.assertGreater(shadows.getpixel((0, 0))[0] - 30, shadows.getpixel((1, 0))[0] - 220)
        self.assertGreater(220 - highlights.getpixel((1, 0))[0], 30 - highlights.getpixel((0, 0))[0])

    def test_exposure_warmth_and_desaturation_have_expected_directions(self):
        grey = Image.new("RGB", (10, 10), (100, 100, 100))
        self.assertGreater(render_recipe(grey, EditRecipe(exposure=25)).getpixel((0, 0))[0], 100)
        self.assertLess(render_recipe(grey, EditRecipe(exposure=-25)).getpixel((0, 0))[0], 100)
        warm = render_recipe(grey, EditRecipe(warmth=100)).getpixel((0, 0))
        self.assertGreater(warm[0], warm[2])
        for recipe in (EditRecipe(saturation=-100), EditRecipe(look="mono")):
            values = np.asarray(render_recipe(fixture(alpha=False), recipe))
            np.testing.assert_array_equal(values[..., 0], values[..., 1])
            np.testing.assert_array_equal(values[..., 1], values[..., 2])

    def test_look_strength_zero_is_identity_and_half_is_intermediate(self):
        image = fixture(alpha=False)
        neutral = render_recipe(image, EditRecipe(look="mono", look_strength=0))
        self.assertEqual(neutral.tobytes(), image.tobytes())
        full = np.asarray(render_recipe(image, EditRecipe(look="mono")), dtype=int)
        half = np.asarray(render_recipe(image, EditRecipe(look="mono", look_strength=50)), dtype=int)
        expected = (np.asarray(image, dtype=int) + full) / 2
        self.assertLessEqual(float(np.max(np.abs(half - expected))), 1)

    def test_vignette_keeps_center_and_dims_corners(self):
        result = render_recipe(Image.new("RGB", (101, 101), "white"), EditRecipe(vignette=100))
        self.assertEqual(result.getpixel((50, 50)), (255, 255, 255))
        self.assertLess(result.getpixel((0, 0))[0], result.getpixel((50, 0))[0])

    def test_auto_levels_ignore_hidden_pixels_and_flat_images(self):
        visible = Image.new("RGBA", (100, 1))
        visible.putdata([(60, 60, 60, 255)] * 50 + [(180, 180, 180, 255)] * 50)
        padded = Image.new("RGBA", (200, 1), (255, 0, 255, 0))
        padded.paste(visible, (0, 0))
        self.assertEqual(auto_levels(visible), auto_levels(padded))
        for color in ((100, 100, 100, 255), (255, 0, 0, 0)):
            self.assertEqual(auto_levels(Image.new("RGBA", (20, 20), color)), (0, 255))

    def test_sharpen_does_not_pull_hidden_colors_into_visible_pixels(self):
        a = Image.new("RGBA", (80, 50), (255, 0, 0, 0))
        b = Image.new("RGBA", a.size, (0, 0, 255, 0))
        for image in (a, b):
            image.paste((100, 150, 200, 255), (20, 10, 60, 40))
        aa = render_recipe(a, EditRecipe(sharpness=100))
        bb = render_recipe(b, EditRecipe(sharpness=100))
        self.assertEqual(aa.crop((20, 10, 60, 40)).tobytes(), bb.crop((20, 10, 60, 40)).tobytes())
        self.assertEqual(aa.getpixel((0, 0)), a.getpixel((0, 0)))

    def test_tiles_match_single_full_tile_across_both_boundaries(self):
        image = fixture(1100, 280)
        recipe = EditRecipe(exposure=10, warmth=30, shadows=20, look="warm", vignette=50, sharpness=70)
        tiled = render_recipe(image, recipe)
        with patch("local_ai_photo_editor.core.recipes._tiles", return_value=[(0, 0, 1100, 280)]):
            full = render_recipe(image, recipe)
        np.testing.assert_array_equal(np.asarray(tiled), np.asarray(full))

    def test_float_tile_size_is_bounded_even_for_extreme_aspect_ratios(self):
        for size in ((40_000_000, 1), (1, 40_000_000), (7000, 5000)):
            for left, top, right, bottom in _tiles(size):
                self.assertLessEqual((right - left) * (bottom - top), 262144)

    def test_render_is_deterministic_and_not_cumulative(self):
        image = fixture()
        recipe = EditRecipe(automatic=50, exposure=20, warmth=-30, look="vivid", sharpness=20)
        self.assertEqual(render_recipe(image, recipe).tobytes(), render_recipe(image, recipe).tobytes())

    def test_unsupported_modes_and_oversized_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            render_recipe(Image.new("I;16", (5, 5)), EditRecipe())
        image = Image.new("RGB", (2, 2))
        with patch.object(image, "_size", (40_000_001, 1)), self.assertRaises(ValueError):
            render_recipe(image, EditRecipe())


class GeometryAndBackgroundTests(unittest.TestCase):
    def test_exact_ratios_are_in_bounds_and_positions_reach_edges(self):
        size = (101, 71)
        for name, ratio in ASPECTS.items():
            for x, y in ((0, 0), (50, 50), (100, 100)):
                recipe = EditRecipe(aspect=name, focus_x=x, focus_y=y)
                left, top, right, bottom = crop_box(size, recipe)
                self.assertTrue(0 <= left < right <= size[0])
                self.assertTrue(0 <= top < bottom <= size[1])
                if ratio:
                    self.assertEqual((right - left) * ratio[1], (bottom - top) * ratio[0])
                if x == 0:
                    self.assertEqual((left, top), (0, 0))
                if x == 100:
                    self.assertEqual((right, bottom), size)

    def test_rotation_and_crop_dimensions_match_full_result(self):
        for turns in range(4):
            for aspect in ASPECTS:
                recipe = EditRecipe(quarter_turns=turns, aspect=aspect, mirror=True, flip=True)
                self.assertEqual(render_recipe(fixture(), recipe).size, output_size((85, 61), recipe))

    def test_mirrors_are_lossless_and_reversible(self):
        image = fixture()
        for recipe in (EditRecipe(mirror=True), EditRecipe(flip=True), EditRecipe(quarter_turns=2)):
            result = render_recipe(render_recipe(image, recipe), recipe)
            self.assertEqual(result.tobytes(), image.tobytes())

    def test_tiny_crop_fails_instead_of_returning_empty_image(self):
        with self.assertRaises(ValueError):
            render_recipe(Image.new("RGB", (2, 2)), EditRecipe(aspect="16:9"))

    def test_solid_background_uses_real_alpha_compositing(self):
        image = Image.new("RGBA", (3, 1))
        image.putdata([(200, 100, 50, 255), (200, 100, 50, 128), (200, 100, 50, 0)])
        original = image.tobytes()
        result = render_recipe(image, EditRecipe(background="solid", background_color=(20, 40, 80)))
        self.assertEqual(result.mode, "RGB")
        self.assertEqual(list(result.getdata()), [(200, 100, 50), (110, 70, 65), (20, 40, 80)])
        self.assertEqual(image.tobytes(), original)

    def test_opaque_input_and_missing_photo_are_rejected(self):
        for image in (Image.new("RGB", (10, 10)), Image.new("RGBA", (10, 10), (1, 2, 3, 255))):
            with self.assertRaises(ValueError):
                render_recipe(image, EditRecipe(background="solid"))
        with self.assertRaises(ValueError):
            render_recipe(fixture(), EditRecipe(background="photo"))

    def test_background_photo_is_fitted_and_blur_leaves_opaque_subject_unchanged(self):
        subject = Image.new("RGBA", (60, 40), (7, 8, 9, 0))
        subject.paste((100, 150, 200, 255), (20, 10, 40, 30))
        background = fixture(100, 70, alpha=False)
        before = background.tobytes()
        result = render_recipe(subject, EditRecipe(background="photo", background_blur=100), background_image=background)
        self.assertEqual(result.size, subject.size)
        self.assertEqual(result.getpixel((30, 20)), (100, 150, 200))
        self.assertEqual(background.tobytes(), before)

    def test_transparent_background_stays_transparent(self):
        result = render_recipe(Image.new("RGBA", (20, 20)), EditRecipe(background="photo", background_blur=50),
                               background_image=Image.new("RGBA", (40, 40), (255, 0, 0, 0)))
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.getchannel("A").getextrema(), (0, 0))

    def test_cancellation_before_and_during_work_never_mutates_source(self):
        image = fixture(1100, 300)
        original = image.tobytes()
        with self.assertRaises(RenderCancelled):
            render_recipe(image, EditRecipe(exposure=50), cancelled=lambda: True)
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            return calls >= 4
        with self.assertRaises(RenderCancelled):
            render_recipe(image, EditRecipe(exposure=50), cancelled=cancel)
        self.assertEqual(image.tobytes(), original)


if __name__ == "__main__":
    unittest.main()
