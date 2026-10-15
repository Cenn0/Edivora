"""Guard against stale Windows run publication after newer main changes."""
from pathlib import Path
import unittest


WORKFLOW = (
    Path(__file__).resolve().parents[1] /
    ".github" / "workflows" / "publish-private-test-suite.yml"
)


class ReleaseFreshnessTests(unittest.TestCase):
    def test_old_workflow_run_never_eligible_by_path_denylist(self) -> None:
        source = WORKFLOW.read_text("utf-8")
        # The compiled repository-root main.py was omitted by the old regex.
        self.assertNotIn("git diff --name-only", source)
        self.assertIn('"$SOURCE_SHA" != "$GITHUB_SHA"', source)
        self.assertIn('"$SOURCE_SHA" != "$(git rev-parse HEAD)"', source)

    def test_live_default_branch_checked_again_before_immutable_publish(self) -> None:
        source = WORKFLOW.read_text("utf-8")
        publication = source.split('gh release create "$RELEASE_TAG"', 1)[0]
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/commits/main" --jq .sha', publication)
        self.assertIn('"$SOURCE_SHA" != "$current_main"', publication)
        self.assertIn("exit 1", publication.rsplit('"$SOURCE_SHA" != "$current_main"', 1)[-1])

    def test_release_still_requires_private_verified_main_push(self) -> None:
        source = WORKFLOW.read_text("utf-8")
        self.assertIn("github.event.workflow_run.event == 'push'", source)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", source)
        self.assertIn("Public distribution blocked pending FFmpeg/model/Qt licence review.", source)


if __name__ == "__main__":
    unittest.main()
