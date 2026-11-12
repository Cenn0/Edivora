"""Regression tests for FFmpeg wheel version recorded by Windows packaging."""
from __future__ import annotations

import importlib.util
from importlib import metadata
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "edivora_ffmpeg_provenance", ROOT / "tools" / "ffmpeg_provenance.py"
)
provenance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(provenance)


class FfmpegProvenanceTests(unittest.TestCase):
    def test_labels_follow_installed_distribution_version(self) -> None:
        for version in ("0.6.0", "0.8.0", "1.2.3"):
            with self.subTest(version=version), mock.patch.object(
                provenance.metadata, "version", return_value=version
            ) as lookup:
                self.assertEqual(
                    provenance.installed_ffmpeg_provenance(),
                    (f"imageio-ffmpeg=={version}",
                     f"imageio-ffmpeg {version} standalone binary"),
                )
                lookup.assert_called_once_with("imageio-ffmpeg")

    def test_missing_distribution_fails_closed(self) -> None:
        with mock.patch.object(
            provenance.metadata, "version",
            side_effect=metadata.PackageNotFoundError("imageio-ffmpeg"),
        ):
            with self.assertRaises(metadata.PackageNotFoundError):
                provenance.installed_ffmpeg_provenance()

    def test_empty_distribution_version_fails_closed(self) -> None:
        with mock.patch.object(provenance.metadata, "version", return_value=""):
            with self.assertRaisesRegex(RuntimeError, "no version metadata"):
                provenance.installed_ffmpeg_provenance()

    def test_windows_packager_records_resolved_values_in_both_manifests(self) -> None:
        source = (ROOT / "tools" / "build_windows.py").read_text("utf-8")
        self.assertIn("ffmpeg_distribution, media_engine = installed_ffmpeg_provenance()", source)
        self.assertIn('"source_python_distribution": ffmpeg_distribution,', source)
        self.assertIn('"media_engine": media_engine,', source)
        self.assertNotIn('"source_python_distribution": "imageio-ffmpeg==0.6.0"', source)
        self.assertNotIn('"media_engine": "imageio-ffmpeg 0.6.0 standalone binary"', source)


if __name__ == "__main__":
    unittest.main()
