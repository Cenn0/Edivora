"""Versioned project persistence: exact pixels, history and adversarial input."""
from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZIP_STORED, ZipFile

from PIL import Image

from local_ai_photo_editor.core import ImageDocument, load_project, save_project


class ProjectFileTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.project = self.folder / "session.laip"
        self.source = self.folder / "private-image.png"
        self.original = Image.new("RGBA", (4, 3), (20, 40, 60, 100))
        self.original.putpixel((0, 0), (255, 70, 8, 0))
        self.document = ImageDocument(self.original, source_path=self.source)

    def _rewrite(self, transform) -> None:
        """Rebuild a valid ZIP whose contents have been edited by the test."""
        with ZipFile(self.project) as archive:
            content = {name: archive.read(name) for name in archive.namelist()}
        transform(content)
        with ZipFile(self.project, "w", compression=ZIP_STORED) as archive:
            for name, data in content.items():
                archive.writestr(name, data)

    def test_roundtrip_preserves_original_current_undo_redo_and_labels(self) -> None:
        second = Image.new("RGBA", (3, 4), (100, 50, 200, 80))
        third = Image.new("RGBA", (3, 4), (20, 220, 10, 180))
        self.document.apply(second, "Rotate")
        self.document.apply(third, "Adjust")
        self.assertTrue(self.document.undo())
        self.assertEqual(save_project(self.document, self.project), self.project)
        restored = load_project(self.project)

        self.assertIsNone(restored.source_path)
        self.assertEqual(restored.original.size, self.original.size)
        self.assertEqual(restored.original.tobytes(), self.original.tobytes())
        self.assertEqual(restored.current.tobytes(), second.tobytes())
        self.assertEqual(restored.history, ("Rotate",))
        self.assertTrue(restored.can_undo)
        self.assertTrue(restored.can_redo)
        self.assertTrue(restored.redo())
        self.assertEqual(restored.current.tobytes(), third.tobytes())
        self.assertEqual(restored.history, ("Rotate", "Adjust"))
        self.assertTrue(restored.undo())
        self.assertTrue(restored.undo())
        self.assertEqual(restored.current.tobytes(), self.original.tobytes())
        self.assertFalse(restored.undo())

    def test_colour_and_alpha_are_exact_with_non_square_size(self) -> None:
        edited = Image.new("RGBA", (5, 3))
        for y in range(3):
            for x in range(5):
                edited.putpixel((x, y), (x * 41, y * 63, (x+y) * 13, (x * 30 + y * 19) % 256))
        self.document.apply(edited, "Crop, mask and colour")
        save_project(self.document, self.project)
        actual = load_project(self.project)
        self.assertEqual(actual.current.mode, "RGBA")
        self.assertEqual(actual.current.tobytes(), edited.tobytes())

    def test_archive_does_not_leak_original_path_or_image_metadata(self) -> None:
        self.document.original.info["exif"] = b"ignored"
        save_project(self.document, self.project)
        with ZipFile(self.project) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"manifest.json", "frames/original.png", "frames/current.png"},
            )
            manifest = archive.read("manifest.json")
            self.assertNotIn(str(self.source).encode(), manifest)
            self.assertNotIn(b"private-image", manifest)
            with Image.open(BytesIO(archive.read("frames/original.png"))) as original:
                self.assertFalse(original.info)

    def test_project_without_edits_is_valid(self) -> None:
        save_project(self.document, self.project)
        restored = load_project(self.project)
        self.assertEqual(restored.history, ())
        self.assertFalse(restored.can_undo)
        self.assertFalse(restored.can_redo)
        self.assertEqual(restored.current.tobytes(), self.original.tobytes())

    def test_discarded_pixel_history_remains_discarded_but_labels_survive(self) -> None:
        original = Image.new("RGB", (2, 2), "black")
        document = ImageDocument(original, history_budget_bytes=12)
        for color in ("red", "green", "blue"):
            document.apply(Image.new("RGB", (2, 2), color), color)
        self.assertEqual(document.history, ("red", "green", "blue"))
        self.assertEqual(document.undo_memory_bytes, 12)
        save_project(document, self.project)
        restored = load_project(self.project)
        self.assertEqual(restored.history, ("red", "green", "blue"))
        self.assertTrue(restored.undo())
        self.assertEqual(restored.current.getpixel((0, 0)), (0, 128, 0))
        self.assertFalse(restored.undo())

    def test_atomic_save_replaces_existing_project(self) -> None:
        save_project(self.document, self.project)
        first = self.project.read_bytes()
        self.document.apply(Image.new("RGBA", (4, 3), "red"), "Red")
        save_project(self.document, self.project)
        self.assertNotEqual(self.project.read_bytes(), first)
        self.assertEqual(load_project(self.project).history, ("Red",))
        self.assertEqual(list(self.folder.glob(".local-ai-photo-project-*")), [])

    def test_failed_save_preserves_old_project_and_cleans_temporary_file(self) -> None:
        save_project(self.document, self.project)
        before = self.project.read_bytes()
        with patch.object(Image.Image, "save", side_effect=OSError("Simulated disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                save_project(self.document, self.project)
        self.assertEqual(self.project.read_bytes(), before)
        self.assertEqual(list(self.folder.glob(".local-ai-photo-project-*")), [])

    def test_refuse_source_hardlink_and_symlink(self) -> None:
        self.original.save(self.source)
        hardlink = self.folder / "source-link.laip"
        try:
            os.link(self.source, hardlink)
        except OSError as exc:
            self.skipTest(f"Hardlinks are unavailable: {exc}")
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "original"):
            save_project(self.document, hardlink)
        self.assertEqual(self.source.read_bytes(), before)
        symbolic = self.folder / "source-symlink.laip"
        try:
            symbolic.symlink_to(self.source)
        except OSError:
            return
        with self.assertRaisesRegex(ValueError, "original"):
            save_project(self.document, symbolic)

    def test_reject_non_project_and_unexpected_extension_for_save(self) -> None:
        self.project.write_bytes(b"not a ZIP")
        with self.assertRaises(ValueError):
            load_project(self.project)
        with self.assertRaisesRegex(ValueError, ".laip"):
            save_project(self.document, self.folder / "not-a-project.png")

    def test_reject_changed_snapshot_checksum(self) -> None:
        self.document.apply(Image.new("RGBA", (4, 3), "red"), "Edited")
        save_project(self.document, self.project)
        def change_frame(content):
            image = Image.new("RGBA", (4, 3), "green")
            output = BytesIO()
            image.save(output, format="PNG")
            content["frames/current.png"] = output.getvalue()
        self._rewrite(change_frame)
        with self.assertRaisesRegex(ValueError, "checksum"):
            load_project(self.project)

    def test_reject_unsupported_version_and_inconsistent_labels(self) -> None:
        self.document.apply(Image.new("RGBA", (4, 3), "blue"), "Blue")
        save_project(self.document, self.project)
        def tamper_version(content):
            manifest = json.loads(content["manifest.json"])
            manifest["version"] = 999
            content["manifest.json"] = json.dumps(manifest).encode()
        self._rewrite(tamper_version)
        with self.assertRaisesRegex(ValueError, "version"):
            load_project(self.project)

        save_project(self.document, self.project)
        def tamper_labels(content):
            manifest = json.loads(content["manifest.json"])
            manifest["history_labels"] = ["Wrong label"]
            content["manifest.json"] = json.dumps(manifest).encode()
        self._rewrite(tamper_labels)
        with self.assertRaisesRegex(ValueError, "history"):
            load_project(self.project)

    def test_reject_missing_and_unexpected_archive_members(self) -> None:
        save_project(self.document, self.project)
        self._rewrite(lambda content: content.pop("frames/original.png"))
        with self.assertRaisesRegex(ValueError, "missing or unexpected"):
            load_project(self.project)

        save_project(self.document, self.project)
        self._rewrite(lambda content: content.update({"../../escape.txt": b"no extraction"}))
        with self.assertRaisesRegex(ValueError, "missing or unexpected"):
            load_project(self.project)
        self.assertFalse((self.folder.parent / "escape.txt").exists())

    def test_reject_duplicate_members_and_oversized_manifest(self) -> None:
        save_project(self.document, self.project)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.project, "a") as archive:
                archive.writestr("manifest.json", b"{}")
        with self.assertRaisesRegex(ValueError, "Invalid"):
            load_project(self.project)

        save_project(self.document, self.project)
        with ZipFile(self.project, "a") as archive:
            archive.writestr("noise", b"X" * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            load_project(self.project)

    def test_history_budget_is_rejected_before_any_png_decoding(self) -> None:
        self.document.apply(Image.new("RGBA", (4, 3), "red"), "Edit")
        save_project(self.document, self.project)

        def lower_budget(content):
            manifest = json.loads(content["manifest.json"])
            manifest["history_budget_bytes"] = 0
            content["manifest.json"] = json.dumps(manifest).encode("utf-8")

        self._rewrite(lower_budget)
        with patch.object(Image, "open", side_effect=AssertionError("Decoded before preflight")) as opened:
            with self.assertRaisesRegex(ValueError, "history exceeds"):
                load_project(self.project)
            opened.assert_not_called()

    def test_invalid_history_descriptor_is_rejected_before_png_decoding(self) -> None:
        self.document.apply(Image.new("RGBA", (4, 3), "red"), "Edit")
        save_project(self.document, self.project)

        def bad_descriptor(content):
            manifest = json.loads(content["manifest.json"])
            manifest["undo"][0]["frame"]["height"] = 40_000_001
            content["manifest.json"] = json.dumps(manifest).encode("utf-8")

        self._rewrite(bad_descriptor)
        with patch.object(Image, "open", side_effect=AssertionError("Decoded before preflight")) as opened:
            with self.assertRaisesRegex(ValueError, "limited"):
                load_project(self.project)
            opened.assert_not_called()

    def test_aggregate_base_and_history_memory_cap_precedes_decode(self) -> None:
        self.document.apply(Image.new("RGBA", (4, 3), "red"), "One")
        self.document.apply(Image.new("RGBA", (4, 3), "blue"), "Two")
        save_project(self.document, self.project)

        def make_large(content):
            manifest = json.loads(content["manifest.json"])
            for frame in (manifest["original"], manifest["current"]):
                frame.update(width=10000, height=4000)  # 160 MB each
            for item in manifest["undo"]:
                item["frame"].update(width=7500, height=4000)  # 120 MB each
            content["manifest.json"] = json.dumps(manifest).encode("utf-8")

        self._rewrite(make_large)
        with patch.object(Image, "open", side_effect=AssertionError("Decoded before preflight")) as opened:
            with self.assertRaisesRegex(ValueError, "decoded image memory"):
                load_project(self.project)
            opened.assert_not_called()

    def test_history_budget_at_exact_descriptor_byte_boundary_still_loads(self) -> None:
        photo = Image.new("RGB", (2, 2), "black")
        document = ImageDocument(photo, history_budget_bytes=12)
        document.apply(Image.new("RGB", (2, 2), "red"), "Edit")
        save_project(document, self.project)
        restored = load_project(self.project)
        self.assertEqual(restored.history_memory_bytes, 12)
        self.assertTrue(restored.undo())

    def test_invalid_frame_dimensions_are_rejected_before_decode(self) -> None:
        save_project(self.document, self.project)
        def tamper_size(content):
            manifest = json.loads(content["manifest.json"])
            manifest["original"]["width"] = 40_000_001
            content["manifest.json"] = json.dumps(manifest).encode()
        self._rewrite(tamper_size)
        with patch.object(Image.Image, "load") as load:
            with self.assertRaisesRegex(ValueError, "limited"):
                load_project(self.project)
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
