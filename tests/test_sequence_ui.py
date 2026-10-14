"""Beginner multi-clip editor: add, arrange, split, save/reopen, and export parameters."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "Qt UI requires PySide6.")
class SequencerQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import imageio_ffmpeg
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from local_ai_photo_editor.ui.sequence_window import SequenceWindow

        cls.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cls.app = QApplication.instance() or QApplication([])
        cls.QTest = QTest
        cls.window_type = SequenceWindow

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make_audio(self, name: str, frequency: int) -> Path:
        dest = self.root / name
        done = subprocess.run([
            self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000",
            "-t", "1.5", "-c:a", "pcm_s16le", "-y", str(dest)
        ], capture_output=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr[-600:])
        return dest

    def wait_for(self, predicate, max_time=12) -> None:
        deadline = time.monotonic() + max_time
        while not predicate() and time.monotonic() < deadline:
            self.QTest.qWait(50)
        self.assertTrue(predicate(), "Qt media metadata did not arrive.")

    def test_add_two_clips_reorder_save_reopen_and_export_plan(self) -> None:
        a = self.make_audio("a.wav", 250)
        b = self.make_audio("b.wav", 700)
        w = self.window_type("audio")
        w.show()
        self.app.processEvents()
        try:
            self.assertEqual(len(w.clips), 0)
            w.open_path(a)
            self.wait_for(lambda: len(w.clips) == 1 and w.duration_ms > 0)
            self.assertEqual(w.clip_list.count(), 1)
            w.start_spin.setValue(0.100)
            self.assertEqual(w.clips[0].start_ms, 100)
            w.open_path(b)
            self.wait_for(lambda: len(w.clips) == 2 and w.active_id == w.clips[1].id)
            self.assertEqual(w.clip_list.count(), 2)
            previous_order = [clip.source.name for clip in w.clips]
            w.move_selected(-1)
            self.assertEqual([clip.source.name for clip in w.clips], previous_order[::-1])
            plan = w._sequence_export(self.root / "result.wav")
            self.assertEqual(len(plan.sequence.clips), 2)
            self.assertEqual(plan.sequence.clips[1].start_ms, 100)
            project = self.root / "edit.edap"
            w._save_to(project)
            self.assertTrue(project.is_file())
            self.assertFalse(w._dirty)
            w.remove_selected()
            self.assertEqual(len(w.clips), 1)
            # QFileDialog is bypassed; the same exact validation controls
            # opening through the UI.
            from local_ai_photo_editor.core.media_project import load_media_project
            reopened = load_media_project(project)
            self.assertEqual(len(reopened.clips), 2)
            self.assertEqual([x.source.name for x in reopened.clips], ["b.wav", "a.wav"])
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)  # allow Windows multimedia decoder threads to release file handles

    def test_clip_split_duplicate_and_selected_trim_are_independent(self) -> None:
        a = self.make_audio("a.wav", 450)
        w = self.window_type("audio")
        w.show()
        self.app.processEvents()
        try:
            w.open_path(a)
            self.wait_for(lambda: len(w.clips) == 1 and w.duration_ms > 0)
            w.player.setPosition(650)
            self.wait_for(lambda: abs(w.player.position() - 650) <= 150)
            w.split_selected()
            self.assertEqual(len(w.clips), 2)
            self.assertEqual(w.clips[0].end_ms, w.clips[1].start_ms)
            first_id = w.clips[0].id
            w.duplicate_selected()
            self.assertEqual(len(w.clips), 3)
            self.assertNotEqual(w.clips[1].id, w.clips[2].id)
            self.assertEqual(w.clips[0].id, first_id)
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)  # allow Windows multimedia decoder threads to release file handles

    def test_ai_is_explicitly_disabled_without_bundled_model(self) -> None:
        from unittest.mock import patch

        w = self.window_type("audio")
        w.show()
        self.app.processEvents()
        try:
            with patch("local_ai_photo_editor.ui.sequence_window.voice_model_available", return_value=False):
                a = self.make_audio("audio.wav", 440)
                w.open_path(a)
                self.wait_for(lambda: len(w.clips) == 1 and w.duration_ms > 0)
                w._update_enabled()
                self.assertFalse(w.ai_button.isEnabled())
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)  # allow Windows multimedia decoder threads to release file handles
