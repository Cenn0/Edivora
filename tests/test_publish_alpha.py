"""Portable release gates use only the standard library and synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools import publish_alpha as release


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def evidence(self):
        source = {
            "run_id": release.BUILD_RUN,
            "head_sha": release.BUILD_COMMIT,
            "artifact_id": release.BUILD_ARTIFACT_ID,
            "artifact_digest": release.BUILD_DIGEST,
        }
        report = {
            "status": "ok",
            "offline_enforcement_confirmed": True,
            "rule_removal_verified": True,
            "executable_sha256": release.EXE_SHA256,
            "smoke_checks": [
                {"name": "worker", "status": "ok", "exit_code": 0,
                 "same_executable_worker_confirmed": True},
                {"name": "gui", "status": "ok", "exit_code": 0},
            ],
        }
        (self.root / "source-artifact.json").write_text(json.dumps(source), encoding="utf-8")
        (self.root / "offline-package-result.json").write_text(json.dumps(report), encoding="utf-8")
        return source, report

    def test_accepts_exact_offline_evidence(self):
        self.evidence()
        release.verify_offline_evidence(self.root)

    def test_rejects_offline_gate_without_firewall(self):
        _, report = self.evidence()
        report["offline_enforcement_confirmed"] = False
        (self.root / "offline-package-result.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "offline block"):
            release.verify_offline_evidence(self.root)

    def test_rejects_different_source_binary(self):
        _, report = self.evidence()
        report["executable_sha256"] = "0" * 64
        (self.root / "offline-package-result.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "EXE differs"):
            release.verify_offline_evidence(self.root)

    def test_rejects_expired_or_modified_actions_artifact(self):
        item = {
            "id": release.BUILD_ARTIFACT_ID,
            "name": "LocalAiPhotoEditor-windows-x64-alpha",
            "digest": release.BUILD_DIGEST,
            "size_in_bytes": release.BUILD_ARTIFACT_SIZE,
            "expired": False,
        }
        data = {"total_count": 1, "artifacts": [item]}
        release.validate_artifact(data, artifact_id=release.BUILD_ARTIFACT_ID,
                                  name=item["name"], digest=release.BUILD_DIGEST,
                                  size=release.BUILD_ARTIFACT_SIZE)
        item["expired"] = True
        with self.assertRaisesRegex(ValueError, "expired"):
            release.validate_artifact(data, artifact_id=release.BUILD_ARTIFACT_ID,
                                      name=item["name"], digest=release.BUILD_DIGEST)
        item["expired"] = False
        item["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            release.validate_artifact(data, artifact_id=release.BUILD_ARTIFACT_ID,
                                      name=item["name"], digest=release.BUILD_DIGEST)

    def test_rejects_wrong_workflow_origin(self):
        data = {
            "id": release.BUILD_RUN,
            "head_sha": release.BUILD_COMMIT,
            "path": ".github/workflows/windows-alpha.yml",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": release.REPO},
            "head_repository": {"full_name": "untrusted/fork"},
        }
        with self.assertRaisesRegex(ValueError, "Head repository mismatch"):
            release.validate_run(data, run_id=release.BUILD_RUN, commit=release.BUILD_COMMIT,
                                 path=data["path"], event="push")

    def test_zip_has_single_top_level_application_directory(self):
        app = self.root / "app"
        app.mkdir()
        for number in range(22):
            (app / ("file-%02d.txt" % number)).write_text("test", encoding="utf-8")
        (app / "LocalAiPhotoEditor.exe").write_bytes(b"synthetic")
        archive_path = self.root / "release.zip"
        release.zip_release(app, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.namelist()
            self.assertTrue(all(name.startswith("LocalAiPhotoEditor/") for name in members))
            self.assertIn("LocalAiPhotoEditor/LocalAiPhotoEditor.exe", members)


if __name__ == "__main__":
    unittest.main()
