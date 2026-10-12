"""Create a complete portable Windows alpha with the pinned offline model."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from collect_licenses import collect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_ai_photo_editor.ai.models import MODEL_SHA256, model_path, verified_model_bytes  # noqa: E402


def main() -> int:
    if sys.platform != "win32" or platform.machine().upper() not in ("AMD64", "X86_64"):
        raise SystemExit("Build this package on 64-bit Windows with 64-bit Python 3.12.")
    verified_model_bytes()
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    notices = build / "third-party-licenses"
    collect(notices)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    command = [
        sys.executable, "-m", "nuitka", "--mode=standalone",
        "--enable-plugin=pyside6", "--include-qt-plugins=platforms,imageformats",
        "--include-package=local_ai_photo_editor", "--include-package=onnxruntime.capi",
        "--include-package-data=onnxruntime", "--assume-yes-for-downloads",
        "--msvc=latest", "--windows-console-mode=disable",
        "--output-filename=LocalAiPhotoEditor.exe", f"--output-dir={build}",
        f"--include-data-dir={model_path().parent}=local_ai_photo_editor/models",
        f"--report={build / 'nuitka-report.xml'}", "--jobs=2", str(ROOT / "main.py"),
    ]
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    compiled = build / "main.dist"
    if not (compiled / "LocalAiPhotoEditor.exe").is_file():
        raise RuntimeError("Nuitka did not produce the expected standalone executable.")
    verified_model_bytes(compiled / "local_ai_photo_editor" / "models" / model_path().name)
    destination = ROOT / "dist" / "LocalAiPhotoEditor"
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(compiled, destination)
    shutil.copytree(notices, destination / "third-party-licenses")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, destination / name)
    shutil.copy2(ROOT / "packaging" / "START_HERE.txt", destination / "START_HERE.txt")
    shutil.copytree(ROOT / "docs", destination / "docs")
    (destination / "build-info.json").write_text(json.dumps({
        "version": "0.1.0a1",
        "commit": os.environ.get("GITHUB_SHA", "local-build"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "model_sha256": MODEL_SHA256,
        "provider": "CPUExecutionProvider",
        "release_channel": "unsigned-development-alpha",
    }, indent=2), encoding="utf-8")
    with (destination / "build-resolved.txt").open("w", encoding="utf-8") as stream:
        subprocess.run([sys.executable, "-m", "pip", "freeze"], stdout=stream, check=True)
    # The workflow verifies the copied executable before this directory is uploaded.
    executable = destination / "LocalAiPhotoEditor.exe"
    print(f"Prepared {executable.name}; SHA-256 {hashlib.sha256(executable.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
