"""Security, command, multiple-window launcher and media editor MVP regressions."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import string
import tempfile
import unittest
from unittest.mock import patch

from local_ai_photo_editor.__main__ import tool_command
from local_ai_photo_editor.core.media import (
    MediaExport, protects_source, validate_source,
)
from local_ai_photo_editor.ui.media_strings import STRINGS

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


class MediaBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        root = Path(self.dir.name)
        self.source = root / "clip with spaces.mp4"
        self.source.write_bytes(b"synthetic fixture")
        self.output = root / "new clip.mp4"

    def test_paths_and_source_protection(self) -> None:
        self.assertEqual(validate_source(self.source, "video"), self.source.resolve())
        self.assertFalse(protects_source(self.source, self.source))
        self.assertTrue(protects_source(self.source, self.output))
        link = self.source.parent / "link.mp4"
        try:
            os.link(self.source, link)
        except OSError:
            pass
        else:
            self.assertFalse(protects_source(self.source, link))
        with self.assertRaises(ValueError):
            validate_source(self.source, "audio")
        self.assertFalse(protects_source(self.source, self.source.parent / "." / self.source.name))

    def test_video_command_is_argument_vector_and_no_network(self) -> None:
        job = MediaExport("video", self.source, self.output, 5000, 200, 4000, mute=True)
        args = job.ffmpeg_arguments(job.temp_output())
        self.assertIn("file,pipe,data", args)
        self.assertIn(str(self.source.resolve()), args)
        self.assertIn("mpeg4", args)
        self.assertIn("-an", args)
        self.assertNotIn("-c:a", args)
        self.assertNotIn("https", " ".join(args))
        self.assertNotIn("-copyts", args)

    def test_audio_volume_normalize_fades_and_formats(self) -> None:
        audio = self.source.parent / "original.wav"
        audio.write_bytes(b"fixture")
        out = self.source.parent / "result.mp3"
        job = MediaExport("audio", audio, out, 10000, 1000, 8500,
                          volume_percent=125, normalize=True, fade_in_ms=500, fade_out_ms=1000)
        args = job.ffmpeg_arguments(job.temp_output())
        self.assertEqual(args[args.index("-c:a") + 1], "libmp3lame")
        filters = args[args.index("-af") + 1]
        self.assertIn("volume=1.25", filters)
        self.assertIn("loudnorm=", filters)
        self.assertIn("afade=t=in:st=0:d=0.500", filters)
        self.assertIn("afade=t=out:st=6.500:d=1.000", filters)

    def test_invalid_ranges_and_source_overwrite_are_rejected(self) -> None:
        base = dict(kind="video", source=self.source, destination=self.output,
                    duration_ms=3000, start_ms=0, end_ms=3000)
        for values in (
            {"start_ms": 2900, "end_ms": 2900},
            {"start_ms": -1},
            {"end_ms": 3001},
            {"volume_percent": 201},
            {"fade_in_ms": 10},
            {"destination": self.source},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                MediaExport(**{**base, **values}).validated()

    def test_temp_must_be_in_same_directory(self) -> None:
        job = MediaExport("video", self.source, self.output, 3000, 0, 2500)
        with self.assertRaises(ValueError):
            job.ffmpeg_arguments(Path(self.dir.name).parent / "other.mp4")

    def test_executable_selection_keeps_one_launcher_binary(self) -> None:
        with patch("local_ai_photo_editor.__main__._compiled_executable", return_value="C:/Edivora/Edivora.exe"):
            self.assertEqual(tool_command("photo"), ("C:/Edivora/Edivora.exe", ["--tool", "photo"]))
            self.assertEqual(tool_command("video"), ("C:/Edivora/Edivora.exe", ["--tool", "video"]))
            self.assertEqual(tool_command("audio"), ("C:/Edivora/Edivora.exe", ["--tool", "audio"]))
        with self.assertRaises(ValueError):
            tool_command("other")

    def test_media_translations_match(self) -> None:
        self.assertEqual(STRINGS["de"].keys(), STRINGS["en"].keys())
        for key in STRINGS["de"]:
            with self.subTest(key=key):
                self.assertTrue(STRINGS["de"][key])
                self.assertTrue(STRINGS["en"][key])
                placeholders = lambda value: {name for _, name, _, _ in string.Formatter().parse(value) if name}
                self.assertEqual(placeholders(STRINGS["de"][key]), placeholders(STRINGS["en"][key]))


@unittest.skipUnless(QT_AVAILABLE, "Qt GUI checks require PySide6.")
class LauncherQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_two_and_three_editors_are_independently_spawned(self) -> None:
        from local_ai_photo_editor.ui.launcher import LauncherWindow
        launched = []
        window = LauncherWindow(lambda tool: launched.append(tool) or True)
        self.addCleanup(window.deleteLater)
        from PySide6.QtWidgets import QCheckBox
        window.show()
        self.app.processEvents()
        self.assertEqual(window.findChildren(QCheckBox), [])
        self.assertFalse(hasattr(window, "open_selected"))
        for tool in ("photo", "video", "audio", "photo"):
            window.quick_buttons[tool].click()
            self.assertTrue(window.isVisible())
        self.assertEqual(launched, ["photo", "video", "audio", "photo"])
        window.language_combo.setCurrentIndex(1)
        self.assertIn("Audio", window.quick_buttons["audio"].accessibleName())
        window.quick_buttons["audio"].click()
        self.assertEqual(launched[-1], "audio")
        window.close()

    def test_both_media_workspaces_initialize_and_localize(self) -> None:
        from local_ai_photo_editor.ui.media_window import MediaWindow
        for mode in ("video", "audio"):
            with self.subTest(mode=mode):
                window = MediaWindow(mode)
                self.assertFalse(window.export_button.isEnabled())
                self.assertIn("Edivora", window.windowTitle())
                self.assertEqual(window.kind, mode)
                window.language_combo.setCurrentIndex(1)
                self.assertEqual(window.open_button.accessibleName(), "Open file")
                window.close()
                window.deleteLater()


if __name__ == "__main__":
    unittest.main()
