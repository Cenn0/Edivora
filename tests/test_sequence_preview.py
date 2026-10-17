"""Bounded, real FFmpeg whole-sequence preview and temporary-file teardown."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import os
import subprocess
import tempfile
import time
import unittest

from local_ai_photo_editor.core.media_project import MediaClip, MediaSequence
from local_ai_photo_editor.core.sequence_time import SequenceTimebase

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "Qt UI requires PySide6")
class SequencePreviewQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import imageio_ffmpeg
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from local_ai_photo_editor.ui.sequence_preview import SequencePreviewDialog

        cls.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cls.app = QApplication.instance() or QApplication([])
        cls.QTest = QTest
        cls.dialog_type = SequencePreviewDialog

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def _clip(self, name, frequency):
        path = self.root / name
        done = subprocess.run([
            self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000",
            "-t", "0.7", "-c:a", "pcm_s16le", "-y", str(path),
        ], capture_output=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr[-400:])
        return MediaClip.create("audio", path, 700, start_ms=100, end_ms=600)

    def test_render_two_clips_playable_source_and_cleanup(self):
        clips = (self._clip("one.wav", 330), self._clip("two.wav", 710))
        sequence = MediaSequence("audio", clips)
        self.assertEqual(SequenceTimebase(sequence).total_ms, 1000)
        dlg = self.dialog_type(sequence, engine=self.ffmpeg, language="en")
        folder = Path(dlg._folder.name)
        dlg.show()
        try:
            deadline = time.monotonic() + 35
            while not dlg.preview_ready and dlg._process is not None and time.monotonic() < deadline:
                self.QTest.qWait(60)
            # Account for deferred QTimer.singleShot process start.
            while not dlg.preview_ready and time.monotonic() < deadline:
                self.QTest.qWait(60)
                if dlg._process is None and dlg._failure is not None:
                    break
            self.assertTrue(dlg.preview_ready, dlg.message.text())
            self.assertTrue(dlg._destination.is_file())
            self.assertGreater(dlg._destination.stat().st_size, 1000)
            self.assertTrue(dlg.play_button.isEnabled())
            self.assertTrue(dlg.seek.isEnabled())
        finally:
            dlg.close()
            dlg.deleteLater()
            self.app.processEvents()
        deadline = time.monotonic() + 10
        while folder.exists() and time.monotonic() < deadline:
            self.QTest.qWait(100)
        self.assertFalse(folder.exists(), "Preview cleanup retained a media decoder handle.")
        self.assertTrue(clips[0].source.exists())
        self.assertTrue(clips[1].source.exists())

    def test_rejects_oversized_preview_without_writing_output(self):
        from local_ai_photo_editor.ui.sequence_preview import preview_allowed, MAX_PREVIEW_MS
        clip = self._clip("short.wav", 400)
        too_long = MediaClip.create("audio", clip.source, MAX_PREVIEW_MS + 5000)
        sequence = MediaSequence("audio", (too_long,))
        self.assertFalse(preview_allowed(sequence))
        with self.assertRaisesRegex(ValueError, "two minutes"):
            self.dialog_type(sequence, engine=self.ffmpeg)

    def test_closed_before_render_starts_cannot_leave_temp_media(self):
        clip = self._clip("short.wav", 400)
        dlg = self.dialog_type(MediaSequence("audio", (clip,)), engine=self.ffmpeg)
        root = Path(dlg._folder.name)
        dlg.close()
        deadline = time.monotonic() + 10
        while root.exists() and time.monotonic() < deadline:
            self.QTest.qWait(100)
        self.assertFalse(root.exists())
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
