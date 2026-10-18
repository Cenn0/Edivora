"""Portable media folders: round trips, quotas and non-destructive failure."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from local_ai_photo_editor.core.media_project import (
    MediaClip, MediaSequence, load_media_project,
)
from local_ai_photo_editor.core.portable_media import (
    create_portable_media_folder,
)


class PortableMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "personal-song.wav"
        self.original.write_bytes(b"audio-data" * 300)
        self.clip = MediaClip.create("audio", self.original, 6000)
        self.seq = MediaSequence("audio", (self.clip,), self.clip.id)

    def test_roundtrip_and_relative_paths(self) -> None:
        original = self.original.read_bytes()
        target = self.root / "project-for-friend"
        manifest = create_portable_media_folder(self.seq, target)
        self.assertEqual(manifest, target / "project.edap")
        loaded = load_media_project(manifest)
        self.assertEqual(loaded.clips[0].id, self.clip.id)
        self.assertEqual(loaded.clips[0].source.read_bytes(), original)
        self.assertEqual(loaded.clips[0].source.parent, target / "media")
        self.assertEqual(original, self.original.read_bytes())
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(raw["clips"][0]["source"], "media/01.wav")
        self.assertNotIn(str(self.original), manifest.read_text(encoding="utf-8"))

    def test_duplicate_clips_share_one_file_copy(self) -> None:
        duplicate = replace(self.clip, id="0" * 32, start_ms=1000)
        seq = MediaSequence("audio", (self.clip, duplicate))
        manifest = create_portable_media_folder(seq, self.root / "duplicates")
        self.assertEqual(len(list((manifest.parent / "media").iterdir())), 1)
        loaded = load_media_project(manifest)
        self.assertEqual(loaded.clips[0].source, loaded.clips[1].source)
        self.assertEqual(loaded.clips[1].start_ms, 1000)

    def test_multiple_sources_use_distinct_relative_media(self) -> None:
        second = self.root / "second.wav"
        second.write_bytes(b"other-audio" * 220)
        second_clip = MediaClip.create("audio", second, 3500)
        seq = MediaSequence("audio", (self.clip, second_clip))
        manifest = create_portable_media_folder(seq, self.root / "two-sources")
        files = sorted(p.name for p in (manifest.parent / "media").iterdir())
        self.assertEqual(files, ["01.wav", "02.wav"])
        opened = load_media_project(manifest)
        self.assertEqual(opened.clips[0].source.read_bytes(), self.original.read_bytes())
        self.assertEqual(opened.clips[1].source.read_bytes(), second.read_bytes())

    def test_existing_target_and_original_cannot_be_replaced(self) -> None:
        target = self.root / "existing"
        target.mkdir()
        sentinel = target / "private.txt"
        sentinel.write_bytes(b"leave me alone")
        before = self.original.read_bytes()
        with self.assertRaises(FileExistsError):
            create_portable_media_folder(self.seq, target)
        self.assertEqual(sentinel.read_bytes(), b"leave me alone")
        self.assertEqual(self.original.read_bytes(), before)

    def test_target_created_during_final_check_is_never_replaced(self) -> None:
        from unittest.mock import patch
        from local_ai_photo_editor.core.portable_media import _target_directory

        target = self.root / "racing-folder"
        count = 0

        def simulate_race(path):
            nonlocal count
            result = _target_directory(path)
            count += 1
            if count == 2:
                target.mkdir()
                (target / "intruder.txt").write_bytes(b"must survive")
            return result

        with patch("local_ai_photo_editor.core.portable_media._target_directory",
                   side_effect=simulate_race):
            with self.assertRaises(FileExistsError):
                create_portable_media_folder(self.seq, target)
        self.assertEqual((target / "intruder.txt").read_bytes(), b"must survive")
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["intruder.txt"])
        self.assertEqual(list(self.root.glob(".edivora-portable-*")), [])

    def test_over_quota_has_no_partial_published_folder(self) -> None:
        target = self.root / "too-large"
        with self.assertRaisesRegex(ValueError, "quota"):
            create_portable_media_folder(self.seq, target, max_total_bytes=500)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".edivora-portable-*")), [])

    def test_cancellation_cleans_staging(self) -> None:
        calls = 0

        def stop() -> bool:
            nonlocal calls
            calls += 1
            return calls >= 3

        target = self.root / "cancelled"
        with self.assertRaises(InterruptedError):
            create_portable_media_folder(self.seq, target, cancelled=stop)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob(".edivora-portable-*")), [])

    def test_invalid_size_budget_fails_before_writes(self) -> None:
        for limit in (0, True, -1, 3 * 1024**3):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    create_portable_media_folder(self.seq, self.root / "nope", max_total_bytes=limit)
                self.assertFalse((self.root / "nope").exists())


if __name__ == "__main__":
    unittest.main()
