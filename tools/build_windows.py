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
from brand_assets import build_windows_icon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_ai_photo_editor.ai.models import MODEL_SHA256, model_path, verified_model_bytes  # noqa: E402
from local_ai_photo_editor.ai.voice import (  # noqa: E402
    VOICE_MODEL_SHA256, voice_model_path, verified_voice_model,
)


def main() -> int:
    if sys.platform != "win32" or platform.machine().upper() not in ("AMD64", "X86_64"):
        raise SystemExit("Build this package on 64-bit Windows with 64-bit Python 3.12.")
    verified_model_bytes()
    verified_voice_model()
    import imageio_ffmpeg
    ffmpeg_binary = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    if not ffmpeg_binary.is_file():
        raise RuntimeError("The pinned FFmpeg wheel does not contain a local executable.")
    codec_listing = subprocess.check_output(
        [str(ffmpeg_binary), "-hide_banner", "-encoders"],
        text=True, timeout=20,
    )
    for codec in ("mpeg4", "aac", "pcm_s16le", "libmp3lame"):
        if not any(line.split()[1:2] == [codec] for line in codec_listing.splitlines()):
            raise RuntimeError(f"Bundled FFmpeg is missing the MVP encoder: {codec}")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    notices = build / "third-party-licenses"
    collect(notices)
    icon_file = build_windows_icon(
        ROOT / "src" / "local_ai_photo_editor" / "assets" / "edivora-mark.svg",
        build / "branding",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    command = [
        sys.executable, "-m", "nuitka", "--mode=standalone",
        "--enable-plugin=pyside6", "--include-qt-plugins=platforms,imageformats,multimedia",
        "--include-module=PySide6.QtSvg",
        "--include-package=local_ai_photo_editor", "--include-package=onnxruntime.capi",
        "--include-package-data=onnxruntime", "--assume-yes-for-downloads",
        "--msvc=latest", "--lto=no", "--windows-console-mode=disable",
        "--output-filename=LocalAiPhotoEditor.exe", f"--output-dir={build}",
        f"--windows-icon-from-ico={icon_file}",
        f"--include-data-dir={ROOT / 'src' / 'local_ai_photo_editor' / 'assets'}=local_ai_photo_editor/assets",
        f"--include-data-dir={model_path().parent}=local_ai_photo_editor/models",
        f"--report={build / 'nuitka-report.xml'}", "--jobs=2", str(ROOT / "main.py"),
    ]
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    compiled = build / "main.dist"
    if not (compiled / "LocalAiPhotoEditor.exe").is_file():
        raise RuntimeError("Nuitka did not produce the expected standalone executable.")
    verified_model_bytes(compiled / "local_ai_photo_editor" / "models" / model_path().name)
    verified_voice_model(compiled / "local_ai_photo_editor" / "models" / voice_model_path().name)
    destination = ROOT / "dist" / "LocalAiPhotoEditor"
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(compiled, destination)
    shutil.copytree(notices, destination / "third-party-licenses")
    media_tools = destination / "media-tools"
    media_tools.mkdir()
    shutil.copy2(ffmpeg_binary, media_tools / "ffmpeg.exe")
    shutil.copy2(ROOT / "docs" / "qt-licenses" / "GPL-3.0-only.txt",
                 media_tools / "GPL-3.0-license.txt")
    # This FFmpeg command-line binary is distinct from Qt's playback backend.
    subprocess.run([str(media_tools / "ffmpeg.exe"), "-version"], check=True, timeout=20,
                   stdout=subprocess.DEVNULL)

    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, destination / name)
    shutil.copy2(ROOT / "packaging" / "START_HERE.txt", destination / "START_HERE.txt")
    shutil.copytree(ROOT / "docs", destination / "docs")
    (destination / "build-info.json").write_text(json.dumps({
        "version": "0.3.0a1",
        "commit": os.environ.get("GITHUB_SHA", "local-build"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "model_sha256": MODEL_SHA256,
        "voice_model_sha256": VOICE_MODEL_SHA256,
        "media_project_formats": [".edvp", ".edap"],
        "ai_features": ["single-video-frame-U2NETP", "audio-Silero-VAD-v6.2.1"],
        "media_binary_sha256": hashlib.sha256(
            (destination / "media-tools" / "ffmpeg.exe").read_bytes()
        ).hexdigest(),
        "media_engine": "imageio-ffmpeg 0.6.0 standalone binary",
        "media_license_review": "Required before wider redistribution",

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
