"""Secure Edivora media project format and real multi-clip FFmpeg integration."""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from local_ai_photo_editor.core.media_project import (
    MAX_CLIPS, MediaClip, MediaSequence, load_media_project, save_media_project,
)
from local_ai_photo_editor.core.media_sequence import (
    SequenceExport, commit_sequence_export,
)


class MediaProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.first = self.root / "first.wav"
        self.second = self.root / "second.wav"
        self.first.write_bytes(b"fixture first" * 100)
        self.second.write_bytes(b"fixture second" * 100)
        self.a = MediaClip.create("audio", self.first, 5000, start_ms=500, end_ms=4100)
        self.b = MediaClip.create("audio", self.second, 8000, start_ms=300, end_ms=7200)

    def make_sequence(self) -> MediaSequence:
        return MediaSequence("audio", (self.a, self.b), self.b.id,
                             normalize=True, fade_in_ms=500, fade_out_ms=200)

    def test_save_load_order_trims_and_master_settings(self) -> None:
        seq = self.make_sequence()
        path = self.root / "session.edap"
        save_media_project(seq, path)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), text)  # in-project sources stay relative
        loaded = load_media_project(path)
        self.assertEqual(loaded, seq)
        self.assertEqual([x.source.name for x in loaded.clips], ["first.wav", "second.wav"])
        self.assertEqual(loaded.length_ms, 10500)

    def test_project_detects_tampered_or_replaced_sources(self) -> None:
        path = self.root / "session.edap"
        save_media_project(self.make_sequence(), path)
        self.first.write_bytes(b"changed" * 100)
        with self.assertRaisesRegex(ValueError, "changed"):
            load_media_project(path)

    def test_reject_unknown_version_fields_duplicates_escape_and_bad_type(self) -> None:
        path = self.root / "session.edap"
        save_media_project(self.make_sequence(), path)
        data = json.loads(path.read_text("utf-8"))
        cases = [
            {**data, "version": 99},
            {**data, "format": "random"},
            {**data, "kind": "video"},
            {**data, "clips": [dict(data["clips"][0], source="../private.wav")]},
            {**data, "clips": [dict(data["clips"][0], start_ms=True)]},
            {**data, "clips": [dict(data["clips"][0], id="../bad")]},
            {**data, "additional": "unused"},
            {**data, "clips": []},
        ]
        for value in cases:
            with self.subTest(case=value):
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises((ValueError, KeyError)):
                    load_media_project(path)
        path.write_text('{"format":"x","format":"x"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_media_project(path)

    def test_limit_video_project_mismatch_and_invalid_splits(self) -> None:
        self.assertEqual(self.a.length_ms, 3600)
        with self.assertRaises(ValueError):
            replace(self.a, start_ms=4000, end_ms=4050).validated("audio")
        with self.assertRaises(ValueError):
            MediaSequence("audio", tuple(self.a for _ in range(MAX_CLIPS + 1))).validated()
        with self.assertRaises(ValueError):
            MediaSequence("video", (self.a,)).validated()
        with self.assertRaises(ValueError):
            save_media_project(self.make_sequence(), self.root / "not-video.edvp")

    def test_atomic_failed_save_keeps_previous_project(self) -> None:
        path = self.root / "session.edap"
        save_media_project(self.make_sequence(), path)
        original = path.read_bytes()
        self.second.unlink()
        with self.assertRaises((FileNotFoundError, ValueError)):
            save_media_project(self.make_sequence(), path)
        self.assertEqual(path.read_bytes(), original)

    def test_external_references_are_explicitly_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            dest = Path(external) / "session.edap"
            save_media_project(self.make_sequence(), dest)
            raw = json.loads(dest.read_text(encoding="utf-8"))
            self.assertTrue(Path(raw["clips"][0]["source"]).is_absolute())
            loaded = load_media_project(dest)
            self.assertEqual(loaded.clips, self.make_sequence().clips)


class FFmpegMultiClipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import imageio_ffmpeg
        cls.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def ff(self, args: list[str]) -> None:
        done = subprocess.run(
            [self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", *args],
            capture_output=True, timeout=40,
        )
        self.assertEqual(done.returncode, 0, done.stderr[-1200:].decode("utf-8", "replace"))

    def test_audio_two_clips_real_render_and_original_protection(self) -> None:
        a, b = self.root / "a.wav", self.root / "b.wav"
        self.ff(["-f", "lavfi", "-i", "sine=frequency=350:sample_rate=48000",
                 "-t", "1.5", "-c:a", "pcm_s16le", "-y", str(a)])
        self.ff(["-f", "lavfi", "-i", "sine=frequency=720:sample_rate=48000",
                 "-t", "1.2", "-c:a", "pcm_s16le", "-y", str(b)])
        orig = a.read_bytes()
        clips = (
            MediaClip.create("audio", a, 1500, start_ms=100, end_ms=1400),
            MediaClip.create("audio", b, 1200, start_ms=0, end_ms=900, volume_percent=70),
        )
        seq = MediaSequence("audio", clips, fade_in_ms=100, fade_out_ms=120)
        export = SequenceExport(seq, self.root / "joined.wav")
        args = export.ffmpeg_arguments(export.temp_output())
        self.assertIn("concat=n=2:v=0:a=1", " ".join(args))
        tmp = Path(args[-1])
        self.ff(args)
        commit_sequence_export(export, tmp)
        self.assertGreater(export.destination.stat().st_size, 20000)
        self.assertEqual(a.read_bytes(), orig)
        with self.assertRaises(ValueError):
            SequenceExport(seq, a).validated()

    def test_video_mixed_audio_and_silent_clips_render(self) -> None:
        a, b = self.root / "a.mp4", self.root / "silent.mp4"
        self.ff([
            "-f", "lavfi", "-i", "testsrc2=s=160x90:r=12",
            "-f", "lavfi", "-i", "sine=frequency=400:sample_rate=48000",
            "-t", "1.2", "-c:v", "mpeg4", "-c:a", "aac", "-y", str(a),
        ])
        self.ff([
            "-f", "lavfi", "-i", "testsrc2=s=240x160:r=15",
            "-t", "1.0", "-c:v", "mpeg4", "-an", "-y", str(b),
        ])
        seq = MediaSequence("video", (
            MediaClip.create("video", a, 1200, start_ms=100, end_ms=1000, has_audio=True),
            MediaClip.create("video", b, 1000, start_ms=0, end_ms=900, has_audio=False),
        ))
        dest = self.root / "sequence.mp4"
        export = SequenceExport(seq, dest)
        temp = export.temp_output()
        args = export.ffmpeg_arguments(temp)
        self.assertIn("anullsrc", " ".join(args))
        self.assertIn("concat=n=2:v=1:a=1", " ".join(args))
        self.ff(args)
        commit_sequence_export(export, temp)
        self.assertGreater(dest.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
