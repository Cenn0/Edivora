"""GUI behaviour and subprocess protocol tests; these do not validate an AI model."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import string
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image

from local_ai_photo_editor.ui.strings import STRINGS

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class TranslationTests(unittest.TestCase):
    def test_languages_have_matching_keys_and_placeholders(self) -> None:
        self.assertEqual(STRINGS["de"].keys(), STRINGS["en"].keys())
        formatter = string.Formatter()
        for key in STRINGS["de"]:
            with self.subTest(key=key):
                self.assertTrue(STRINGS["de"][key].strip())
                self.assertTrue(STRINGS["en"][key].strip())
                placeholders = lambda text: {field for _, field, _, _ in formatter.parse(text) if field}
                self.assertEqual(placeholders(STRINGS["de"][key]), placeholders(STRINGS["en"][key]))


@unittest.skipUnless(QT_AVAILABLE, "PySide6 is unavailable; GUI behaviour needs the Windows/Qt CI run.")
class EditorWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui import EditorWindow

        cls.app = QApplication.instance() or QApplication([])
        cls.window_type = EditorWindow
        cls.qt = Qt
        cls.qtest = QTest

    def setUp(self) -> None:
        self.window = self.window_type()
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        if self.window.is_busy:
            self.window.cancel_background_removal()
            self._wait_until(lambda: not self.window.is_busy)
        self.window._close_approved = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def _wait_until(self, predicate, timeout: float = 8) -> None:
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.qtest.qWait(10)
        self.assertTrue(predicate(), "Timed out waiting for a Qt lifecycle event.")

    def test_initial_controls_and_language_switch(self) -> None:
        self.assertTrue(self.window.open_button.isEnabled())
        self.assertFalse(self.window.ai_button.isEnabled())
        self.assertFalse(self.window.export_button.isEnabled())
        self.assertEqual(self.window.open_button.text(), "Foto öffnen")
        self.window.set_language("en")
        self.assertEqual(self.window.open_button.text(), "Open photo")
        self.assertEqual(self.window.language_combo.currentData(), "en")

    def test_adjustment_preview_is_committed_explicitly_and_undoable(self) -> None:
        picture = Image.new("RGBA", (30, 20), (40, 80, 120, 128))
        self.window.set_document(picture)
        self.window.sliders["brightness"].setValue(150)
        self.app.processEvents()
        self.assertEqual(self.window.document.current.tobytes(), picture.tobytes())
        self.assertTrue(self.window.apply_button.isEnabled())
        self.assertFalse(self.window.export_button.isEnabled())
        self.assertFalse(self.window.ai_button.isEnabled())
        self.window.apply_adjustments()
        self.assertEqual(self.window.document.current.getpixel((0, 0)), (60, 120, 180, 128))
        self.assertFalse(self.window.has_pending_adjustments)
        self.window.undo()
        self.assertEqual(self.window.document.current.tobytes(), picture.tobytes())
        self.window.redo()
        self.assertEqual(len(self.window.document.history), 1)

    def test_rotation_does_not_mutate_original_and_comparison_disables_edits(self) -> None:
        self.window.set_document(Image.new("RGB", (24, 16), "red"))
        self.window.rotate_clockwise()
        self.assertEqual(self.window.document.current.size, (16, 24))
        self.assertEqual(self.window.document.original.size, (24, 16))
        self.window.original_button.click()
        self.assertFalse(self.window.rotate_button.isEnabled())
        self.assertFalse(self.window.ai_button.isEnabled())
        self.window.original_button.click()
        self.assertTrue(self.window.rotate_button.isEnabled())

    def test_crop_selection_maps_fitted_preview_to_photo_pixels(self) -> None:
        self.window.set_document(Image.new("RGB", (400, 200), "blue"))
        self.window.crop_button.click()
        self.app.processEvents()
        canvas = self.window.canvas
        rect = canvas.image_rect
        start = rect.topLeft() + type(rect.topLeft())(rect.width() * 0.25, rect.height() * 0.25)
        end = rect.topLeft() + type(rect.topLeft())(rect.width() * 0.75, rect.height() * 0.75)
        self.qtest.mousePress(canvas, self.qt.MouseButton.LeftButton, pos=start.toPoint())
        self.qtest.mouseMove(canvas, end.toPoint())
        self.qtest.mouseRelease(canvas, self.qt.MouseButton.LeftButton, pos=end.toPoint())
        box = canvas.crop_box
        self.assertIsNotNone(box)
        self.assertAlmostEqual(box[2] - box[0], 200, delta=3)
        self.assertAlmostEqual(box[3] - box[1], 100, delta=3)
        self.assertTrue(self.window.crop_apply_button.isEnabled())
        self.window.apply_crop()
        self.assertEqual(self.window.document.current.size, (box[2] - box[0], box[3] - box[1]))
        self.assertFalse(self.window.crop_button.isChecked())

    def test_export_refuses_the_imported_source_before_replacement_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.png"
            Image.new("RGB", (8, 8), "orange").save(source)
            before = source.read_bytes()
            self.window.open_path(source)
            with patch("local_ai_photo_editor.ui.window.QFileDialog.getSaveFileName", return_value=(str(source), "PNG (*.png)")), patch.object(self.window, "_show_error") as error, patch.object(self.window, "_confirm") as confirm:
                self.window.export_copy()
            error.assert_called_once_with("source_protected")
            confirm.assert_not_called()
            self.assertEqual(source.read_bytes(), before)

    def test_completed_job_applies_output_and_cleans_tempfiles_protocol_only(self) -> None:
        # This fixture copies pixels. It tests process/files/lifecycle, never AI quality.
        script = (
            "import json,pathlib,shutil,sys; "
            "p=pathlib.Path(sys.argv[1]); "
            "shutil.copyfile(p/'input.png',p/'output.png'); "
            "(p/'result.json').write_text(json.dumps({'status':'ok'}),encoding='utf-8')"
        )
        self.window.set_document(Image.new("RGBA", (32, 24), (80, 100, 120, 120)))
        with patch("local_ai_photo_editor.__main__.worker_command", side_effect=lambda directory: (sys.executable, ["-c", script, str(directory)])):
            self.window.start_background_removal()
        directory = self.window._job_directory
        self.assertIsNotNone(directory)
        self.assertFalse(self.window.export_button.isEnabled())
        self._wait_until(lambda: not self.window.is_busy)
        self.assertFalse(directory.exists())
        self.assertEqual(len(self.window.document.history), 1)
        self.assertEqual(self.window.document.current.getpixel((0, 0)), (80, 100, 120, 120))
        self.assertTrue(self.window.export_button.isEnabled())

    def test_cancellation_stops_process_before_removing_job_directory(self) -> None:
        self.window.set_document(Image.new("RGB", (16, 16), "green"))
        with patch("local_ai_photo_editor.__main__.worker_command", side_effect=lambda directory: (sys.executable, ["-c", "import time; time.sleep(30)"])):
            self.window.start_background_removal()
        directory = self.window._job_directory
        self.assertTrue(directory.exists())
        self.window.cancel_background_removal()
        self._wait_until(lambda: not self.window.is_busy)
        self.assertFalse(directory.exists())
        self.assertEqual(self.window.document.history, ())
        self.assertTrue(self.window.ai_button.isEnabled())

    def test_failed_worker_recovers_controls_and_reports_missing_model(self) -> None:
        script = (
            "import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); "
            "(p/'result.json').write_text(json.dumps({'status':'error','code':'MODEL_MISSING'}),encoding='utf-8'); "
            "sys.exit(1)"
        )
        self.window.set_document(Image.new("RGB", (16, 16), "green"))
        with patch("local_ai_photo_editor.__main__.worker_command", side_effect=lambda directory: (sys.executable, ["-c", script, str(directory)])), patch.object(self.window, "_show_error") as error:
            self.window.start_background_removal()
            directory = self.window._job_directory
            self._wait_until(lambda: not self.window.is_busy)
        error.assert_called_once_with("model_missing")
        self.assertFalse(directory.exists())
        self.assertEqual(self.window.document.history, ())
        self.assertTrue(self.window.ai_button.isEnabled())

    def test_save_open_project_restores_undo_redo_and_clean_state(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "editing.laip"
            source = Image.new("RGBA", (24, 16), (40, 100, 150, 99))
            self.window.set_document(source)
            self.window.rotate_clockwise()
            self.window.rotate_clockwise()
            self.window.undo()
            self.assertTrue(self.window._has_unexported_changes())
            with patch("local_ai_photo_editor.ui.window.QFileDialog.getSaveFileName", return_value=(str(path), "")):
                self.window.save_project_as()
            self.assertTrue(path.exists())
            self.assertFalse(self.window._has_unexported_changes())
            self.assertTrue(self.window.document.can_redo)
            self.assertEqual(self.window.file_label.text(), "editing.laip")
            self.window.rotate_clockwise()
            self.assertTrue(self.window._has_unexported_changes())
            with patch.object(self.window, "_confirm", return_value=True):
                self.window.open_project_path(path)
            self.assertFalse(self.window._has_unexported_changes())
            self.assertEqual(self.window.document.original.size, (24, 16))
            self.assertEqual(self.window.document.current.size, (16, 24))
            self.assertTrue(self.window.document.can_redo)
            self.window.redo()
            self.assertEqual(self.window.document.current.size, (24, 16))
            self.assertTrue(self.window._has_unexported_changes())
            self.window.save_project()
            self.assertFalse(self.window._has_unexported_changes())

    def test_reopened_project_never_overwrites_existing_image(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source_path = Path(folder) / "original.png"
            project_path = Path(folder) / "safe.laip"
            Image.new("RGB", (8, 6), "red").save(source_path)
            original_bytes = source_path.read_bytes()
            self.window.open_path(source_path)
            from local_ai_photo_editor.core import save_project
            save_project(self.window.document, project_path)
            self.window.open_project_path(project_path)
            self.assertIsNone(self.window.document.source_path)
            with (
                patch("local_ai_photo_editor.ui.window.QFileDialog.getSaveFileName", return_value=(str(source_path), "PNG (*.png)")),
                patch.object(self.window, "_confirm") as confirm,
                patch.object(self.window, "_show_error") as error,
            ):
                self.window.export_copy()
            error.assert_called_once_with("project_export_existing")
            confirm.assert_not_called()
            self.assertEqual(source_path.read_bytes(), original_bytes)
            fresh = Path(folder) / "fresh.png"
            with patch("local_ai_photo_editor.ui.window.QFileDialog.getSaveFileName", return_value=(str(fresh), "PNG (*.png)")):
                self.window.export_copy()
            self.assertTrue(fresh.exists())
            self.assertEqual(self.window.status_label.text(), self.window._t("export_done", name=fresh.name))

    def test_invalid_project_does_not_replace_active_document(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "broken.laip"
            broken.write_text("not an archive", encoding="utf-8")
            self.window.set_document(Image.new("RGB", (12, 8), "green"))
            self.window.rotate_clockwise()
            document_before = self.window.document
            revision_before = self.window._revision
            with patch.object(self.window, "_confirm", return_value=True), patch.object(self.window, "_show_error") as error:
                self.window.open_project_path(broken)
            error.assert_called_once_with("project_error", unittest.mock.ANY)
            self.assertIs(self.window.document, document_before)
            self.assertEqual(self.window._revision, revision_before)
            self.assertTrue(self.window._has_unexported_changes())


if __name__ == "__main__":
    unittest.main()
