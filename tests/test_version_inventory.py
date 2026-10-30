"""Version-only Windows package inventory must not embed source locations."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "tools" / "version_inventory.py"
_spec = importlib.util.spec_from_file_location("edivora_version_inventory", SOURCE)
inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory)


class DummyDistribution:
    def __init__(self, name: str, version: str, origin: str = "") -> None:
        self.metadata = {"Name": name, "direct_url.json": origin}
        self.version = version


class VersionInventoryTests(unittest.TestCase):
    def test_deterministic_versions_only_without_private_source_origins(self):
        private_origin = "file:///users/synthetic-private-path/project"
        credentialed_origin = ("git+https://" + "username" + ":" + "synthetic-token"
                              + "@" + "example.invalid/repo")
        entries = [
            DummyDistribution("Some_Package", "2.3.0", private_origin),
            DummyDistribution("another.package", "1.0+local", credentialed_origin),
        ]
        text = inventory.render_version_inventory(entries)
        self.assertEqual(text.splitlines()[-2:], [
            "another-package==1.0+local", "some-package==2.3.0",
        ])
        self.assertNotIn(private_origin, text)
        self.assertNotIn(credentialed_origin, text)
        self.assertNotIn("file://", text)
        self.assertNotIn("git+https://", text)

    def test_disallow_untrusted_distribution_metadata(self):
        for name, version in (("Name\nX", "1"), ("ok", "1 @ https://host"),
                              ("", "1"), ("ok", "")):
            with self.subTest(name=name, version=version):
                with self.assertRaises(ValueError):
                    inventory.render_version_inventory([DummyDistribution(name, version)])

    def test_duplicate_normalized_name_conflicts_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            inventory.render_version_inventory([
                DummyDistribution("Same.Package", "1.0"),
                DummyDistribution("same-package", "2.0"),
            ])

    def test_no_empty_inventory(self):
        with self.assertRaisesRegex(ValueError, "No installed"):
            inventory.render_version_inventory([])

    def test_actual_environment_inventory_omits_local_paths(self):
        text = inventory.render_version_inventory()
        self.assertGreater(len(text.splitlines()), 4)
        self.assertNotIn("file://", text)
        self.assertNotIn("git+https://", text)
        self.assertNotIn("/home/", text)


if __name__ == "__main__":
    unittest.main()
