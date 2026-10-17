"""Explicit media relinking: source identity, failure atomicity and path safety."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from local_ai_photo_editor.core.media_project import (
    MediaClip, MediaSequence, load_media_project, save_media_project,
    unavailable_media,
)


class MediaRelinkingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / "track.wav"
        self.source.write_bytes(b"demo-audio-file" * 150)
        self.clip = MediaClip.create("audio", self.source, 5000)
        self.project = self.root / "project.edap"
        save_media_project(MediaSequence("audio", (self.clip,)), self.project)

    def _move_source(self):
        moved = self.root / "other-folder" / "track.wav"
        moved.parent.mkdir(exist_ok=True)
        self.source.rename(moved)
        return moved

    def test_missing_media_discovery_and_exact_relink(self):
        moved = self._move_source()
        missing = unavailable_media(self.project)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].clip_id, self.clip.id)
        self.assertEqual(missing[0].reason, "missing")
        self.assertEqual(missing[0].name, "track.wav")
        with self.assertRaises(FileNotFoundError):
            load_media_project(self.project)
        new = load_media_project(self.project, replacements={self.clip.id: moved})
        self.assertEqual(new.clips[0].source, moved)
        self.assertEqual(new.clips[0].start_ms, self.clip.start_ms)
        self.assertEqual(new.clips[0].end_ms, self.clip.end_ms)
        self.assertEqual(new.clips[0].id, self.clip.id)
        # Relinking doesn't edit the saved manifest before the user saves.
        self.assertIn('"source": "track.wav"', self.project.read_text("utf-8"))

    def test_wrong_file_and_wrong_size_do_not_replace(self):
        moved = self._move_source()
        wrong = self.root / "wrong.wav"
        wrong.write_bytes(b"Z" * moved.stat().st_size)
        with self.assertRaisesRegex(ValueError, "changed"):
            load_media_project(self.project, replacements={self.clip.id: wrong})
        wrong.write_bytes(b"small")
        with self.assertRaisesRegex(ValueError, "changed"):
            load_media_project(self.project, replacements={self.clip.id: wrong})
        self.assertEqual(unavailable_media(self.project)[0].reason, "missing")

    def test_changed_in_place_can_be_relinked_to_original_bytes(self):
        backup = self.root / "backup.wav"
        shutil.copyfile(self.source, backup)
        self.source.write_bytes(b"modified" * 320)
        self.assertEqual(unavailable_media(self.project)[0].reason, "changed")
        result = load_media_project(self.project, replacements={self.clip.id: backup})
        self.assertEqual(result.clips[0].source, backup)
        self.assertEqual(self.source.read_bytes(), b"modified" * 320)

    def test_forged_override_and_unused_mapping_rejected(self):
        self.assertEqual(unavailable_media(self.project), ())
        other = self.root / "same.wav"
        shutil.copyfile(self.source, other)
        with self.assertRaisesRegex(ValueError, "unchanged"):
            load_media_project(self.project, replacements={self.clip.id: other})
        with self.assertRaisesRegex(ValueError, "Unused"):
            load_media_project(self.project, replacements={"a" * 32: other})

    def test_escaping_relative_reference_does_not_become_a_relink_prompt(self):
        data = json.loads(self.project.read_text("utf-8"))
        data["clips"][0]["source"] = "../outside.wav"
        self.project.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside"):
            unavailable_media(self.project)

    def test_invalid_json_and_invalid_digest_are_rejected(self):
        data = json.loads(self.project.read_text("utf-8"))
        data["clips"][0]["fingerprint"]["sample_sha256"] = "g" * 64
        self.project.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            unavailable_media(self.project)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            load_media_project(self.project)

    def test_relinked_save_remains_portable_within_project_dir(self):
        moved = self._move_source()
        result = load_media_project(self.project, replacements={self.clip.id: moved})
        relocated_project = moved.parent / "new.edap"
        save_media_project(result, relocated_project)
        self.assertEqual(load_media_project(relocated_project), result)
        self.assertNotIn(str(self.root), relocated_project.read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
