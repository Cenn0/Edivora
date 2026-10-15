"""Unsaved media-project choices must never silently discard data on save failure."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "Native Qt GUI tests require PySide6.")
class UnsavedMediaPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.ui.sequence_window import SequenceWindow

        cls.app = QApplication.instance() or QApplication([])
        cls.window_type = SequenceWindow

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.window = self.window_type("audio")
        # Only the dialog and save decision are under test. Source validation
        # is exercised separately by real media-project and sequencer tests.
        self.window.clips = [SimpleNamespace(source=self.path / "clip.wav")]
        self.window._dirty = True

    def tearDown(self) -> None:
        self.window._dirty = False
        self.window.clips = []
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def choose(self, answer):
        """Exercise the actual branching with a controlled, nonmodal dialog."""
        from PySide6.QtWidgets import QMessageBox as NativeMessageBox

        buttons = {}
        with patch("local_ai_photo_editor.ui.sequence_window.QMessageBox") as mock_type:
            mock_type.StandardButton = NativeMessageBox.StandardButton
            mock_type.Icon = NativeMessageBox.Icon
            dialog = mock_type.return_value
            dialog.exec.return_value = int(answer)
            dialog.button.side_effect = lambda which: buttons.setdefault(which, MagicMock())
            decision = self.window._confirm_unsaved()
        return decision, dialog, buttons

    def test_cancel_blocks_opening_and_keeps_dirty_project(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        with patch.object(self.window, "save_media_project") as save:
            allowed, _, _ = self.choose(QMessageBox.StandardButton.Cancel)
        self.assertFalse(allowed)
        self.assertTrue(self.window._dirty)
        save.assert_not_called()

        with patch.object(self.window, "_confirm_unsaved", return_value=False), \
             patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getOpenFileName") as picker:
            self.window.open_media_project()
            picker.assert_not_called()

    def test_discard_is_explicit_and_does_not_autosave(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        with patch.object(self.window, "save_media_project") as save:
            allowed, _, _ = self.choose(QMessageBox.StandardButton.Discard)
        self.assertTrue(allowed)
        self.assertTrue(self.window._dirty)
        save.assert_not_called()

    def test_save_existing_project_allows_continuation_only_after_success(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.window._project_file = self.path / "existing.edap"
        for result in (True, False):
            with self.subTest(save_succeeded=result), \
                 patch.object(self.window, "_save_to", return_value=result) as write:
                allowed, _, _ = self.choose(QMessageBox.StandardButton.Save)
                self.assertIs(allowed, result)
                write.assert_called_once_with(self.window._project_file)

    def test_save_as_cancel_does_not_abandon_current_project(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getSaveFileName",
                   return_value=("", "")):
            allowed, _, _ = self.choose(QMessageBox.StandardButton.Save)
        self.assertFalse(allowed)
        self.assertTrue(self.window._dirty)
        self.assertIsNone(self.window._project_file)

    def test_save_as_adds_expected_project_extension(self) -> None:
        selected = str(self.path / "my-video-or-audio-edit")
        with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getSaveFileName",
                   return_value=(selected, "")), \
             patch.object(self.window, "_save_to", return_value=True) as write:
            self.assertTrue(self.window.save_media_project_as())
        write.assert_called_once_with(Path(selected).with_suffix(".edap"))

    def test_failed_disk_write_keeps_unsaved_changes(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        previous = self.path / "previous.edap"
        self.window._project_file = previous
        target = self.path / "next.edap"
        with patch("local_ai_photo_editor.ui.sequence_window.save_media_project",
                   side_effect=OSError("no storage space")), \
             patch("local_ai_photo_editor.ui.sequence_window.QMessageBox.warning") as warning:
            self.assertFalse(self.window._save_to(target))
            warning.assert_called_once()
        self.assertTrue(self.window._dirty)
        self.assertEqual(self.window._project_file, previous)

    def test_successful_write_marks_session_saved(self) -> None:
        target = self.path / "saved.edap"
        with patch("local_ai_photo_editor.ui.sequence_window.save_media_project") as write:
            self.assertTrue(self.window._save_to(target))
            write.assert_called_once()
        self.assertFalse(self.window._dirty)
        self.assertEqual(self.window._project_file, target)

    def test_explicit_bilingual_actions_and_safe_default(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        for language, labels in (
            ("de", ("Projekt speichern", "Änderungen verwerfen", "Abbrechen")),
            ("en", ("Save project", "Discard changes", "Cancel")),
        ):
            with self.subTest(language=language):
                self.window.language = language
                decision, dialog, buttons = self.choose(QMessageBox.StandardButton.Cancel)
                self.assertFalse(decision)
                for action, caption in zip(
                    (QMessageBox.StandardButton.Save,
                     QMessageBox.StandardButton.Discard,
                     QMessageBox.StandardButton.Cancel), labels
                ):
                    buttons[action].setText.assert_called_once_with(caption)
                dialog.setEscapeButton.assert_called_once_with(QMessageBox.StandardButton.Cancel)
                dialog.setDefaultButton.assert_called_once_with(QMessageBox.StandardButton.Save)

    def test_no_clips_disables_save_and_defaults_to_cancel(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.window.clips = []
        decision, dialog, buttons = self.choose(QMessageBox.StandardButton.Cancel)
        self.assertFalse(decision)
        buttons[QMessageBox.StandardButton.Save].setEnabled.assert_called_once_with(False)
        dialog.setDefaultButton.assert_called_once_with(QMessageBox.StandardButton.Cancel)

    def test_clean_project_needs_no_dialog(self) -> None:
        self.window._dirty = False
        with patch("local_ai_photo_editor.ui.sequence_window.QMessageBox") as message:
            self.assertTrue(self.window._confirm_unsaved())
            message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
