"""Regression tests for FFmpeg wheel version recorded by Windows packaging."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
from importlib import metadata
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
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
        self.assertIn("verified_bundled_ffmpeg_path(", source)
        self.assertIn("imageio_ffmpeg.get_ffmpeg_exe(), imageio_ffmpeg.__file__", source)
        self.assertIn('"media_engine": media_engine,', source)
        self.assertNotIn('"source_python_distribution": "imageio-ffmpeg==0.6.0"', source)
        self.assertNotIn('"media_engine": "imageio-ffmpeg 0.6.0 standalone binary"', source)


    def test_public_license_notice_stays_version_neutral(self) -> None:
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text("utf-8")
        self.assertNotIn("imageio-ffmpeg==0.6.0", notice)
        self.assertIn("FFMPEG_BUILD_PROVENANCE.json", notice)
        self.assertIn("NOT YET PUBLICATION-READY", notice)



class BundledFfmpegPathTests(unittest.TestCase):
    """Reject system/overridden FFmpeg when claiming wheel provenance."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package_dir = self.root / "imageio_ffmpeg"
        self.binaries_dir = self.package_dir / "binaries"
        self.binaries_dir.mkdir(parents=True)
        self.package_file = self.package_dir / "__init__.py"
        self.package_file.write_text("", encoding="utf-8")
        self.binary = self.binaries_dir / "ffmpeg-win-x86_64.exe"
        self.binary.write_bytes(b"synthetic binary")
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(self.binary.read_bytes()).digest()
        ).decode("ascii").rstrip("=")
        self.wheel_record = metadata.PackagePath(
            "imageio_ffmpeg/binaries/ffmpeg-win-x86_64.exe"
        )
        self.wheel_record.hash = SimpleNamespace(mode="sha256", value=digest)
        self.distribution = SimpleNamespace(
            files=[self.wheel_record],
            locate_file=lambda entry: self.root / str(entry),
        )
        patcher = mock.patch.object(
            provenance.metadata, "distribution", return_value=self.distribution
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_wheel_binary_accepted(self) -> None:
        self.assertEqual(
            provenance.verified_bundled_ffmpeg_path(self.binary, self.package_file),
            self.binary.resolve(),
        )

    def test_external_override_rejected_without_leaking_path(self) -> None:
        outside = self.root / "synthetic-sensitive-path" / "ffmpeg.exe"
        outside.parent.mkdir()
        outside.write_bytes(b"synthetic binary")
        with self.assertRaises(RuntimeError) as error:
            provenance.verified_bundled_ffmpeg_path(outside, self.package_file)
        self.assertNotIn("synthetic-sensitive-path", str(error.exception))

    def test_similarly_prefixed_sibling_rejected(self) -> None:
        sibling = self.package_dir / "binaries-other" / "ffmpeg.exe"
        sibling.parent.mkdir()
        sibling.write_bytes(b"synthetic binary")
        with self.assertRaises(RuntimeError):
            provenance.verified_bundled_ffmpeg_path(sibling, self.package_file)

    def test_missing_binary_rejected_without_path_echo(self) -> None:
        with self.assertRaises(RuntimeError) as error:
            provenance.verified_bundled_ffmpeg_path(
                self.root / "synthetic-sensitive-path", self.package_file
            )
        self.assertNotIn("synthetic-sensitive-path", str(error.exception))

    def test_binary_symlink_outside_wheel_rejected(self) -> None:
        outside = self.root / "elsewhere.exe"
        outside.write_bytes(b"synthetic binary")
        link = self.binaries_dir / "symlink.exe"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(RuntimeError):
            provenance.verified_bundled_ffmpeg_path(link, self.package_file)

    def test_symlinked_binaries_directory_rejected(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "ffmpeg.exe").write_bytes(b"synthetic binary")
        self.binary.unlink()
        self.binaries_dir.rmdir()
        try:
            self.binaries_dir.symlink_to(elsewhere, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlinks unavailable")
        with self.assertRaises(RuntimeError):
            provenance.verified_bundled_ffmpeg_path(
                elsewhere / "ffmpeg.exe", self.package_file
            )


    def test_unrecorded_file_in_wheel_directory_is_rejected(self) -> None:
        other = self.binaries_dir / "ffmpeg-injected.exe"
        other.write_bytes(b"synthetic injected binary")
        with self.assertRaises(RuntimeError):
            provenance.verified_bundled_ffmpeg_path(other, self.package_file)

    def test_recorded_binary_modified_after_install_is_rejected(self) -> None:
        self.binary.write_bytes(b"synthetic modified binary")
        with self.assertRaises(RuntimeError):
            provenance.verified_bundled_ffmpeg_path(self.binary, self.package_file)

    def test_missing_or_unsupported_record_hash_is_rejected(self) -> None:
        for bad_hash in (None, SimpleNamespace(mode="md5", value="placeholder"),
                         SimpleNamespace(mode="sha256", value="")):
            with self.subTest(bad_hash=bad_hash):
                self.wheel_record.hash = bad_hash
                with self.assertRaises(RuntimeError):
                    provenance.verified_bundled_ffmpeg_path(
                        self.binary, self.package_file
                    )

    def test_missing_wheel_record_is_rejected(self) -> None:
        for records in (None, []):
            with self.subTest(records=records):
                self.distribution.files = records
                with self.assertRaises(RuntimeError):
                    provenance.verified_bundled_ffmpeg_path(
                        self.binary, self.package_file
                    )

if __name__ == "__main__":
    unittest.main()
