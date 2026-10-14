"""Real subprocess-backed preview, explicit acceptance, cancellation and media undo."""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from local_ai_photo_editor.ai.restoration import model_available
from local_ai_photo_editor.core.media_project import MediaClip
from local_ai_photo_editor.core.video_adjustments import VideoAdjustments
from test_video_improvements import fixture


class VideoImprovementUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        cls.app = QApplication.instance() or QApplication([])
        cls.qt = QTest

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = fixture(self.root, seconds="3")
        self.clip = MediaClip.create("video", self.source, 3000)
        self.dialogs = []
        self.addCleanup(self.close_dialogs)

    def close_dialogs(self):
        for dialog in self.dialogs:
            dialog.reject()
            self.wait_for(lambda: not dialog.runner.busy)
            dialog.deleteLater()
        self.app.processEvents()

    def wait_for(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.qt.qWait(20)
        self.assertTrue(predicate(), "Video GUI operation timed out.")

    def dialog(self, language="de", **kwargs):
        from local_ai_photo_editor.ui.video_dialog import VideoEnhancementDialog
        dialog = VideoEnhancementDialog(kwargs.pop("clip", self.clip), 100, language, (self.source,))
        self.dialogs.append(dialog)
        dialog.show()
        self.wait_for(lambda: dialog.apply_button.isEnabled())
        return dialog

    def test_conventional_preview_is_explicit_and_original_is_unchanged(self):
        before = self.source.read_bytes()
        d = self.dialog()
        d.sliders["exposure"].setValue(25)
        self.assertFalse(d.apply_button.isEnabled())
        self.assertIsNone(d.result_clip)
        d.calculate_preview()
        self.wait_for(lambda: not d.runner.busy)
        self.assertTrue(d.apply_button.isEnabled())
        d.compare.setChecked(True)
        self.assertEqual(d._key()[0].exposure, 25)
        d.apply()
        self.assertEqual(d.result_clip.video_adjustments.exposure, 25)
        self.assertEqual(d.result_clip.source, self.source)
        self.assertEqual(self.source.read_bytes(), before)

    def test_missing_model_does_not_disable_conventional_tools(self):
        with patch("local_ai_photo_editor.ui.video_dialog.model_available", return_value=False):
            d = self.dialog("en")
        self.assertFalse(d.ai.isEnabled())
        self.assertTrue(d.preview_button.isEnabled())
        self.assertTrue(d.apply_button.isEnabled())
        self.assertIn("Apply", d.apply_button.accessibleName())

    def test_reject_before_initial_timer_never_starts_worker(self):
        from local_ai_photo_editor.ui.video_dialog import VideoEnhancementDialog
        d = VideoEnhancementDialog(self.clip, 100, "en", (self.source,))
        d.reject()
        self.qt.qWait(50)
        self.assertFalse(d.runner.busy)
        self.assertIsNone(d.runner.folder)
        d.deleteLater()

    @unittest.skipUnless(model_available(), "Verified DnCNN model required.")
    def test_real_ai_clip_creation_bakes_recipe_once_and_keeps_audio_settings(self):
        short = replace(self.clip, end_ms=400, volume_percent=70)
        d = self.dialog(clip=short)
        d.sliders["warmth"].setValue(-20)
        d.ai.setChecked(True)
        d.calculate_preview()
        self.wait_for(lambda: d.apply_button.isEnabled())
        output = self.root / "derived.mp4"
        with patch("local_ai_photo_editor.ui.video_dialog.QFileDialog.getSaveFileName", return_value=(str(output), "MP4")):
            d.apply()
        self.wait_for(lambda: not d.runner.busy, timeout=30)
        self.assertIsNotNone(d.result_clip)
        self.assertEqual(d.result_clip.source, output)
        self.assertEqual(d.result_clip.volume_percent, 70)
        self.assertEqual(d.result_clip.video_adjustments, VideoAdjustments())
        self.assertTrue(output.is_file())
        self.assertEqual(d.result_clip.end_ms, 400)

    @unittest.skipUnless(model_available(), "Verified DnCNN model required.")
    def test_cancel_active_neural_job_keeps_existing_destination(self):
        from PySide6.QtWidgets import QMessageBox
        d = self.dialog()
        d.ai.setChecked(True)
        d.calculate_preview()
        self.wait_for(lambda: d.apply_button.isEnabled())
        output = self.root / "existing.mp4"
        output.write_bytes(b"old file stays byte-for-byte")
        with patch("local_ai_photo_editor.ui.video_dialog.QFileDialog.getSaveFileName", return_value=(str(output), "MP4")), \
             patch("local_ai_photo_editor.ui.video_dialog.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            d.apply()
        self.wait_for(lambda: d.runner.busy and d.progress.value() > 0)
        d.cancel_button.click()
        self.wait_for(lambda: not d.runner.busy, timeout=15)
        self.assertEqual(output.read_bytes(), b"old file stays byte-for-byte")
        self.assertIsNone(d.result_clip)
        self.assertFalse(list(self.root.glob(".edivora-restoration-*")))

    def test_video_changes_undo_redo_and_mute_are_tracked(self):
        from local_ai_photo_editor.ui.sequence_window import SequenceWindow
        w = SequenceWindow("video")
        w.show()
        try:
            w.open_path(self.source)
            self.wait_for(lambda: len(w.clips) == 1 and not w._loading)
            w._save_to(self.root / "saved.edvp")
            w.clips[0] = replace(w.clips[0], video_adjustments=VideoAdjustments(exposure=15))
            w._mark_changed()
            self.assertTrue(w._dirty)
            w.undo_edit()
            self.wait_for(lambda: not w._loading)
            self.assertEqual(w.clips[0].video_adjustments, VideoAdjustments())
            self.assertFalse(w._dirty)
            w.redo_edit()
            self.wait_for(lambda: not w._loading)
            self.assertEqual(w.clips[0].video_adjustments.exposure, 15)
            w.mute.setChecked(True)
            self.assertTrue(w.clips[0].mute)
            w.duplicate_selected()
            self.wait_for(lambda: len(w.clips) == 2 and not w._loading)
            w.undo_edit()
            self.wait_for(lambda: len(w.clips) == 1 and not w._loading)
            self.assertEqual(w.video_size.currentData(), "hd")
            w.video_size.setCurrentIndex(1)
            self.assertEqual(w._sequence_export(self.root / "export.mp4").video_profile, "full_hd")
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()

    def test_undo_missing_source_preserves_current_state_and_history(self):
        from local_ai_photo_editor.ui.sequence_window import SequenceWindow
        w = SequenceWindow("video")
        w.show()
        try:
            w.open_path(self.source)
            self.wait_for(lambda: len(w.clips) == 1 and not w._loading)
            w.remove_selected()
            self.assertEqual(w.clips, [])
            cursor = w._history.cursor
            self.source.unlink()
            with patch("local_ai_photo_editor.ui.sequence_window.QMessageBox.warning") as warning:
                w.undo_edit()
            warning.assert_called_once()
            self.assertEqual(w.clips, [])
            self.assertFalse(w._loading)
            self.assertEqual(w._history.cursor, cursor)
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
