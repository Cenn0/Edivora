"""Regression checks for the simple first-run layout and disclosure workflow."""
from __future__ import annotations

import importlib.util
import os
import unittest
from unittest.mock import patch

from PIL import Image

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; GUI tests run in Qt CI.")
class BeginnerWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui import EditorWindow

        cls.app = QApplication.instance() or QApplication([])
        cls.window_type = EditorWindow

    def setUp(self) -> None:
        self.window = self.window_type()
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window._close_approved = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def open_image(self) -> None:
        self.window.set_document(Image.new("RGBA", (96, 64), (100, 140, 180, 225)))
        self.app.processEvents()

    def test_start_screen_shows_four_clear_tasks_not_precision_widgets(self) -> None:
        self.assertTrue(self.window.open_button.isEnabled())
        self.assertFalse(self.window.export_button.isEnabled())
        self.assertTrue(self.window.save_project_button.isHidden())
        self.assertFalse(self.window.save_project_action.isEnabled())
        self.assertEqual(len(self.window.quick_buttons), 4)
        self.assertTrue(all(not b.isEnabled() for b in self.window.quick_buttons))
        self.assertTrue(self.window.more_tools_panel.isHidden())
        self.assertIn("Öffne ein Foto", self.window.quick_hint_label.text())
        self.assertIn("Weitere Möglichkeiten", self.window.more_tools_button.text())

    def test_advanced_tools_are_revealed_only_on_demand(self) -> None:
        self.open_image()
        self.assertTrue(all(button.isEnabled() for button in self.window.quick_buttons))
        self.assertTrue(self.window.more_tools_panel.isHidden())
        self.window.more_tools_button.click()
        self.app.processEvents()
        self.assertFalse(self.window.more_tools_panel.isHidden())
        self.assertTrue(all(button.isEnabled() for button in self.window.editing_buttons))
        self.assertTrue(all(button.isEnabled() for button in self.window.subject_buttons))
        self.assertTrue(self.window.mask_button.isEnabled())
        self.assertTrue(self.window.ai_button.isEnabled())
        self.window.more_tools_button.click()
        self.assertTrue(self.window.more_tools_panel.isHidden())

    def test_quick_ai_cutout_uses_preview_dialog_not_direct_ai_apply(self) -> None:
        self.open_image()
        with patch.object(self.window, "show_editing_tools") as edit, \\
                patch.object(self.window, "show_ai_tools") as ai, \\
                patch.object(self.window, "start_background_removal") as direct:
            self.window.quick_buttons[0].click()
            self.window.quick_buttons[1].click()
            self.window.quick_buttons[2].click()
            self.window.quick_buttons[3].click()
        self.assertEqual([c.args for c in edit.call_args_list], [("light",), ("shape",)])
        self.assertEqual([c.args for c in ai.call_args_list], [("blur",), ("cutout",)])
        direct.assert_not_called()
        self.assertEqual(self.window.document.history, ())

    def test_pending_slider_changes_auto_expand_and_lock_their_controls(self) -> None:
        self.open_image()
        self.window.sliders["brightness"].setValue(115)
        self.app.processEvents()
        self.assertTrue(self.window.has_pending_adjustments)
        self.assertFalse(self.window.more_tools_panel.isHidden())
        self.assertTrue(self.window.more_tools_button.isChecked())
        self.assertFalse(self.window.more_tools_button.isEnabled())
        self.assertTrue(all(not b.isEnabled() for b in self.window.quick_buttons))
        self.assertTrue(self.window.apply_button.isEnabled())
        self.assertIn("Übernimm oder verwirf", self.window.quick_hint_label.text())
        self.window.discard_adjustments()
        self.assertTrue(self.window.more_tools_button.isEnabled())
        self.assertTrue(all(b.isEnabled() for b in self.window.quick_buttons))
        # The user may now fold the optional controls away again.
        self.window.more_tools_button.click()
        self.assertTrue(self.window.more_tools_panel.isHidden())

    def test_crop_and_original_comparison_do_not_leave_blocked_actions(self) -> None:
        self.open_image()
        self.window.more_tools_button.click()
        self.window.crop_button.click()
        self.assertFalse(self.window.more_tools_button.isEnabled())
        self.assertIn("Zuschnitt", self.window.quick_hint_label.text())
        self.window.crop_button.click()
        self.assertTrue(self.window.more_tools_button.isEnabled())
        self.window.original_button.click()
        self.assertTrue(all(not b.isEnabled() for b in self.window.quick_buttons))
        self.assertIn("Original", self.window.quick_hint_label.text())
        self.window.original_button.click()
        self.assertTrue(all(b.isEnabled() for b in self.window.quick_buttons))

    def test_switching_language_keeps_disclosure_and_translations(self) -> None:
        self.open_image()
        self.window.more_tools_button.click()
        self.window.set_language("en")
        self.assertEqual(self.window.quick_buttons[0].text(), "Enhance photo …")
        self.assertEqual(self.window.quick_buttons[3].text(), "Remove background (AI) …")
        self.assertEqual(self.window.more_tools_button.text(), "Show fewer options ▴")
        self.assertIn("Export a copy", self.window.quick_hint_label.text())
        self.assertFalse(self.window.more_tools_panel.isHidden())
        self.window.more_tools_button.click()
        self.assertEqual(self.window.more_tools_button.text(), "Show more options ▾")
        self.window.set_language("de")
        self.assertIn("Weitere Möglichkeiten", self.window.more_tools_button.text())


if __name__ == "__main__":
    unittest.main()
