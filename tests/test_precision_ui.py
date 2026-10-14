"""Real Qt tests with synthetic/manual selections, not an AI quality benchmark."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import string
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image

from local_ai_photo_editor.core.local_adjustments import LocalEdit, LOCAL_MODES, render_local
from local_ai_photo_editor.core.mask import MaskStroke
from local_ai_photo_editor.core.selection import render_selection
from local_ai_photo_editor.core.recipes import RenderCancelled
from local_ai_photo_editor.ui.detail_strings import STRINGS

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class PrecisionTextTests(unittest.TestCase):
    def test_translation_keys_values_and_placeholders_match(self):
        self.assertEqual(STRINGS["de"].keys(), STRINGS["en"].keys())
        formatter = string.Formatter()
        for key in STRINGS["de"]:
            placeholders = lambda value: {field for _, field, _, _ in formatter.parse(value) if field}
            self.assertTrue(STRINGS["de"][key].strip())
            self.assertTrue(STRINGS["en"][key].strip())
            self.assertEqual(placeholders(STRINGS["de"][key]), placeholders(STRINGS["en"][key]))


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; interaction tests require Qt CI.")
class PrecisionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui.precision_dialog import PrecisionDialog
        from local_ai_photo_editor.ui.precision_window import EditorWindow
        cls.app = QApplication.instance() or QApplication([])
        cls.dialog_type, cls.window_type = PrecisionDialog, EditorWindow
        cls.qtest, cls.qt, cls.point, cls.pointf = QTest, Qt, QPoint, QPointF

    def setUp(self):
        self.window = self.window_type()
        self.image = Image.new("RGBA", (1200, 800), (80, 130, 190, 200))
        self.image.paste((120, 170, 80, 255), (300, 200, 900, 600))
        self.mask = Image.new("L", self.image.size)
        self.mask.paste(255, (300, 200, 900, 600))
        self.window.set_document(self.image)
        self.dialogs = []

    def wait_until(self, condition):
        deadline = time.monotonic() + 12
        while not condition() and time.monotonic() < deadline:
            self.qtest.qWait(10)
        self.assertTrue(condition(), "Qt operation exceeded test deadline")

    def dialog(self, mode="light", *, manual=False):
        dialog = self.dialog_type(self.image, "de", mode, self.window, manual=manual, start_immediately=False)
        self.dialogs.append(dialog)
        if not manual:
            dialog._install_selection(self.mask)
        return dialog

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.reject()
            self.wait_until(lambda d=dialog: not d.is_busy)
            dialog.deleteLater()
        self.window._editing_dialog = None
        self.window._close_approved = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_manual_path_never_starts_model_and_requires_a_painted_area(self):
        from local_ai_photo_editor.ui.subject_job import SubjectSelectionJob
        with patch.object(SubjectSelectionJob, "start") as start:
            dialog = self.dialog(manual=True)
            self.app.processEvents()
            start.assert_not_called()
            self.assertFalse(dialog.apply_button.isEnabled())
            self.assertFalse(dialog._start_timer.isActive())
            dialog.push_selection(MaskStroke(((.5, .5),), "restore", .15))
            self.assertGreater(dialog._working_preview_mask.getextrema()[1], 0)
            self.assertFalse(dialog.apply_button.isEnabled())
            dialog.brush_button.click()
            self.assertTrue(dialog.apply_button.isEnabled())

    def test_brush_changes_selection_only_and_cancel_preserves_document(self):
        dialog = self.dialog()
        original, mask = self.image.tobytes(), dialog._mask.tobytes()
        dialog.brush_button.click()
        dialog.brush_mode.setCurrentIndex(1)
        dialog._stroke_finished(((.5, .5),))
        self.assertEqual(dialog._mask.tobytes(), mask)
        self.assertEqual(self.window.document.current.tobytes(), original)
        self.assertEqual(dialog._working_preview_mask.getpixel((480, 320)), 0)
        dialog.reject()
        self.assertIsNone(dialog.result_image)
        self.assertEqual(len(self.window.document.history), 0)

    def test_all_selection_commands_are_undoable_and_do_not_rerun_ai(self):
        dialog = self.dialog()
        with patch.object(dialog.job, "start") as inference:
            original = dialog._working_preview_mask.tobytes()
            for command in ("invert", "clear", "reset"):
                dialog.push_selection(command)
            self.assertEqual(dialog._working_preview_mask.tobytes(), original)
            dialog.undo_selection()
            self.assertEqual(dialog._working_preview_mask.getextrema(), (0, 0))
            dialog.redo_selection()
            self.assertEqual(dialog._working_preview_mask.tobytes(), original)
            inference.assert_not_called()

    def test_invalid_selection_change_preserves_journal(self):
        dialog = self.dialog()
        dialog.push_selection("invert")
        dialog.undo_selection()
        dialog.push_selection(MaskStroke(((float("nan"), .5),), "restore", .1))
        self.assertEqual(dialog.selection_history.actions, ())
        self.assertTrue(dialog.selection_history.can_redo)
        self.assertFalse(dialog.apply_button.isEnabled())

    def test_all_ten_modes_reuse_the_corrected_selection(self):
        dialog = self.dialog()
        dialog.push_selection(MaskStroke(((.5, .5),), "erase", .1))
        original = dialog._working_preview_mask.tobytes()
        with patch.object(dialog.job, "start") as inference:
            for mode in LOCAL_MODES:
                with self.subTest(mode=mode):
                    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(mode))
                    dialog._render_preview()
                    self.assertTrue(dialog._preview_valid)
                    self.assertEqual(dialog._working_preview_mask.tobytes(), original)
            inference.assert_not_called()

    def test_full_render_uses_corrected_full_size_selection_and_latest_settings(self):
        dialog = self.dialog("warm")
        dialog.push_selection("invert")
        dialog.push_selection(MaskStroke(((.5, .5),), "restore", .1))
        dialog.strength.setValue(80)
        expected_mask = render_selection(self.mask, dialog.selection_history.actions)
        expected = render_local(self.image, expected_mask, LocalEdit("warm", 80))
        dialog.accept()
        self.wait_until(lambda: not dialog.is_busy)
        self.assertEqual(dialog.result_image.size, self.image.size)
        self.assertEqual(dialog.result_image.tobytes(), expected.tobytes())

    def test_crop_after_correction_is_calculated_at_full_resolution(self):
        dialog = self.dialog("crop", manual=True)
        dialog.push_selection(MaskStroke(((.25, .4), (.4, .5)), "restore", .1))
        dialog.brush_button.click()
        expected = render_local(self.image, render_selection(dialog._mask, dialog.selection_history.actions), dialog.edit)
        dialog.accept()
        self.wait_until(lambda: not dialog.is_busy)
        self.assertEqual((dialog.result_image.size, dialog.result_image.tobytes()), (expected.size, expected.tobytes()))

    def test_changing_brush_settings_does_not_rewrite_previous_strokes(self):
        dialog = self.dialog(manual=True)
        dialog._stroke_finished(((.5, .5),))
        actions = dialog.selection_history.actions
        dialog.brush_size.setValue(150)
        dialog.brush_softness.setValue(0)
        dialog._render_preview()
        self.assertEqual(dialog.selection_history.actions, actions)
        self.assertEqual(actions[0].diameter, .04)
        self.assertEqual(actions[0].feather, .35)

    def test_empty_selection_disables_apply_and_reset_keeps_journal(self):
        dialog = self.dialog("warm")
        dialog.push_selection("clear")
        dialog.reset_settings()
        dialog._render_preview()
        self.assertFalse(dialog.apply_button.isEnabled())
        self.assertEqual(dialog.selection_history.actions, ("clear",))
        dialog.undo_selection()
        self.assertTrue(dialog.apply_button.isEnabled())

    def test_zero_strength_disables_apply_and_new_modes_have_valid_defaults(self):
        dialog = self.dialog("cool")
        self.assertEqual(dialog.edit.strength, 35)
        dialog.strength.setValue(0)
        dialog._render_preview()
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.accept()
        self.assertIsNone(dialog.result_image)

    def test_inference_failure_can_fall_back_to_manual_selection(self):
        dialog = self.dialog_type(self.image, "de", "warm", self.window, start_immediately=False)
        self.dialogs.append(dialog)
        dialog._selection_finished(None, "MODEL_MISSING", False)
        self.assertFalse(dialog.manual_button.isHidden())
        with patch.object(dialog.job, "start") as inference:
            dialog.manual_button.click()
            self.assertIsNotNone(dialog._mask)
            self.assertTrue(dialog.brush_button.isChecked())
            inference.assert_not_called()

    def test_navigation_preserves_pointer_location_and_clamps_bounds(self):
        dialog = self.dialog()
        dialog.show()
        self.app.processEvents()
        canvas = dialog.canvas
        point = canvas.image_rect.center()
        before = canvas._normalized_point(point)
        canvas.set_zoom(3, point)
        after = canvas._normalized_point(point)
        self.assertAlmostEqual(before.x(), after.x())
        self.assertAlmostEqual(before.y(), after.y())
        canvas.pan_by(self.pointf(1e9, 1e9))
        self.assertLessEqual(canvas.image_rect.left(), 28.01)
        self.assertLessEqual(canvas.image_rect.top(), 28.01)
        canvas.set_zoom(100)
        self.assertEqual(canvas.zoom_factor, 8)
        canvas.set_zoom(.1)
        self.assertEqual(canvas.zoom_factor, 1)
        with self.assertRaises(ValueError):
            canvas.set_zoom(float("nan"))

    def test_zoom_survives_parameter_preview_but_resets_for_changed_geometry(self):
        dialog = self.dialog()
        canvas = dialog.canvas
        canvas.set_zoom(3)
        dialog.strength.setValue(50)
        dialog._render_preview()
        self.assertEqual(canvas.zoom_factor, 3)
        canvas.set_image(Image.new("RGB", (100, 100)), (100, 100))
        self.assertEqual(canvas.zoom_factor, 1)

    def test_zoom_and_pan_do_not_shift_an_active_brush_stroke(self):
        dialog = self.dialog(manual=True)
        canvas = dialog.canvas
        canvas._brush_points = [self.pointf(.5, .5)]
        before = canvas.image_rect
        canvas.set_zoom(5)
        canvas.pan_by(self.pointf(100, 100))
        self.assertEqual(canvas.image_rect, before)
        canvas._brush_points = None

    def test_panning_does_not_paint_and_keyboard_zoom_is_available(self):
        dialog = self.dialog(manual=True)
        dialog.show()
        self.app.processEvents()
        canvas = dialog.canvas
        canvas.set_zoom(2)
        center = canvas.image_rect.center().toPoint()
        self.qtest.mousePress(canvas, self.qt.MouseButton.MiddleButton, pos=center)
        self.qtest.mouseMove(canvas, center + self.point(30, 10))
        self.qtest.mouseRelease(canvas, self.qt.MouseButton.MiddleButton, pos=center + self.point(30, 10))
        self.assertEqual(dialog.selection_history.actions, ())
        self.qtest.keyClick(canvas, self.qt.Key.Key_Plus)
        self.assertGreater(canvas.zoom_factor, 2)
        self.qtest.keyClick(canvas, self.qt.Key.Key_Home)
        self.assertEqual(canvas.zoom_factor, 1)

    def test_zoomed_brush_hits_the_visible_normalized_coordinate(self):
        dialog = self.dialog(manual=True)
        dialog.show()
        self.app.processEvents()
        canvas = dialog.canvas
        canvas.set_zoom(3)
        position = self.point(canvas.width() // 2 + 20, canvas.height() // 2)
        expected = canvas._normalized_point(self.pointf(position))
        self.qtest.mouseClick(canvas, self.qt.MouseButton.LeftButton, pos=position)
        self.assertEqual(len(dialog.selection_history.actions), 1)
        point = dialog.selection_history.actions[0].points[0]
        self.assertAlmostEqual(point[0], expected.x(), places=4)
        self.assertAlmostEqual(point[1], expected.y(), places=4)

    def test_window_controls_respect_pending_adjustments_and_translation(self):
        self.window.set_language("en")
        self.assertEqual(self.window.manual_selection_button.text(), STRINGS["en"]["detail_manual"])
        self.window.sliders["brightness"].setValue(110)
        self.assertFalse(self.window.manual_selection_action.isEnabled())
        self.window.discard_adjustments()
        self.assertTrue(self.window.manual_selection_action.isEnabled())

    def test_accepted_precise_edit_is_one_document_undo_redo_step(self):
        def accept(dialog):
            dialog._install_selection(self.mask)
            dialog.push_selection("invert")
            dialog.accept()
            self.wait_until(lambda: not dialog.is_busy)
            return dialog.result()
        with patch.object(self.dialog_type, "exec", accept):
            self.window.show_ai_tools("warm")
        self.assertEqual(len(self.window.document.history), 1)
        result = self.window.document.current.tobytes()
        self.window.undo()
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())
        self.window.redo()
        self.assertEqual(self.window.document.current.tobytes(), result)

    def test_cancelling_render_never_commits_partial_selection_or_pixels(self):
        dialog = self.dialog("warm")
        started = threading.Event()
        def slow(*args, **kwargs):
            started.set()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if kwargs["cancelled"]():
                    raise RenderCancelled()
                time.sleep(.005)
            raise RuntimeError("Cancellation was not delivered")
        with patch("local_ai_photo_editor.ui.precision_dialog.render_local", side_effect=slow):
            dialog.accept()
            self.wait_until(started.is_set)
            dialog.reject()
            self.wait_until(lambda: not dialog.is_busy)
        self.assertIsNone(dialog.result_image)
        self.assertEqual(len(self.window.document.history), 0)

    def test_failed_render_preserves_photo_and_restores_controls(self):
        dialog = self.dialog("warm")
        with patch("local_ai_photo_editor.ui.precision_dialog.render_local", side_effect=MemoryError()):
            dialog.accept()
            self.wait_until(lambda: not dialog.is_busy)
        self.assertIsNone(dialog.result_image)
        self.assertTrue(dialog.panel.isEnabled())
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())

    def test_capture_actual_precision_controls_in_both_languages(self):
        # The existing CI artifact step retains these synthetic UI diagnostics.
        output = Path("test-results/precision-ui")
        output.mkdir(parents=True, exist_ok=True)
        for language in ("de", "en"):
            dialog = self.dialog_type(self.image, language, "warm", self.window, start_immediately=False)
            self.dialogs.append(dialog)
            dialog._install_selection(self.mask)
            dialog.show()
            self.app.processEvents()
            for mode in ("warm", "cool", "vivid", "muted"):
                dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(mode))
                dialog._render_preview()
                self.app.processEvents()
                self.assertTrue(dialog.grab().save(str(output / f"precision-{mode}-{language}.png")))
            dialog.brush_button.click()
            dialog.canvas.set_zoom(2)
            self.app.processEvents()
            self.assertTrue(dialog.grab().save(str(output / f"precision-brush-{language}.png")))
            dialog.reject()


if __name__ == "__main__":
    unittest.main()
