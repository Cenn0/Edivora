"""Deterministic package file inventory: integrity, bounds and privacy."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("edivora_binary_inventory",
                                              ROOT / "tools/binary_inventory.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class BinaryInventoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.package = self.root / "package"
        self.package.mkdir()
        (self.package / "media-tools").mkdir()
        (self.package / "media-tools" / "ffmpeg.exe").write_bytes(b"fake binary")
        (self.package / "models").mkdir()
        (self.package / "models" / "u2netp.onnx").write_bytes(b"synthetic weights")
        (self.package / "LICENSE.txt").write_text("notice\n", encoding="utf-8")

    def test_every_file_hashed_and_sorted_without_host_paths(self):
        doc = inventory.build_inventory(self.package)
        self.assertEqual(doc["file_count"], 3)
        self.assertFalse(doc["public_redistribution_approved"])
        self.assertEqual(doc["license_compliance"], "NOT_REVIEWED")
        self.assertEqual([f["path"] for f in doc["files"]],
                         ["LICENSE.txt", "media-tools/ffmpeg.exe", "models/u2netp.onnx"])
        self.assertEqual([f["category"] for f in doc["files"]],
                         ["notice", "executable", "model"])
        self.assertNotIn(str(self.root), json.dumps(doc))
        self.assertEqual(doc, inventory.build_inventory(self.package))

    def test_changed_byte_changes_aggregate_and_exact_sha(self):
        first = inventory.build_inventory(self.package)
        (self.package / "models" / "u2netp.onnx").write_bytes(b"synthetic weightS")
        second = inventory.build_inventory(self.package)
        self.assertNotEqual(first["sha256_manifest"], second["sha256_manifest"])
        self.assertEqual(first["file_count"], second["file_count"])

    def test_external_atomic_manifest_and_self_reference_guard(self):
        outfile = self.root / "inventory.json"
        result = inventory.write_inventory(self.package, outfile)
        self.assertEqual(json.loads(outfile.read_text("utf-8")), result)
        self.assertEqual(inventory.build_inventory(self.package), result)
        with self.assertRaisesRegex(ValueError, "outside"):
            inventory.write_inventory(self.package, self.package / "manifest.json")

    def test_symlink_and_special_file_fail_closed(self):
        link = self.package / "link"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation requires additional Windows privilege.")
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            inventory.build_inventory(self.package)

    def test_file_count_and_total_bytes_limits(self):
        with patch.object(inventory, "MAX_FILES", 2):
            with self.assertRaisesRegex(ValueError, "too many"):
                inventory.build_inventory(self.package)
        with patch.object(inventory, "MAX_TOTAL_BYTES", 5):
            with self.assertRaisesRegex(ValueError, "size budget"):
                inventory.build_inventory(self.package)

    def test_refuses_empty_package_and_invalid_output_dir(self):
        blank = self.root / "blank"
        blank.mkdir()
        with self.assertRaisesRegex(ValueError, "empty"):
            inventory.build_inventory(blank)
        with self.assertRaisesRegex(ValueError, "invalid"):
            inventory.write_inventory(self.package, self.root / "missing" / "manifest.json")


if __name__ == "__main__":
    unittest.main()
