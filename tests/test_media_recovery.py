"""Checkpoint round trips, corruption and original-project protection."""
from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from local_ai_photo_editor.core.media_project import (
    MediaClip, MediaSequence, load_media_project, save_media_project
)
from local_ai_photo_editor.core.media_recovery import (
    candidate_recovery, clear_recovery, write_recovery
)


class RecoveryCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "song.wav"
        self.source.write_bytes(b"fake-audio" * 140)
        self.clip = MediaClip.create("audio", self.source, 4000)
        self.base = MediaSequence("audio", (self.clip,))
        self.project = self.root / "session.edap"
        save_media_project(self.base, self.project)

    def changed(self):
        return MediaSequence("audio", (replace(self.clip, end_ms=2900),))

    def test_checkpoint_does_not_change_saved_project(self):
        original = self.project.read_bytes()
        with self.assertRaises(FileNotFoundError):
            write_recovery(self.changed(), self.root / "unsaved.edap")
        sidecar = write_recovery(self.changed(), self.project)
        self.assertNotEqual(sidecar, self.project)
        self.assertEqual(original, self.project.read_bytes())
        self.assertEqual(load_media_project(sidecar), self.changed())
        self.assertEqual(load_media_project(self.project), self.base)

    def test_checkpoint_found_only_when_newer_and_removed_after_save(self):
        sidecar = write_recovery(self.changed(), self.project)
        later = self.project.stat().st_mtime_ns + 3_000_000_000
        os.utime(sidecar, ns=(later, later))
        item = candidate_recovery(self.project)
        self.assertIsNotNone(item)
        self.assertEqual(item.checkpoint, sidecar)
        save_media_project(self.changed(), self.project)
        clear_recovery(self.project)
        self.assertFalse(sidecar.exists())
        self.assertIsNone(candidate_recovery(self.project))

    def test_older_sidecar_is_not_offered(self):
        sidecar = write_recovery(self.changed(), self.project)
        earlier = self.project.stat().st_mtime_ns - 3_000_000_000
        os.utime(sidecar, ns=(earlier, earlier))
        self.assertIsNone(candidate_recovery(self.project))

    def test_corrupted_new_checkpoint_keeps_original(self):
        before = self.project.read_bytes()
        sidecar = write_recovery(self.changed(), self.project)
        sidecar.write_text('{"invalid":"json"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            candidate_recovery(self.project)
        self.assertEqual(before, self.project.read_bytes())

    def test_unrelated_sidecar_name_cannot_be_overwritten_or_deleted(self):
        # A user file at the derived name must never be silently sacrificed.
        sidecar = write_recovery(self.changed(), self.project)
        foreign = b"NOT AN EDIVORA CHECKPOINT"
        sidecar.write_bytes(foreign)
        before = self.project.read_bytes()
        with self.assertRaisesRegex(ValueError, "move it aside manually"):
            write_recovery(self.changed(), self.project)
        with self.assertRaisesRegex(ValueError, "move it aside manually"):
            clear_recovery(self.project)
        self.assertEqual(sidecar.read_bytes(), foreign)
        self.assertEqual(self.project.read_bytes(), before)

    def test_existing_valid_checkpoint_can_be_replaced_and_cleared(self):
        sidecar = write_recovery(self.changed(), self.project)
        old_content = sidecar.read_bytes()
        newer = MediaSequence("audio", (replace(self.clip, end_ms=2800),))
        self.assertEqual(write_recovery(newer, self.project), sidecar)
        self.assertNotEqual(sidecar.read_bytes(), old_content)
        self.assertEqual(load_media_project(sidecar), newer)
        clear_recovery(self.project)
        self.assertFalse(sidecar.exists())

    def test_symlink_sidecar_rejected(self):
        sidecar = write_recovery(self.changed(), self.project)
        sidecar.unlink()
        try:
            sidecar.symlink_to(self.project)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink needs elevated Windows permissions.")
        with self.assertRaisesRegex(ValueError, "symlink"):
            write_recovery(self.changed(), self.project)
        with self.assertRaisesRegex(ValueError, "symlink"):
            clear_recovery(self.project)
        self.assertEqual(load_media_project(self.project), self.base)


if __name__ == "__main__":
    unittest.main()
