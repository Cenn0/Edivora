"""Local video-frame foreground cutout, using the already bundled U2NETP.

This is **one still frame** from the currently selected video, not a temporal
video AI filter. Work runs in a separate cancellable process and never writes
to the source video file or contacts a remote service.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

from PIL import Image

from ..core.media import ffmpeg_executable, protects_source, validate_source
from .background import remove_background


def extract_ai_frame(source: Path, at_ms: int, destination: Path,
                     *, ffmpeg: str | None = None) -> Path:
    source = validate_source(source, "video")
    if type(at_ms) is not int or at_ms < 0 or at_ms > 2 * 60 * 60 * 1000:
        raise ValueError("Invalid frame timestamp.")
    destination = Path(destination).expanduser().absolute()
    if (destination.suffix.lower() != ".png" or not destination.parent.is_dir()
            or destination.is_symlink() or not protects_source(source, destination)):
        raise ValueError("Choose a regular PNG destination different from the source.")
    with tempfile.TemporaryDirectory(prefix="edivora-frame-") as folder:
        still = Path(folder) / "frame.png"
        args = [
            ffmpeg or ffmpeg_executable(),
            "-nostdin", "-hide_banner", "-loglevel", "error",
            "-protocol_whitelist", "file,pipe,data",
            "-ss", f"{at_ms / 1000:.3f}", "-i", str(source),
            "-frames:v", "1", "-an", "-sn", "-dn",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease",
            "-y", str(still),
        ]
        subprocess.run(args, check=True, timeout=45,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        with Image.open(still) as picture:
            if not 1 <= picture.width * picture.height <= 2_000_000:
                raise ValueError("Selected frame exceeds the local AI bounds.")
            picture.load()
            output = remove_background(picture.convert("RGBA"))
        temporary = destination.parent / f".edivora-ai-{uuid.uuid4().hex}.png"
        try:
            output.save(temporary, format="PNG")
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise RuntimeError("AI image export failed.")
            if destination.is_symlink() or not protects_source(source, destination):
                raise ValueError("Output path changed while processing.")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def frame_worker(job_directory: Path, executable: str | None = None) -> int:
    folder = Path(job_directory)
    reply = folder / "result.json"
    try:
        request = folder / "request.json"
        if request.stat().st_size > 8192:
            raise ValueError("Oversized video AI request.")
        data = json.loads(request.read_text("utf-8"))
        if type(data) is not dict or set(data) != {"source", "at_ms", "destination"}:
            raise ValueError("Invalid video AI request.")
        path = extract_ai_frame(
            Path(data["source"]), data["at_ms"], Path(data["destination"]),
            ffmpeg=ffmpeg_executable(executable),
        )
        reply.write_text(json.dumps({"ok": True, "name": path.name}), encoding="utf-8")
        return 0
    except Exception as exc:
        reply.write_text(json.dumps({
            "ok": False, "message": f"{type(exc).__name__}: {str(exc)[:250]}",
        }), encoding="utf-8")
        return 1
