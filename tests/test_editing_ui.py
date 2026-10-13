"""Guided workspace lifecycle and integration, using real Qt when installed."""
from __future__ import annotations

from dataclasses import replace
import importlib.util
import os
import string
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image

from local_ai_photo_editor.core.recipes import EditRecipe, RenderCancelled
from local_ai_photo_editor.ui.editing_strings import STRINGS

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class EditingTranslationTests(unittest.TestCase):
    def test_keys_placeholders_and_nonempty_labels_match(self):
        self.assertEqual(STRINGS["de"].keys(), STRINGS["en"].keys())
        formatter = string.Formatter()
        for key in STRINGS["de"]:
            with self.subTest(key=key):
                placeholders = lambda text: {name for _, name, _, _ in formatter.parse(text) if name}
                self.assertEqual(placeholders(STRINGS["de"][key]), placeholders(STRINGS["en"][key]))
                self.assertTrue(STRINGS["de"][key].strip())
                self.assertTrue(STRINGS["en"][key].strip())


@unittest.skipUnless(QT_AVAILABLE, "PySide6 unavailable; real GUI tests run in CI.")
class EditingUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui import EditorWindow
        from local_ai_photo_editor.ui.editing_dialog import EditingDialog
        cls.app = QApplication.instance() or QApplication([])
        cls.window_type, cls.dialog_type, cls.qtest = EditorWindow, EditingDialog, QTest

    def setUp(self):
        self.window = self.window_type()
        self.dialogs = []
        self.image = Image.new("RGBA", (1200, 800), (70, 100, 150, 128))
        self.window.set_document(self.image)

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.reject()
            self.wait_until(lambda d=dialog: not d.is_rendering)
            dialog.deleteLater()
        self.window._editing_dialog = None
        self.window._close_approved = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def wait_until(self, predicate):
        deadline = time.monotonic() + 10
        while not predicate() and time.monotonic() < deadline:
            self.qtest.qWait(10)
        self.assertTrue(predicate(), "Qt worker or modal lifecycle timed out")

    def dialog(self, section="light", image=None):
        dialog = self.dialog_type(image if image is not None else self.image, "de", section, self.window)
        self.dialogs.append(dialog)
        return dialog

    def test_public_entry_point_and_old_translation_keys_are_preserved(self):
        self.assertTrue(all(b.isEnabled() for b in self.window.editing_buttons))
        self.assertIn("Vorschau", self.window._t("preview"))
        self.window.set_language("en")
        self.assertEqual(self.window.editing_buttons[0].text(), "Light & colors …")
        self.window.sliders["brightness"].setValue(120)
        self.assertFalse(self.window.editing_action.isEnabled())
        self.window.discard_adjustments()
        self.window.crop_button.click()
        self.assertFalse(self.window.editing_action.isEnabled())
        self.window.crop_button.click()
        self.window.original_button.click()
        self.assertFalse(self.window.editing_action.isEnabled())

    def test_preview_does_not_mutate_document_and_cancel_discards_it(self):
        dialog = self.dialog()
        original = self.window.document.current.tobytes()
        dialog.controls["exposure"].setValue(30)
        dialog._render_preview()
        self.assertEqual(self.window.document.current.tobytes(), original)
        self.assertNotEqual(dialog._preview_result.tobytes(), dialog._preview_source.tobytes())
        dialog.reject()
        self.assertIsNone(dialog.result_image)
        self.assertFalse(dialog._timer.isActive())
        self.assertEqual(len(self.window.document.history), 0)

    def test_apply_computes_latest_recipe_at_full_size_not_cached_thumbnail(self):
        dialog = self.dialog()
        dialog.controls["exposure"].setValue(20)
        dialog._render_preview()
        dialog.controls["exposure"].setValue(50)
        dialog.accept()
        self.wait_until(lambda: not dialog.is_rendering)
        self.assertIsNotNone(dialog.result_image)
        self.assertEqual(dialog.result_image.size, self.image.size)
        self.assertGreater(dialog.result_image.getpixel((0, 0))[0], dialog._preview_result.getpixel((0, 0))[0])
        self.assertEqual(dialog.result_image.getchannel("A").tobytes(), self.image.getchannel("A").tobytes())

    def test_neutral_recipe_cannot_add_an_empty_commit(self):
        dialog = self.dialog()
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.accept()
        self.assertFalse(dialog.is_rendering)
        self.assertIsNone(dialog.result_image)

    def test_before_compare_and_resets_do_not_accumulate_changes(self):
        dialog = self.dialog("look")
        dialog.set_recipe(EditRecipe(exposure=20, look="mono", vignette=25))
        dialog._render_preview()
        dialog.compare_button.click()
        self.assertEqual(dialog.status.text(), STRINGS["de"]["before_status"])
        dialog.reset_section()
        self.assertEqual(dialog.recipe, EditRecipe(exposure=20))
        dialog.reset_all()
        self.assertEqual(dialog.recipe, EditRecipe())

    def test_suggestion_changes_only_its_documented_controls(self):
        dialog = self.dialog()
        dialog.set_recipe(EditRecipe(warmth=30, look="warm", mirror=True))
        before = dialog.recipe
        dialog.suggest_improvement()
        self.assertEqual(dialog.recipe, replace(before, automatic=60, shadows=15, highlights=10))

    def test_background_requires_transparency_and_a_selected_photo(self):
        opaque = self.dialog("background", Image.new("RGB", (50, 50), "red"))
        self.assertFalse(opaque.combos["background"].isEnabled())
        dialog = self.dialog("background")
        dialog.set_recipe(EditRecipe(background="photo"))
        dialog._render_preview()
        self.assertFalse(dialog.apply_button.isEnabled())
        dialog.set_background_image(Image.new("RGB", (80, 60), "blue"))
        dialog._render_preview()
        self.assertTrue(dialog.apply_button.isEnabled())

    def test_successful_modal_result_is_one_undo_redo_step(self):
        def apply(dialog):
            dialog.set_recipe(EditRecipe(look="mono", aspect="square"))
            dialog.accept()
            self.wait_until(lambda: not dialog.is_rendering)
            return dialog.result()
        original = self.window.document.current.tobytes()
        with patch.object(self.dialog_type, "exec", apply):
            self.window.show_editing_tools("look")
        self.assertEqual(len(self.window.document.history), 1)
        self.assertEqual(self.window.document.current.size, (800, 800))
        edited = self.window.document.current.tobytes()
        self.window.undo()
        self.assertEqual(self.window.document.current.tobytes(), original)
        self.window.redo()
        self.assertEqual(self.window.document.current.tobytes(), edited)
        self.assertEqual(self.window.document.original.tobytes(), original)

    def test_cancelled_modal_session_does_not_create_history(self):
        def cancel(dialog):
            dialog.set_recipe(EditRecipe(exposure=50))
            dialog.reject()
            return dialog.result()
        with patch.object(self.dialog_type, "exec", cancel):
            self.window.show_editing_tools()
        self.assertEqual(len(self.window.document.history), 0)

    def test_stale_dialog_result_cannot_overwrite_another_document(self):
        replacement = Image.new("RGB", (17, 13), "green")
        def replace_document(dialog):
            dialog.result_image = Image.new("RGB", (20, 20), "red")
            self.window.set_document(replacement)
            return 1
        with patch.object(self.dialog_type, "exec", replace_document):
            self.window.show_editing_tools()
        self.assertEqual(self.window.document.current.tobytes(), replacement.tobytes())
        self.assertEqual(len(self.window.document.history), 0)

    def test_cancel_during_full_render_waits_for_thread_and_discards_result(self):
        dialog = self.dialog()
        dialog.set_recipe(EditRecipe(exposure=30))
        started = threading.Event()
        def slow_render(*args, **kwargs):
            started.set()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if kwargs["cancelled"]():
                    raise RenderCancelled()
                time.sleep(.005)
            raise RuntimeError("Cancellation was not delivered")
        with patch("local_ai_photo_editor.ui.editing_dialog.render_recipe", side_effect=slow_render):
            dialog.accept()
            self.wait_until(started.is_set)
            dialog.reject()
            self.assertTrue(dialog.is_rendering)
            self.wait_until(lambda: not dialog.is_rendering)
        self.assertIsNone(dialog.result_image)
        self.assertEqual(dialog.result(), 0)

    def test_render_failure_keeps_dialog_and_document_recoverable(self):
        dialog = self.dialog()
        dialog.set_recipe(EditRecipe(exposure=30))
        with patch("local_ai_photo_editor.ui.editing_dialog.render_recipe", side_effect=MemoryError("test")), \
                patch.object(dialog, "_show_error") as error:
            dialog.accept()
            self.wait_until(lambda: not dialog.is_rendering)
            error.assert_called_once()
        self.assertIsNone(dialog.result_image)
        self.assertTrue(dialog.tabs.isEnabled())
        self.assertTrue(dialog.apply_button.isEnabled())
        self.assertEqual(len(self.window.document.history), 0)

    def test_no_false_ai_busy_indicator_for_conventional_tools(self):
        dialog = self.dialog()
        self.window._editing_dialog = dialog
        self.window._update_state()
        self.assertFalse(self.window.is_busy)
        self.assertFalse(self.window._editable())
        self.assertFalse(self.window.editing_action.isEnabled())
        self.window._editing_dialog = None


if __name__ == "__main__":
    unittest.main()
