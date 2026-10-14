"""Validated, local-only FFmpeg commands for the beginner media editors.

No Qt, networking, shell, automatic downloads or media writes occur here.
The UI executes commands asynchronously and commits a completed temporary export.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import uuid

VIDEO_INPUTS = frozenset({".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"})
AUDIO_INPUTS = frozenset({".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"})
AUDIO_OUTPUTS = frozenset({".wav", ".mp3"})
MAX_SOURCE_BYTES = 20 * 1024**3
MIN_SELECTION_MS = 100


def ffmpeg_executable(compiled_executable: str | Path | None = None) -> str:
    """Use the copied, fixed bundled executable in standalone builds.

    Source checkouts use the pinned imageio-ffmpeg wheel; no runtime download.
    An installed binary cannot silently fall back to a different system ffmpeg.
    """
    if compiled_executable is not None or getattr(sys, "frozen", False):
        root = Path(compiled_executable or sys.executable).resolve().parent
        path = root / "media-tools" / "ffmpeg.exe"
        if not path.is_file():
            raise FileNotFoundError(f"Bundled media engine is missing: {path}")
        return str(path)
    import imageio_ffmpeg
    binary = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"FFmpeg is unavailable: {binary}")
    return str(binary)


def validate_source(path: str | Path, kind: str) -> Path:
    if kind not in {"video", "audio"}:
        raise ValueError("Unknown editor kind.")
    file = Path(path).expanduser().resolve(strict=True)
    if not file.is_file():
        raise ValueError("The selected input is not a regular file.")
    if file.suffix.lower() not in (VIDEO_INPUTS if kind == "video" else AUDIO_INPUTS):
        raise ValueError("This media file extension is not supported by the MVP.")
    size = file.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError("The media file is empty or exceeds the 20 GiB MVP limit.")
    return file


def protects_source(source: Path, destination: Path) -> bool:
    """Protect aliases, existing hardlinks, and paths through symlink parents."""
    if source.resolve() == destination.resolve():
        return False
    if destination.is_symlink():
        return False
    if destination.exists() and os.path.samefile(source, destination):
        return False
    return True


@dataclass(frozen=True)
class MediaExport:
    kind: str
    source: Path
    destination: Path
    duration_ms: int
    start_ms: int
    end_ms: int
    volume_percent: int = 100
    mute: bool = False
    normalize: bool = False
    fade_in_ms: int = 0
    fade_out_ms: int = 0

    def validated(self) -> "MediaExport":
        source = validate_source(self.source, self.kind)
        output = Path(self.destination).expanduser().absolute()
        if self.kind == "video":
            suffixes = {".mp4"}
        else:
            suffixes = AUDIO_OUTPUTS
        if output.suffix.lower() not in suffixes:
            raise ValueError("Choose a supported output extension.")
        if not output.parent.is_dir():
            raise ValueError("Output directory does not exist.")
        if not protects_source(source, output):
            raise ValueError("Source files cannot be overwritten, even through an alias.")
        if self.duration_ms <= 0 or self.end_ms > self.duration_ms:
            raise ValueError("Media duration has not been determined.")
        if not (0 <= self.start_ms < self.end_ms):
            raise ValueError("Choose an end later than the start.")
        if self.end_ms - self.start_ms < MIN_SELECTION_MS:
            raise ValueError("The selection must be at least 0.1 seconds.")
        if not 0 <= self.volume_percent <= 200:
            raise ValueError("Volume must be between 0 and 200 percent.")
        if self.fade_in_ms < 0 or self.fade_out_ms < 0:
            raise ValueError("Fade lengths cannot be negative.")
        if self.fade_in_ms + self.fade_out_ms > self.end_ms - self.start_ms:
            raise ValueError("Fade lengths exceed the selected duration.")
        if self.kind == "video" and (self.normalize or self.fade_in_ms or self.fade_out_ms):
            raise ValueError("Audio-only effects are not available in the video MVP.")
        if self.kind == "audio" and self.mute:
            raise ValueError("Mute is not an audio-export operation.")
        return self

    def temp_output(self) -> Path:
        self.validated()
        return self.destination.parent / (
            f".edivora-{uuid.uuid4().hex}{self.destination.suffix.lower()}"
        )

    def ffmpeg_arguments(self, temporary_output: Path) -> list[str]:
        """Return argv only; no shell invocation or user-controlled filter syntax."""
        self.validated()
        temporary_output = Path(temporary_output)
        if temporary_output.parent.resolve() != self.destination.parent.resolve():
            raise ValueError("Temporary export must share the output directory.")
        if temporary_output.suffix.lower() != self.destination.suffix.lower():
            raise ValueError("Temporary export suffix must match destination.")
        if not protects_source(self.source.resolve(), temporary_output):
            raise ValueError("Temporary export must not overwrite input.")
        length_ms = self.end_ms - self.start_ms
        args = [
            "-nostdin", "-hide_banner", "-loglevel", "error", "-nostats",
            "-protocol_whitelist", "file,pipe,data",
            "-ss", f"{self.start_ms / 1000:.3f}",
            "-i", str(self.source.resolve()),
            "-t", f"{length_ms / 1000:.3f}",
        ]
        if self.kind == "video":
            args += ["-map", "0:v:0"]
            if not self.mute:
                args += ["-map", "0:a?"]
            args += ["-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1"]
            # MPEG-4 Part 2/AAC work without assuming a GPL-only H.264 encoder.
            # Even dimensions and yuv420p aid playback on common devices.
            args += [
                "-vf", "scale=ceil(iw/2)*2:ceil(ih/2)*2",
                "-c:v", "mpeg4", "-q:v", "4", "-pix_fmt", "yuv420p",
            ]
            if self.mute:
                args += ["-an"]
            else:
                if self.volume_percent != 100:
                    args += ["-af", f"volume={self.volume_percent / 100:.2f}"]
                args += ["-c:a", "aac", "-b:a", "160k"]
            args += ["-movflags", "+faststart"]
        else:
            args += [
                "-map", "0:a:0", "-vn", "-sn", "-dn",
                "-map_metadata", "-1", "-map_chapters", "-1",
            ]
            filters = []
            if self.volume_percent != 100:
                filters.append(f"volume={self.volume_percent / 100:.2f}")
            if self.normalize:
                filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")
            if self.fade_in_ms:
                filters.append(f"afade=t=in:st=0:d={self.fade_in_ms / 1000:.3f}")
            if self.fade_out_ms:
                fade_start = (length_ms - self.fade_out_ms) / 1000
                filters.append(f"afade=t=out:st={fade_start:.3f}:d={self.fade_out_ms / 1000:.3f}")
            if filters:
                args += ["-af", ",".join(filters)]
            if self.destination.suffix.lower() == ".mp3":
                args += ["-c:a", "libmp3lame", "-b:a", "192k"]
            else:
                args += ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
        return [*args, "-y", str(temporary_output)]


def commit_export(export: MediaExport, temporary_output: Path) -> None:
    """Atomically install a non-empty successful export; never replace the source."""
    export.validated()
    temporary_output = Path(temporary_output)
    if temporary_output.is_symlink() or not temporary_output.is_file():
        raise ValueError("Export did not produce a regular media file.")
    if temporary_output.stat().st_size == 0:
        raise ValueError("Export produced an empty file.")
    if temporary_output.resolve().parent != export.destination.parent.resolve():
        raise ValueError("Export is outside the chosen output directory.")
    if not protects_source(export.source.resolve(), export.destination):
        raise ValueError("Source was changed during export.")
    os.replace(temporary_output, export.destination)
