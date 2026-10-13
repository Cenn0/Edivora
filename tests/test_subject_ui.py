"""Qt interaction and process tests. Fake worker fixtures do not prove model quality."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import string
import sys
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image

from local_ai_photo_editor.core.subject import SubjectEdit, render_subject
from local_ai_photo_editor.core.recipes import RenderCancelled
from local_ai_photo_editor.ui.subject_strings import STRINGS

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


def fixture():
    image = Image.new("RGBA", (1000, 640), (40, 60, 120, 128))
    image.paste((90, 150, 50, 255), (250, 160, 750, 480))
    mask = Image.new("L", image.size)
    mask.paste(255, (250, 160, 750, 480))
    return image, mask


class SubjectTranslationTests(unittest.TestCase):
    def test_keys_placeholders_and_nonempty_text_match(self):
        self.assertEqual(STRINGS["de"].keys(), STRINGS["en"].keys())
        formatter = string.Formatter()
        for key in STRINGS["de"]:
            fields = lambda value: {field for _, field, _, _ in formatter.parse(value) if field}
            self.assertTrue(STRINGS["de"][key].strip())
            self.assertTrue(STRINGS["en"][key].strip())
            self.assertEqual(fields(STRINGS["de"][key]), fields(STRINGS["en"][key]))


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; Qt coverage requires CI.")
class SubjectUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui import EditorWindow
        from local_ai_photo_editor.ui.subject_dialog import SubjectDialog
        cls.app = QApplication.instance() or QApplication([])
        cls.window_type, cls.dialog_type, cls.qtest = EditorWindow, SubjectDialog, QTest

    def setUp(self):
        self.window = self.window_type()
        self.image, self.mask = fixture()
        self.window.set_document(self.image)
        self.dialogs = []

    def wait_until(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.qtest.qWait(10)
        self.assertTrue(predicate(), "Qt operation did not finish before the test deadline")

    def dialog(self, mode="blur", selected=True):
        dialog = self.dialog_type(self.image, "de", mode, self.window, start_immediately=False)
        self.dialogs.append(dialog)
        if selected:
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

    def test_ai_buttons_respect_existing_preview_crop_and_comparison(self):
        self.assertTrue(self.window.subject_action.isEnabled())
        self.window.set_language("en")
        self.assertEqual(self.window.subject_buttons[0].text(), "Soften background …")
        self.window.sliders["brightness"].setValue(110)
        self.assertFalse(self.window.subject_action.isEnabled())
        self.window.discard_adjustments()
        self.window.crop_button.click()
        self.assertFalse(self.window.subject_action.isEnabled())
        self.window.crop_button.click()
        self.window.original_button.click()
        self.assertFalse(self.window.subject_action.isEnabled())

    def test_effects_require_a_selection_and_explicit_accept(self):
        dialog = self.dialog(selected=False)
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.accept()
        self.assertIsNone(dialog.result_image)
        dialog._install_selection(self.mask)
        self.assertTrue(dialog.apply_button.isEnabled())
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())
        self.assertEqual(len(self.window.document.history), 0)

    def test_switching_all_effects_reuses_the_same_inferred_mask(self):
        dialog = self.dialog()
        original_mask = dialog._mask.tobytes()
        with patch.object(dialog.job, "start") as inference:
            for mode in ("blur", "color_pop", "light", "dim", "cutout", "crop"):
                dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(mode))
                dialog._render_preview()
                self.assertTrue(dialog._preview_valid)
                self.assertEqual(dialog._mask.tobytes(), original_mask)
            inference.assert_not_called()

    def test_apply_uses_latest_settings_and_full_resolution_not_the_overlay(self):
        dialog = self.dialog("light")
        dialog.strength.setValue(10)
        dialog._render_preview()
        dialog.selection_check.setChecked(True)
        dialog.strength.setValue(70)
        expected = render_subject(self.image, self.mask, SubjectEdit("light", strength=70))
        dialog.accept()
        self.wait_until(lambda: not dialog.is_busy)
        self.assertEqual(dialog.result_image.size, self.image.size)
        self.assertEqual(dialog.result_image.tobytes(), expected.tobytes())
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())

    def test_before_and_selection_views_do_not_change_results(self):
        dialog = self.dialog("color_pop")
        expected = dialog._preview_result.tobytes()
        dialog.compare_button.click()
        self.assertEqual(dialog.status.text(), STRINGS["de"]["before_status"])
        dialog.compare_button.click()
        dialog.selection_check.setChecked(True)
        self.assertEqual(dialog.status.text(), STRINGS["de"]["selected_status"])
        self.assertEqual(dialog._preview_result.tobytes(), expected)

    def test_zero_strength_disables_empty_color_edit_and_reset_restores_defaults(self):
        dialog = self.dialog("light")
        dialog.strength.setValue(0)
        dialog._render_preview()
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.accept()
        self.assertFalse(dialog.is_busy)
        dialog.feather.setValue(20)
        dialog.reset_settings()
        self.assertEqual(dialog.edit, SubjectEdit("light", strength=35))

    def test_cancel_stops_queued_inference_and_creates_no_history(self):
        dialog = self.dialog_type(self.image, "de", "blur", self.window)
        self.dialogs.append(dialog)
        with patch.object(dialog.job, "start") as inference:
            dialog.reject()
            self.app.processEvents()
            inference.assert_not_called()
        self.assertIsNone(dialog.result_image)
        self.assertEqual(len(self.window.document.history), 0)

    def test_inference_failure_is_recoverable_and_never_enables_apply(self):
        dialog = self.dialog(selected=False)
        dialog._selection_finished(None, "MODEL_MISSING", False)
        self.assertIn("Modell fehlt", dialog.status.text())
        self.assertFalse(dialog.apply_button.isEnabled())
        self.assertFalse(dialog.retry_button.isHidden())
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())

    def test_uniform_or_wrong_size_selections_are_not_accepted(self):
        dialog = self.dialog(selected=False)
        for mask in (Image.new("L", self.image.size, 0), Image.new("L", (2, 2))):
            with self.assertRaises(ValueError):
                dialog._install_selection(mask)
        self.assertFalse(dialog.apply_button.isEnabled())

    def test_accepted_ai_edit_is_one_reversible_document_step(self):
        def accept(dialog):
            dialog._install_selection(self.mask)
            dialog.accept()
            self.wait_until(lambda: not dialog.is_busy)
            return dialog.result()
        with patch.object(self.dialog_type, "exec", accept):
            self.window.show_ai_tools("color_pop")
        result = self.window.document.current.tobytes()
        self.assertNotEqual(result, self.image.tobytes())
        self.assertEqual(len(self.window.document.history), 1)
        self.window.undo()
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())
        self.window.redo()
        self.assertEqual(self.window.document.current.tobytes(), result)
        self.assertEqual(self.window.document.original.tobytes(), self.image.tobytes())

    def test_changed_document_rejects_stale_ai_result(self):
        replacement = Image.new("RGB", (12, 8), "blue")
        def stale(dialog):
            dialog._start_timer.stop()
            dialog.result_image = self.image
            self.window.set_document(replacement)
            return 1
        with patch.object(self.dialog_type, "exec", stale):
            self.window.show_ai_tools()
        self.assertEqual(self.window.document.current.tobytes(), replacement.tobytes())

    def test_cancel_during_full_render_waits_then_discards_the_result(self):
        dialog = self.dialog()
        started = threading.Event()
        def slow_render(*args, **kwargs):
            started.set()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if kwargs["cancelled"]():
                    raise RenderCancelled()
                time.sleep(.005)
            raise RuntimeError("Cancellation was not requested")
        with patch("local_ai_photo_editor.ui.subject_dialog.render_subject", side_effect=slow_render):
            dialog.accept()
            self.wait_until(started.is_set)
            dialog.reject()
            self.wait_until(lambda: not dialog.is_busy)
        self.assertIsNone(dialog.result_image)
        self.assertEqual(dialog.result(), 0)

    def test_render_error_leaves_the_accepted_photo_and_retry_controls_usable(self):
        dialog = self.dialog("light")
        with patch("local_ai_photo_editor.ui.subject_dialog.render_subject", side_effect=MemoryError()):
            dialog.accept()
            self.wait_until(lambda: not dialog.is_busy)
        self.assertIsNone(dialog.result_image)
        self.assertTrue(dialog.panel.isEnabled())
        self.assertEqual(self.window.document.current.tobytes(), self.image.tobytes())


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; native process lifecycle requires CI.")
class SubjectProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.qtest = QTest

    def run_job(self, script, *, cancel=False, timeout=5000, missing=False):
        from local_ai_photo_editor.ui.subject_job import SubjectSelectionJob
        job = SubjectSelectionJob(timeout_ms=timeout)
        outcomes, directories = [], []
        job.finished.connect(lambda mask, error, cleanup: outcomes.append((mask, error, cleanup)))
        def command(directory):
            # Windows can emit FailedToStart synchronously from start(). Capture
            # the owned directory before that callback performs its cleanup.
            directories.append(Path(directory))
            return (str(Path(directory) / "does-not-exist.exe"), []) if missing else (sys.executable, ["-c", script, str(directory)])
        with patch("local_ai_photo_editor.__main__.worker_command", side_effect=command):
            job.start(Image.new("RGB", (48, 32), "blue"))
            if cancel:
                job.cancel()
            deadline = time.monotonic() + 10
            while job.is_running and time.monotonic() < deadline:
                self.qtest.qWait(10)
            if job.is_running:
                job.cancel()
                self.qtest.qWait(1000)
            self.assertFalse(job.is_running)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(len(directories), 1)
        self.assertFalse(directories[0].exists())
        job.deleteLater()
        self.app.processEvents()
        return outcomes[0]

    def test_real_child_process_returns_validated_mask_and_is_cleaned_up(self):
        script = '''from pathlib import Path
import json, sys
from PIL import Image
from local_ai_photo_editor.core.selection_io import write_subject_result
p = Path(sys.argv[-1])
m = Image.new("L", (48,32))
m.paste(255, (12,8,36,24))
(p / "result.json").write_text(json.dumps(write_subject_result(m,p)))
'''
        mask, error, cleanup_failed = self.run_job(script)
        self.assertEqual(error, "")
        self.assertFalse(cleanup_failed)
        self.assertEqual(mask.mode, "L")
        self.assertEqual(mask.getpixel((24, 16)), 255)

    def test_cancel_before_process_start_cannot_publish_result(self):
        mask, error, cleanup_failed = self.run_job("import time; time.sleep(10)", cancel=True)
        self.assertIsNone(mask)
        self.assertEqual(error, "CANCELLED")
        self.assertFalse(cleanup_failed)

    def test_timeout_stops_and_cleans_the_child_process(self):
        mask, error, cleanup_failed = self.run_job("import time; time.sleep(10)", timeout=30)
        self.assertIsNone(mask)
        self.assertEqual(error, "TIMEOUT")
        self.assertFalse(cleanup_failed)

    def test_failed_start_is_reported_once_and_cleaned(self):
        mask, error, cleanup_failed = self.run_job("", missing=True)
        self.assertIsNone(mask)
        self.assertEqual(error, "START_FAILED")
        self.assertFalse(cleanup_failed)


if __name__ == "__main__":
    unittest.main()
