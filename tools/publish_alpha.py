"""Publish only the already-verified Windows 0.1 test alpha.

Build-time/release-time tooling; not imported by the application.  The exact
Actions artifacts are intentionally pinned to prevent accidental publication
of a later, unverified build.  Subsequent versions need their own evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request
import zipfile

REPO = "Cenn0/LocalAiPhotoEditor"
TAG = "v0.1.0-alpha.1"
BUILD_RUN = 38311556834
BUILD_COMMIT = "2b1682b74bd406238865e0b6f8ad1ed151890032"
BUILD_ARTIFACT_ID = 11775901053
BUILD_DIGEST = "sha256:0abda2fb998a43ce01ef989ed51fd4dfa128de006f3956ccd4c725c7b34e70b9"
BUILD_ARTIFACT_SIZE = 70652403
OFFLINE_RUN = 38313711747
OFFLINE_COMMIT = "6d75397a8cf4ca6f573c650033b6f4018f650b1f"
OFFLINE_ARTIFACT_ID = 11775129907
OFFLINE_DIGEST = "sha256:abaf7edaa502118f1d0c7de5d32df3bb66a4f0eef7376973c620c010888bfdc5"
EXE_SHA256 = "cc8ab845f93310a63b16187a5143fef43d71e98dbf55b7aaf4f098457fc5cb8a"
MODEL_SHA256 = "309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8"
ARCHIVE_NAME = "LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def api_get(endpoint: str) -> dict:
    token = os.environ.get("GH_TOKEN")
    require(bool(token), "GH_TOKEN is required for the private repository")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + REPO + "/" + endpoint,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def validate_run(run: dict, *, run_id: int, commit: str, path: str, event: str) -> None:
    require(run.get("id") == run_id, "Unexpected workflow run ID")
    require(run.get("head_sha") == commit, "Unexpected source commit")
    require(run.get("path") == path, "Unexpected workflow path")
    require(run.get("event") == event, "Unexpected workflow event")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "Source workflow did not complete successfully")
    require(run.get("repository", {}).get("full_name") == REPO, "Source repository mismatch")
    require(run.get("head_repository", {}).get("full_name") == REPO, "Head repository mismatch")


def validate_artifact(artifacts: dict, *, artifact_id: int, name: str,
                      digest: str, size: int | None = None) -> None:
    require(artifacts.get("total_count", 0) <= 100, "Incomplete artifact listing")
    selected = [
        a for a in artifacts.get("artifacts", [])
        if a.get("id") == artifact_id and a.get("name") == name
    ]
    require(len(selected) == 1, "Expected exactly one selected artifact")
    a = selected[0]
    require(a.get("digest") == digest, "Artifact SHA-256 does not match the recorded value")
    require(a.get("expired") is False, "Required Actions artifact expired")
    if size is not None:
        require(a.get("size_in_bytes") == size, "Artifact size mismatch")


def verify_remote() -> None:
    require(os.environ.get("GITHUB_REPOSITORY") == REPO, "Unexpected repository")
    source = api_get("actions/runs/" + str(BUILD_RUN))
    validate_run(source, run_id=BUILD_RUN, commit=BUILD_COMMIT,
                 path=".github/workflows/windows-alpha.yml", event="push")
    offline = api_get("actions/runs/" + str(OFFLINE_RUN))
    validate_run(offline, run_id=OFFLINE_RUN, commit=OFFLINE_COMMIT,
                 path=".github/workflows/offline-package-check.yml",
                 event="workflow_dispatch")
    validate_artifact(
        api_get("actions/runs/" + str(BUILD_RUN) + "/artifacts?per_page=100"),
        artifact_id=BUILD_ARTIFACT_ID, name="LocalAiPhotoEditor-windows-x64-alpha",
        digest=BUILD_DIGEST, size=BUILD_ARTIFACT_SIZE,
    )
    validate_artifact(
        api_get("actions/runs/" + str(OFFLINE_RUN) + "/artifacts?per_page=100"),
        artifact_id=OFFLINE_ARTIFACT_ID,
        name="offline-package-check-" + str(OFFLINE_RUN),
        digest=OFFLINE_DIGEST,
    )
    print("Both successful workflow runs and their exact artifacts are confirmed.")


def verify_offline_evidence(evidence_dir: Path) -> None:
    source = read_json(evidence_dir / "source-artifact.json")
    report = read_json(evidence_dir / "offline-package-result.json")
    require(source.get("run_id") == BUILD_RUN, "Offline test used another source run")
    require(source.get("head_sha") == BUILD_COMMIT, "Offline test used another source commit")
    require(source.get("artifact_id") == BUILD_ARTIFACT_ID, "Offline test used another artifact")
    require(source.get("artifact_digest") == BUILD_DIGEST, "Offline source digest mismatch")
    require(report.get("status") == "ok", "Offline package runtime was not successful")
    require(report.get("offline_enforcement_confirmed") is True,
            "An effective offline block was not confirmed")
    require(report.get("rule_removal_verified") is True, "Firewall cleanup unconfirmed")
    require(report.get("executable_sha256") == EXE_SHA256, "Offline-tested EXE differs")
    checks = report.get("smoke_checks", [])
    require(isinstance(checks, list) and len(checks) == 2,
            "Expected exactly two offline checks")
    by_name = {item.get("name"): item for item in checks if isinstance(item, dict)}
    require(set(by_name) == {"worker", "gui"}, "Missing offline worker or GUI check")
    require(all(item.get("status") == "ok" and item.get("exit_code") == 0
                for item in by_name.values()), "Offline worker or GUI failed")
    require(by_name["worker"].get("same_executable_worker_confirmed") is True,
            "Worker did not use the firewall-blocked executable")


def verify_package(package_dir: Path) -> None:
    require(package_dir.is_dir(), "Application directory is missing")
    exe = package_dir / "LocalAiPhotoEditor.exe"
    model = package_dir / "local_ai_photo_editor" / "models" / "u2netp.onnx"
    require(exe.is_file() and sha256(exe) == EXE_SHA256, "Executable hash mismatch")
    require(model.is_file() and sha256(model) == MODEL_SHA256, "Bundled model mismatch")
    info = read_json(package_dir / "build-info.json")
    require(info.get("commit") == BUILD_COMMIT, "Bundled application built from another commit")
    require(info.get("version") == "0.1.0a1", "Unexpected application version")
    require(info.get("model_sha256") == MODEL_SHA256, "Build model identity mismatch")
    require(info.get("provider") == "CPUExecutionProvider", "Unexpected execution provider")
    for path in package_dir.rglob("*"):
        require(not path.is_symlink(), "Package contains a symbolic link: " + str(path))
    for name in ("THIRD_PARTY_NOTICES.md", "LICENSE", "START_HERE.txt",
                 "build-resolved.txt"):
        require((package_dir / name).is_file(), "Missing distributable file: " + name)
    require((package_dir / "third-party-licenses").is_dir(),
            "Missing third-party license inventory")


def zip_release(directory: Path, output_file: Path) -> None:
    with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=7, allowZip64=True) as archive:
        files = sorted(p for p in directory.rglob("*") if p.is_file())
        require(len(files) > 20, "Suspiciously incomplete standalone directory")
        for path in files:
            archive.write(path, arcname="LocalAiPhotoEditor/" + path.relative_to(directory).as_posix())
    with zipfile.ZipFile(output_file, "r") as archive:
        require(archive.testzip() is None, "Created ZIP contains a damaged member")
        require("LocalAiPhotoEditor/LocalAiPhotoEditor.exe" in archive.namelist(),
                "Archive is missing the executable")


def assemble(application_dir: Path, evidence_dir: Path, output_dir: Path) -> None:
    require(not output_dir.exists(), "Refusing to replace an existing release directory")
    verify_offline_evidence(evidence_dir)
    verify_package(application_dir)
    root = Path(__file__).resolve().parents[1]
    output_dir.mkdir(parents=True)
    stage = output_dir / "staging" / "LocalAiPhotoEditor"
    shutil.copytree(application_dir, stage)
    # The binary is from the tested build. Documentation follows the release commit.
    shutil.rmtree(stage / "docs", ignore_errors=True)
    shutil.copytree(root / "docs", stage / "docs")
    for source, dest in [
        (root / "LICENSE", stage / "LICENSE"),
        (root / "THIRD_PARTY_NOTICES.md", stage / "THIRD_PARTY_NOTICES.md"),
        (root / "packaging" / "START_HERE.txt", stage / "START_HERE.txt"),
        (root / "README.md", stage / "README.md"),
    ]:
        shutil.copy2(source, dest)
    provenance = {
        "version": TAG,
        "application_build_commit": BUILD_COMMIT,
        "documentation_commit": os.environ.get("GITHUB_SHA"),
        "verified_build_run": BUILD_RUN,
        "source_artifact_id": BUILD_ARTIFACT_ID,
        "source_artifact_digest": BUILD_DIGEST,
        "offline_check_run": OFFLINE_RUN,
        "offline_artifact_digest": OFFLINE_DIGEST,
        "exe_sha256": EXE_SHA256,
        "model_sha256": MODEL_SHA256,
        "package_status": "unsigned-test-alpha",
        "acceptance_limit": "Windows Server 2022 checks; clean Windows 11 acceptance outstanding",
    }
    require(bool(provenance["documentation_commit"]), "GITHUB_SHA not provided")
    (stage / "distribution-info.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    out = output_dir / ARCHIVE_NAME
    zip_release(stage, out)
    digest = sha256(out)
    (output_dir / "SHA256SUMS.txt").write_text(
        digest + "  " + ARCHIVE_NAME + "\n", encoding="utf-8"
    )
    shutil.rmtree(output_dir / "staging")
    print("Built " + str(out) + " sha256=" + digest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify-remote")
    assemble_cmd = commands.add_parser("assemble")
    assemble_cmd.add_argument("--application", type=Path, required=True)
    assemble_cmd.add_argument("--evidence", type=Path, required=True)
    assemble_cmd.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "verify-remote":
        verify_remote()
    else:
        assemble(arguments.application, arguments.evidence, arguments.output)


if __name__ == "__main__":
    main()
