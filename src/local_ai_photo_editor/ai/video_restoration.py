"""Bounded local preview and frame-by-frame DnCNN video denoising worker.

The preview is a real decoded frame. Rendering streams one RGB frame at a
 time, not an in-memory movie; conventional corrections precede neural denoising.
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image

from ..core.media import ffmpeg_executable
from ..core.video_adjustments import bounded_scale
from ..core.video_job import MAX_RESULT_BYTES, VideoJob
from .process_owner import ProcessOwner
from .restoration import Denoiser

FPS = 30
MAX_FRAME_BYTES = 4_000_000


def _base(executable: str) -> list[str]:
    return [executable, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-threads", "2", "-filter_threads", "2", "-protocol_whitelist", "file,pipe,data"]


def _frame(owner: ProcessOwner, executable: str, request: VideoJob,
           *, corrected: bool, preview: bool) -> Image.Image:
    filters = [bounded_scale("hd", preview=preview)]
    if corrected:
        filters += request.adjustments.filters()
    child = owner.spawn(_base(executable) + [
        "-ss", f"{request.at_ms / 1000:.3f}", "-i", str(request.source.resolve()),
        "-frames:v", "1", "-an", "-sn", "-dn", "-vf", ",".join(filters),
        "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
    raw = child.stdout.read(MAX_FRAME_BYTES + 1)
    if len(raw) > MAX_FRAME_BYTES:
        raise ValueError("Preview exceeded the allowed frame size.")
    owner.wait(child)
    child.stdout.close()
    with Image.open(io.BytesIO(raw)) as image:
        if image.format != "PNG" or not 1 <= image.width * image.height <= 1280 * 720:
            raise ValueError("Invalid decoded video frame.")
        image.load()
        return image.convert("RGB")


def _read_frame(stream, count: int) -> bytes:
    output = bytearray()
    while len(output) < count:
        piece = stream.read(count - len(output))
        if not piece:
            break
        output.extend(piece)
    if output and len(output) != count:
        raise ValueError("Decoder returned an incomplete video frame.")
    return bytes(output)


def run_job(folder: Path, executable: str | None = None) -> dict:
    folder = Path(folder).resolve(strict=True)
    request = VideoJob.read(folder)
    # A job directory is private and fresh. Refuse aliases/pre-existing outputs.
    for name in ("before.png", "after.png", "output.mp4", "result.json"):
        if (folder / name).exists() or (folder / name).is_symlink():
            raise ValueError("Restoration job output already exists.")
    encoder = executable or ffmpeg_executable()
    owner = ProcessOwner(folder, 240 if request.mode == "preview" else 6 * 60 * 60)
    started = time.monotonic()
    try:
        denoiser = Denoiser() if request.strength else None
        if request.mode == "preview":
            before = _frame(owner, encoder, request, corrected=False, preview=True)
            after = _frame(owner, encoder, request, corrected=True, preview=True)
            if denoiser is not None:
                after = Image.fromarray(denoiser.apply(np.asarray(after), request.strength,
                                                      owner.cancelled.is_set))
            owner.check()
            before.save(folder / "before.png", "PNG")
            after.save(folder / "after.png", "PNG")
            return {"ok": True, "mode": "preview", "seconds": time.monotonic() - started}

        dimensions = _frame(owner, encoder, request, corrected=False, preview=False).size
        width, height = dimensions
        duration = (request.end_ms - request.start_ms) / 1000
        expected_frames = math.ceil(duration * FPS)
        chain = [f"fps={FPS}", f"scale={width}:{height}", "setsar=1"]
        chain += request.adjustments.filters()
        decoder = owner.spawn(_base(encoder) + [
            "-ss", f"{request.start_ms / 1000:.3f}", "-i", str(request.source.resolve()),
            "-t", f"{duration:.3f}", "-an", "-sn", "-dn", "-vf", ",".join(chain),
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
        output = folder / "output.mp4"
        writer = owner.spawn(_base(encoder) + [
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
            "-framerate", str(FPS), "-i", "pipe:0",
            "-protocol_whitelist", "file,pipe,data", "-ss", f"{request.start_ms / 1000:.3f}",
            "-i", str(request.source.resolve()), "-map", "0:v:0", "-map", "1:a:0?",
            "-af", f"apad=whole_dur={duration:.3f}", "-t", f"{duration:.3f}",
            "-c:v", "mpeg4", "-q:v", "2", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", "-map_metadata", "-1", "-map_chapters", "-1",
            "-fs", str(MAX_RESULT_BYTES), "-y", str(output)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        print(json.dumps({"children": [decoder.pid, writer.pid]}), flush=True)
        frames = 0
        while raw := _read_frame(decoder.stdout, width * height * 3):
            owner.check()
            if frames >= expected_frames + 1:
                raise ValueError("Decoded video exceeded the bounded frame budget.")
            rgb = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)
            restored = denoiser.apply(rgb, request.strength, owner.cancelled.is_set)
            writer.stdin.write(restored.tobytes())
            frames += 1
            print(json.dumps({"progress": min(99, round(frames * 100 / expected_frames))}), flush=True)
        decoder.stdout.close()
        owner.wait(decoder)
        writer.stdin.close()
        owner.wait(writer)
        if (not frames or abs(frames - expected_frames) > 1 or not output.is_file()
                or not 1 <= output.stat().st_size < MAX_RESULT_BYTES):
            raise ValueError("Restoration did not produce the expected bounded clip.")
        owner.check()
        return {"ok": True, "mode": "render", "frames": frames,
                "duration_ms": min(request.end_ms - request.start_ms, round(frames * 1000 / FPS)),
                "width": width, "height": height, "seconds": time.monotonic() - started}
    finally:
        owner.close()


def restoration_worker(folder: Path, executable: str | None = None) -> int:
    folder = Path(folder)
    try:
        # Validate before writing any response; a malicious existing response may
        # be a symlink. The UI creates private job directories itself.
        if (folder.is_symlink() or not folder.is_dir() or (folder / "result.json").exists()
                or (folder / "result.json").is_symlink()):
            return 1
        result = run_job(folder, ffmpeg_executable(executable))
        code = 0
    except Exception as exc:
        result = {"ok": False, "cancelled": isinstance(exc, InterruptedError),
                  "message": f"{type(exc).__name__}: {str(exc)[:600]}"}
        code = 1
    with (folder / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream)
    return code
