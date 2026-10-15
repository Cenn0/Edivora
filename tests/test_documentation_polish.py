"""Keep public-facing 0.4 instructions aligned with tested source boundaries."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text("utf-8")


class DocumentationPolishTests(unittest.TestCase):
    def test_current_source_version_is_consistent(self) -> None:
        package = read("pyproject.toml")
        self.assertIn('version = "0.4.0a1"', package)
        for path in (
            "README.md", "README.en.md", "docs/ROADMAP.md",
            "docs/UI_IMPLEMENTATION.md", "docs/MEDIA_PROJECTS_AI.md",
            "docs/MODELS.md",
        ):
            with self.subTest(path=path):
                self.assertIn("0.4.0a1", read(path))
        self.assertNotIn("Aktueller `main`-Quellcode: 0.3.0a1", read("docs/ROADMAP.md"))
        self.assertNotIn("current `main` source (0.3.0a1)", read("docs/MEDIA_PROJECTS_AI.md"))

    def test_public_docs_do_not_advertise_uncleared_binary_downloads(self) -> None:
        for path in ("README.md", "README.en.md", "docs/GETTING_STARTED.md"):
            with self.subTest(path=path):
                content = read(path)
                self.assertNotIn("/releases/download/", content)
                self.assertNotIn("/artifacts/", content)
        self.assertIn("keine genehmigte öffentliche Windows-ZIP", read("docs/ROADMAP.md"))
        self.assertIn("public Windows binary redistribution is not approved",
                      read("docs/RELEASE_NOTES_RESPONSIVE_SUITE.md"))

    def test_launcher_and_media_project_guidance_matches_04(self) -> None:
        guide = read("docs/GETTING_STARTED.md")
        self.assertNotIn("Ausgewählte Werkzeuge öffnen", guide)
        self.assertNotIn("markiere **1–3 Werkzeuge**", guide)
        self.assertIn("Launcher bleibt geöffnet", guide)
        self.assertIn("Änderungen verwerfen", guide)
        self.assertIn("Full HD", guide)
        self.assertIn("Abbrechen", guide)
        implementation = read("docs/UI_IMPLEMENTATION.md")
        self.assertIn("Undo/Redo", implementation)
        self.assertNotIn("kein Medien-Undo", implementation)
        self.assertIn("640 × 480", implementation)


if __name__ == "__main__":
    unittest.main()
