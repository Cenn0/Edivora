"""Precision selection and local-color invariants, not model-quality tests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageOps

from local_ai_photo_editor.core.mask import MaskStroke, paint_alpha_strokes
from local_ai_photo_editor.core.local_adjustments import LocalEdit, LOCAL_MODES, render_local
from local_ai_photo_editor.core.recipes import RenderCancelled
from local_ai_photo_editor.core.selection import MAX_SELECTION_ACTIONS, SelectionHistory, render_selection
from local_ai_photo_editor.core.subject import SUBJECT_MODES, SubjectEdit, render_subject


def stroke(mode="restore", x=.5, y=.5, feather=.35):
    return MaskStroke(((x, y),), mode, .12, feather)


class SelectionHistoryTests(unittest.TestCase):
    def test_undo_redo_reset_and_invert_are_deterministic(self):
        baseline = Image.new("L", (100, 80))
        baseline.paste(180, (10, 10, 40, 40))
        history = SelectionHistory()
        history.push(stroke())
        painted = render_selection(baseline, history.actions)
        history.push("invert")
        self.assertEqual(render_selection(baseline, history.actions).tobytes(), ImageOps.invert(painted).tobytes())
        history.undo()
        self.assertEqual(render_selection(baseline, history.actions).tobytes(), painted.tobytes())
        history.redo()
        history.push("reset")
        self.assertEqual(render_selection(baseline, history.actions).tobytes(), baseline.tobytes())
        history.undo()
        self.assertNotEqual(render_selection(baseline, history.actions).tobytes(), baseline.tobytes())

    def test_new_edit_clears_redo_but_invalid_edit_preserves_it(self):
        history = SelectionHistory()
        history.push("invert")
        history.undo()
        with self.assertRaises(ValueError):
            history.push("invalid")
        self.assertTrue(history.can_redo)
        history.push("clear")
        self.assertFalse(history.can_redo)
        self.assertEqual(history.actions, ("clear",))

    def test_action_count_is_bounded_and_undo_frees_capacity(self):
        history = SelectionHistory()
        for _ in range(MAX_SELECTION_ACTIONS):
            history.push("invert")
        with self.assertRaises(ValueError):
            history.push("clear")
        history.undo()
        history.push("clear")
        self.assertEqual(len(history.actions), MAX_SELECTION_ACTIONS)
        self.assertFalse(history.can_redo)

    def test_empty_history_is_owned_and_metadata_free(self):
        image = Image.new("L", (10, 10), 128)
        image.info["comment"] = "private"
        result = render_selection(image, ())
        self.assertIsNot(result, image)
        self.assertEqual(result.tobytes(), image.tobytes())
        self.assertEqual(result.info, {})
        self.assertEqual(image.info["comment"], "private")
        history = SelectionHistory()
        self.assertFalse(history.undo())
        self.assertFalse(history.redo())

    def test_clear_keeps_the_baseline_and_can_be_undone(self):
        baseline = Image.new("L", (20, 20), 100)
        history = SelectionHistory()
        history.push("clear")
        self.assertEqual(render_selection(baseline, history.actions).getextrema(), (0, 0))
        self.assertEqual(baseline.getextrema(), (100, 100))
        history.undo()
        self.assertEqual(render_selection(baseline, history.actions).getextrema(), (100, 100))

    def test_all_actions_are_validated_before_allocating_output(self):
        baseline = Image.new("L", (20, 20))
        with patch.object(baseline, "copy", side_effect=AssertionError("Must validate first")):
            for actions in ((stroke(), "bad"), (stroke(x=float("nan")),), (True,), ("clear",) * 129):
                with self.subTest(actions=actions), self.assertRaises(ValueError):
                    render_selection(baseline, actions)

    def test_rejects_unbounded_or_malformed_input(self):
        for actions in ([], None, (MaskStroke(((.5, .5),), "restore", .3),),
                        (MaskStroke(((.5, .5),) * 2049, "restore", .1),)):
            with self.subTest(actions=type(actions)), self.assertRaises(ValueError):
                render_selection(Image.new("L", (10, 10)), actions)
        with self.assertRaises(ValueError):
            render_selection(Image.new("RGB", (10, 10)), ())

    def test_cancel_before_and_during_replay_does_not_mutate_input(self):
        image = Image.new("L", (100, 100), 128)
        before = image.tobytes()
        with self.assertRaises(RenderCancelled):
            render_selection(image, (stroke(),), cancelled=lambda: True)
        calls = 0
        def cancelled():
            nonlocal calls
            calls += 1
            return calls >= 3
        with self.assertRaises(RenderCancelled):
            render_selection(image, (stroke(), "invert", stroke("erase")), cancelled=cancelled)
        self.assertEqual(image.tobytes(), before)


class SelectionRasterTests(unittest.TestCase):
    def test_raster_matches_existing_alpha_brush_including_soft_edges(self):
        rng = np.random.default_rng(11)
        for size in ((101, 77), (300, 150), (1, 25), (30, 1)):
            mask = Image.fromarray(rng.integers(0, 256, (size[1], size[0]), dtype=np.uint8))
            for mode in ("restore", "erase"):
                for feather in (0, .35, 1):
                    with self.subTest(size=size, mode=mode, feather=feather):
                        actions = (MaskStroke(((0., 0.), (.5, .6), (1., 1.)), mode, .15, feather),)
                        image = Image.new("RGBA", size, (10, 20, 30, 0))
                        image.putalpha(mask)
                        expected = paint_alpha_strokes(image, list(actions)).getchannel("A")
                        actual = render_selection(mask, actions)
                        self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_normalized_brush_lands_at_same_relative_position(self):
        for size in ((200, 100), (1000, 500)):
            mask = render_selection(Image.new("L", size), (stroke(x=.25, y=.75, feather=0),))
            self.assertEqual(mask.getpixel((round((size[0] - 1) * .25), round((size[1] - 1) * .75))), 255)
            self.assertEqual(mask.getpixel((size[0] - 1, 0)), 0)

    def test_corner_is_clipped_not_wrapped(self):
        result = render_selection(Image.new("L", (100, 100)), (stroke(x=0, y=0),))
        self.assertEqual(result.getpixel((0, 0)), 255)
        self.assertEqual(result.getpixel((99, 99)), 0)

    def test_brush_does_not_require_a_full_size_rgba_proxy(self):
        real_new = Image.new
        def new(mode, *args, **kwargs):
            self.assertEqual(mode, "L")
            return real_new(mode, *args, **kwargs)
        baseline = Image.new("L", (200, 100))
        with patch("local_ai_photo_editor.core.selection.Image.new", side_effect=new):
            render_selection(baseline, (stroke(),))


class LocalAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGBA", (80, 60), (100, 120, 170, 180))
        self.image.putpixel((40, 30), (70, 200, 20, 0))
        self.mask = Image.new("L", self.image.size)
        self.mask.paste(255, (20, 10, 60, 50))

    def test_new_modes_change_only_selected_colors_preserving_alpha(self):
        before = self.image.tobytes()
        for mode in ("warm", "cool", "vivid", "muted"):
            with self.subTest(mode=mode):
                result = render_local(self.image, self.mask, LocalEdit(mode, 75))
                self.assertNotEqual(result.getpixel((30, 20)), self.image.getpixel((30, 20)))
                self.assertEqual(result.getpixel((0, 0)), self.image.getpixel((0, 0)))
                self.assertEqual(result.getpixel((40, 30)), self.image.getpixel((40, 30)))
                self.assertEqual(result.getchannel("A").tobytes(), self.image.getchannel("A").tobytes())
                self.assertEqual(self.image.tobytes(), before)

    def test_temperature_and_full_desaturation_have_expected_directions(self):
        warm = render_local(self.image, self.mask, LocalEdit("warm", 100)).getpixel((30, 20))
        cool = render_local(self.image, self.mask, LocalEdit("cool", 100)).getpixel((30, 20))
        self.assertGreater(warm[0], cool[0])
        self.assertLess(warm[2], cool[2])
        muted = render_local(self.image, self.mask, LocalEdit("muted", 100)).getpixel((30, 20))
        self.assertEqual(muted[0], muted[1])
        self.assertEqual(muted[1], muted[2])

    def test_zero_strength_and_empty_mask_do_not_modify_colors(self):
        for mode in LOCAL_MODES[6:]:
            for mask, strength in ((self.mask, 0), (Image.new("L", self.mask.size), 100)):
                with self.subTest(mode=mode):
                    self.assertEqual(render_local(self.image, mask, LocalEdit(mode, strength)).tobytes(), self.image.tobytes())

    def test_existing_effects_are_pixel_identical_to_previous_adapter(self):
        for mode in SUBJECT_MODES:
            with self.subTest(mode=mode):
                expected = render_subject(self.image, self.mask, SubjectEdit(mode, 60, 10, 12))
                result = render_local(self.image, self.mask, LocalEdit(mode, 60, 10, 12))
                self.assertEqual((result.mode, result.size, result.tobytes()), (expected.mode, expected.size, expected.tobytes()))

    def test_invalid_parameters_and_mask_are_rejected(self):
        for values in ({"mode": "bad"}, {"strength": True}, {"strength": 101}, {"feather": -1}, {"padding": 41}):
            with self.assertRaises(ValueError):
                LocalEdit(**values)
        with self.assertRaises(ValueError):
            render_local(self.image, Image.new("L", (1, 1)), LocalEdit())
        with self.assertRaises(ValueError):
            render_local(self.image, self.mask, {})

    def test_cancellation_never_publishes_partial_result(self):
        before = self.image.tobytes()
        with self.assertRaises(RenderCancelled):
            render_local(self.image, self.mask, LocalEdit("warm", 80), cancelled=lambda: True)
        self.assertEqual(self.image.tobytes(), before)


if __name__ == "__main__":
    unittest.main()
