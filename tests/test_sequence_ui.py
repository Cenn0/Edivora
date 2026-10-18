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

    def test_video_and_audio_show_embedded_brand_mark(self) -> None:
        from PySide6.QtWidgets import QLabel
        for kind in ("video", "audio"):
            with self.subTest(kind=kind):
                w = self.window_type(kind)
                try:
                    labels = w.findChildren(QLabel, "brandMark")
                    self.assertEqual(len(labels), 1)
                    self.assertEqual(labels[0].accessibleName(), "Edivora")
                    self.assertFalse(labels[0].pixmap().isNull())
                finally:
                    w._dirty = False
                    w.close()
                    w.deleteLater()
                    self.app.processEvents()

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

    def test_open_missing_media_relinks_and_requires_resave(self) -> None:
        from unittest.mock import patch
        from local_ai_photo_editor.core.media_project import (
            MediaClip, MediaSequence, load_media_project, save_media_project,
        )

        original = self.make_audio("to-move.wav", 430)
        clip = MediaClip.create("audio", original, 1500)
        project = self.root / "moved.edap"
        save_media_project(MediaSequence("audio", (clip,)), project)
        moved = self.root / "moved-audio.wav"
        original.rename(moved)

        w = self.window_type("audio")
        w.show()
        self.app.processEvents()
        try:
            # A cancelled file chooser must not mutate the active editor.
            with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getOpenFileName",
                       return_value=("", "")):
                self.assertIsNone(w._load_with_relinks(project))
            self.assertFalse(w.clips)

            with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getOpenFileName",
                       return_value=(str(moved), "")):
                outcome = w._load_with_relinks(project)
            self.assertIsNotNone(outcome)
            sequence, relinked = outcome
            self.assertTrue(relinked)
            self.assertEqual(sequence.clips[0].source, moved.resolve())

            # Use the same UI path as the toolbar and check unsaved state.
            with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getOpenFileName",
                       side_effect=[(str(project), ""), (str(moved), "")]):
                w.open_media_project()
            self.wait_for(lambda: w.duration_ms > 0 and len(w.clips) == 1)
            self.assertTrue(w._dirty)
            self.assertTrue(w._relink_unsaved)
            self.assertTrue(w._save_to(project))
            self.assertFalse(w._dirty)
            self.assertFalse(w._relink_unsaved)
            self.assertEqual(load_media_project(project).clips[0].source, moved.resolve())
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)

    def test_portable_export_button_copies_without_changing_open_project(self) -> None:
        from unittest.mock import patch
        from local_ai_photo_editor.core.media_project import load_media_project

        source = self.make_audio("portable.wav", 435)
        project = self.root / "saved.edap"
        w = self.window_type("audio")
        w.show()
        self.app.processEvents()
        try:
            w.open_path(source)
            self.wait_for(lambda: len(w.clips) == 1 and w.duration_ms > 0)
            self.assertTrue(w._save_to(project))
            original_project = project.read_bytes()
            original_audio = source.read_bytes()
            with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getExistingDirectory",
                       return_value=str(self.root)):
                w.export_portable_project()
            self.wait_for(lambda: w._portable_worker is None, max_time=30)
            manifest = self.root / "saved-portable" / "project.edap"
            self.assertTrue(manifest.exists())
            portable = load_media_project(manifest)
            self.assertEqual(portable.clips[0].source.read_bytes(), original_audio)
            self.assertEqual(w._project_file, project)
            self.assertFalse(w._dirty)
            self.assertEqual(source.read_bytes(), original_audio)
            self.assertEqual(project.read_bytes(), original_project)
        finally:
            # Ensure a worker can never outlive its QWidget during test cleanup.
            if w._portable_worker is not None:
                w._portable_worker.requestInterruption()
                w._portable_worker.wait(10_000)
                self.app.processEvents()
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)

    def test_autosave_recovery_requires_consent_and_explicit_save(self) -> None:
        from unittest.mock import patch
        from local_ai_photo_editor.core.media_recovery import (
            candidate_recovery, write_recovery
        )
        from local_ai_photo_editor.core.media_project import load_media_project

        a = self.make_audio("recovery.wav", 400)
        project = self.root / "recovery.edap"
        first = self.window_type("audio")
        first.show()
        self.app.processEvents()
        second = None
        try:
            first.open_path(a)
            self.wait_for(lambda: len(first.clips) == 1 and first.duration_ms > 0)
            self.assertTrue(first._save_to(project))
            saved = project.read_bytes()
            first.start_spin.setValue(0.200)
            self.assertTrue(first._dirty)
            first._autosave_recovery()
            # Ensure a strictly newer checkpoint regardless of NTFS granularity.
            checkpoint = write_recovery(first._snapshot(), project)
            newer = project.stat().st_mtime_ns + 3_000_000_000
            os.utime(checkpoint, ns=(newer, newer))
            self.assertIsNotNone(candidate_recovery(project))
            self.assertEqual(project.read_bytes(), saved)

            second = self.window_type("audio")
            second.show()
            self.app.processEvents()
            with patch("local_ai_photo_editor.ui.sequence_window.QFileDialog.getOpenFileName",
                       return_value=(str(project), "")), patch(
                       "local_ai_photo_editor.ui.sequence_window.QMessageBox.question",
                       return_value=__import__("PySide6.QtWidgets",
                                               fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes):
                second.open_media_project()
            self.wait_for(lambda: len(second.clips) == 1 and second.duration_ms > 0)
            self.assertTrue(second._dirty)
            self.assertTrue(second._recovery_pending)
            self.assertEqual(second.clips[0].start_ms, 200)
            self.assertEqual(project.read_bytes(), saved)
            self.assertTrue(second._save_to(project))
            self.assertFalse(second._dirty)
            self.assertFalse(second._recovery_pending)
            self.assertFalse(checkpoint.exists())
            self.assertEqual(load_media_project(project).clips[0].start_ms, 200)
        finally:
            first._dirty = False
            first.close()
            first.deleteLater()
            if second is not None:
                second._dirty = False
                second.close()
                second.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)

    def test_failed_automatic_checkpoint_preserves_saved_project(self) -> None:
        from unittest.mock import patch

        a = self.make_audio("full.wav", 370)
        project = self.root / "full.edap"
        w = self.window_type("audio")
        w.show()
        self.app.processEvents()
        try:
            w.open_path(a)
            self.wait_for(lambda: len(w.clips) == 1 and w.duration_ms > 0)
            self.assertTrue(w._save_to(project))
            before = project.read_bytes()
            w.start_spin.setValue(0.150)
            with patch("local_ai_photo_editor.ui.sequence_window.write_recovery",
                       side_effect=OSError("disk full")):
                w._autosave_recovery()
            self.assertTrue(w._dirty)
            self.assertEqual(project.read_bytes(), before)
        finally:
            w._dirty = False
            w.close()
            w.deleteLater()
            self.app.processEvents()
            self.QTest.qWait(150)

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
