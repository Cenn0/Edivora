"""New shared Edivora shell behavior on source Qt, with synthetic photos only."""
from __future__ import annotations

import importlib.util
import os
import unittest
from unittest.mock import patch

from PIL import Image

from local_ai_photo_editor.ui.strings import STRINGS
from local_ai_photo_editor.ui.theme import COLORS, stylesheet

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class EdivoraTokenTests(unittest.TestCase):
    def test_design_palette_is_one_source_of_truth(self) -> None:
        self.assertEqual(COLORS["app"], "#171B2D")
        self.assertEqual(COLORS["primary"], "#4FF3D3")
        self.assertEqual(COLORS["ai"], "#C98CFF")
        css = stylesheet()
        self.assertIn("QFrame#navRail", css)
        self.assertIn("QPushButton#quickAiAction", css)
        self.assertIn("#4FF3D3", css)
        self.assertNotIn("$primary", css)

    def test_suite_labels_translate_both_ways(self) -> None:
        for key in ("nav_start", "nav_photo", "nav_video", "nav_audio",
                    "home_planned", "home_title", "home_import_title",
                    "finish_task_first", "home_continue", "compare_compact"):
            self.assertIn(key, STRINGS["de"])
            self.assertIn(key, STRINGS["en"])


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; run the Qt UI tests in CI.")
class EdivoraShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui import EditorWindow
        cls.app = QApplication.instance() or QApplication([])
        cls.editor = EditorWindow

    def setUp(self) -> None:
        self.window = self.editor()
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window._close_approved = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_start_hub_and_navigation_enable_the_available_media_mvp(self) -> None:
        w = self.window
        self.assertEqual(w.windowTitle(), "Edivora · Foto")
        self.assertIs(w.stage_stack.currentWidget(), w.home_page)
        self.assertTrue(w.nav_start.isChecked())
        self.assertTrue(w.nav_video.isEnabled())
        self.assertTrue(w.nav_audio.isEnabled())
        self.assertEqual(len(w.home_media_buttons), 3)
        self.assertTrue(w.home_media_buttons[0].isEnabled())
        self.assertTrue(w.home_media_buttons[1].isEnabled())
        self.assertTrue(w.home_media_buttons[2].isEnabled())
        self.assertTrue(w.home_continue_button.isHidden())

    def test_opened_photo_appears_on_canvas_and_can_be_resumed_from_start(self) -> None:
        w = self.window
        w.set_document(Image.new("RGB", (100, 70), (75, 90, 120)))
        self.app.processEvents()
        self.assertIs(w.stage_stack.currentWidget(), w.photo_frame)
        self.assertTrue(w.nav_photo.isChecked())
        w._go_start()
        self.assertIs(w.stage_stack.currentWidget(), w.home_page)
        self.assertTrue(w.home_continue_button.isVisible())
        w.home_continue_button.click()
        self.assertIs(w.stage_stack.currentWidget(), w.photo_frame)

    def test_pending_preview_cannot_be_concealed_by_start_navigation(self) -> None:
        w = self.window
        w.set_document(Image.new("RGB", (100, 70), (75, 90, 120)))
        w.sliders["brightness"].setValue(125)
        self.assertTrue(w.has_pending_adjustments)
        self.assertFalse(w.more_tools_panel.isHidden())
        w.nav_start.click()
        self.assertIs(w.stage_stack.currentWidget(), w.photo_frame)
        self.assertTrue(w.nav_photo.isChecked())
        self.assertTrue(w.apply_button.isEnabled())
        self.assertFalse(w.more_tools_button.isEnabled())
        w.discard_adjustments()
        w.nav_start.click()
        self.assertIs(w.stage_stack.currentWidget(), w.home_page)

    def test_switching_languages_updates_navigation_and_advanced_toggle(self) -> None:
        w = self.window
        w.set_document(Image.new("RGB", (100, 70), (75, 90, 120)))
        w.set_language("en")
        self.assertIn("Photo", w.nav_photo.accessibleName())
        self.assertEqual(w.nav_photo.accessibleName(), "Photo")
        self.assertIn("Open separate window", w.nav_video.toolTip())
        self.assertEqual(w.quick_buttons[0].text(), "Enhance photo …")
        w.set_language("de")
        self.assertIn("Foto", w.nav_photo.accessibleName())
        self.assertIn("Weitere", w.more_tools_button.text())

    def test_media_navigation_starts_independent_tools(self) -> None:
        w = self.window
        with patch.object(w, "_launch_other_tool") as launch:
            w.nav_video.click()
            w.nav_audio.click()
            w.home_media_buttons[1].click()
            w.home_media_buttons[2].click()
        self.assertEqual([x.args[0] for x in launch.call_args_list],
                         ["video", "audio", "video", "audio"])

    def test_photo_navigation_opens_import_without_simulated_media_features(self) -> None:
        w = self.window
        with patch.object(w, "open_photo") as choose:
            w._go_photo()
            choose.assert_called_once()
        self.assertIs(w.stage_stack.currentWidget(), w.home_page)

    def test_unsaved_edits_are_visible_and_home_does_not_discard_them(self) -> None:
        w = self.window
        w.set_document(Image.new("RGB", (100, 70), (75, 90, 120)))
        w.rotate_clockwise()
        self.assertIn("Änderungen", w.save_state_label.text())
        history_size = len(w.document.history)
        w._go_start()
        self.assertEqual(len(w.document.history), history_size)
        w._go_photo()
        self.assertEqual(len(w.document.history), history_size)


if __name__ == "__main__":
    unittest.main()
