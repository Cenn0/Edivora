"""Regression coverage for precision-dialog state transitions."""
from __future__ import annotations

import importlib.util
import os
import time
import unittest
from unittest.mock import patch

from PIL import Image

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; these regressions require Qt.")
class PrecisionStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from local_ai_photo_editor.ui.precision_dialog import PrecisionDialog
        cls.app = QApplication.instance() or QApplication([])
        cls.dialog_type, cls.qtest = PrecisionDialog, QTest

    def setUp(self):
        self.image = Image.new("RGB", (100, 80), (100, 120, 150))
        self.mask = Image.new("L", self.image.size)
        self.mask.paste(255, (20, 20, 80, 60))
        self.dialog = self.dialog_type(self.image, "de", "warm", start_immediately=False)

    def wait(self):
        deadline = time.monotonic() + 10
        while self.dialog.is_busy and time.monotonic() < deadline:
            self.qtest.qWait(10)
        self.assertFalse(self.dialog.is_busy)

    def tearDown(self):
        self.dialog.reject()
        self.wait()
        self.dialog.deleteLater()
        self.app.processEvents()

    def test_apply_reuses_current_preview_before_starting_full_render(self):
        self.dialog._install_selection(self.mask)
        with patch.object(self.dialog, "_render_preview", side_effect=AssertionError("Unnecessary preview work")):
            self.dialog.accept()
            self.wait()
        self.assertIsNotNone(self.dialog.result_image)

    def test_dirty_preview_is_refreshed_before_full_render(self):
        self.dialog._install_selection(self.mask)
        self.dialog.strength.setValue(80)
        with patch.object(self.dialog, "_render_preview", wraps=self.dialog._render_preview) as preview:
            self.dialog.accept()
            self.wait()
            preview.assert_called_once()
        self.assertIsNotNone(self.dialog.result_image)

    def test_invalid_model_replacement_preserves_mask_history_and_preview(self):
        self.dialog._install_selection(self.mask)
        self.dialog.push_selection("invert")
        before = self.dialog._working_preview_mask.tobytes()
        for invalid in (Image.new("L", self.image.size), Image.new("L", (2, 2)), None):
            with self.assertRaises(ValueError):
                self.dialog._install_selection(invalid)
            self.assertEqual(self.dialog.selection_history.actions, ("invert",))
            self.assertEqual(self.dialog._working_preview_mask.tobytes(), before)
            self.assertEqual(self.dialog._mask.tobytes(), self.mask.tobytes())

    def test_manual_allocation_failure_keeps_a_recoverable_empty_dialog(self):
        with patch("local_ai_photo_editor.ui.precision_dialog.Image.new", side_effect=MemoryError()):
            self.dialog.start_manual_selection()
        self.assertIsNone(self.dialog._mask)
        self.assertFalse(self.dialog.apply_button.isEnabled())
        self.assertFalse(self.dialog.is_busy)
        self.dialog.start_manual_selection()
        self.assertIsNotNone(self.dialog._mask)
        self.assertTrue(self.dialog.brush_button.isChecked())


if __name__ == "__main__":
    unittest.main()
