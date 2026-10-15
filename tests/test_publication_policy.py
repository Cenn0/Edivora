"""Regression checks for public repository release boundaries.

These are static policy checks, not a legal opinion or final binary inventory.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def file_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def step_block(yaml: str, title: str) -> str:
    start = yaml.index("      - name: " + title)
    next_step = yaml.find("      - name:", start + 8)
    return yaml[start:next_step if next_step != -1 else None]


class PublicRepositoryPolicyTests(unittest.TestCase):
    def test_public_windows_artifact_uploads_are_disabled(self):
        workflow = file_text(".github/workflows/windows-alpha.yml")
        for step in (
            "Upload checked portable alpha",
            "Upload verification evidence",
            "Preserve failed runtime package for diagnosis",
        ):
            with self.subTest(step=step):
                self.assertIn(
                    "github.event.repository.private == true",
                    step_block(workflow, step),
                )

    def test_private_release_job_requires_private_repo(self):
        workflow = file_text(".github/workflows/publish-private-test-suite.yml")
        job_guard = workflow.split("  publish:", 1)[1].split("    runs-on:", 1)[0]
        self.assertIn("github.event.repository.private == true", job_guard)

    def test_quarantine_supports_repeatable_removal(self):
        workflow = file_text(".github/workflows/public-binary-quarantine.yml")
        self.assertIn("actions: write", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("gh release delete-asset", workflow)
        self.assertIn("gh api -X DELETE", workflow)
        self.assertIn("workflow_dispatch:", workflow)

    def test_public_documentation_does_not_claim_private_access(self):
        self.assertNotIn("repository is currently private", file_text("README.en.md").lower())
        self.assertNotIn("github-repository ist derzeit privat", file_text("README.md").lower())
        self.assertNotIn("das repository ist zurzeit privat", file_text("docs/CONTRIBUTING.md").lower())
        self.assertTrue((ROOT / "SECURITY.md").is_file())
        self.assertTrue((ROOT / ".github/pull_request_template.md").is_file())


if __name__ == "__main__":
    unittest.main()
