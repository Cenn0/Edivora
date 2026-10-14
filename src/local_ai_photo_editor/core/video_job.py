"""Strict restoration-job protocol and atomic installation of derived clips."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from .media import MIN_SELECTION_MS, protects_source, validate_source
from .media_project import _allowed_path, _unique_pairs
from .video_adjustments import VideoAdjustments

MAX_AI_DURATION_MS = 30_000
MAX_JOB_BYTES = 16_384
MAX_RESULT_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True)
class VideoJob:
    source: Path
    start_ms: int
    end_ms: int
    at_ms: int
    adjustments: VideoAdjustments
    strength: int = 0
    mode: str = "preview"

    def validated(self) -> "VideoJob":
        validate_source(_allowed_path(Path(self.source)), "video")
        for value in (self.start_ms, self.end_ms, self.at_ms, self.strength):
            if type(value) is not int:
                raise ValueError("Video request numbers must be integers.")
        if (self.mode not in ("preview", "render") or not 0 <= self.strength <= 100
                or not 0 <= self.start_ms < self.end_ms <= 7_200_000
                or self.end_ms - self.start_ms < MIN_SELECTION_MS
                or not self.start_ms <= self.at_ms < self.end_ms):
            raise ValueError("Invalid video request range, mode, or strength.")
        if type(self.adjustments) is not VideoAdjustments:
            raise ValueError("Invalid video adjustments.")
        self.adjustments.validated()
        if self.mode == "render" and (self.strength == 0
                or self.end_ms - self.start_ms > MAX_AI_DURATION_MS):
            raise ValueError("Neural rendering requires a selected range of at most 30 seconds.")
        return self

    def to_dict(self) -> dict:
        self.validated()
        return {"source": str(self.source.resolve()), "start_ms": self.start_ms,
                "end_ms": self.end_ms, "at_ms": self.at_ms,
                "adjustments": self.adjustments.to_dict(),
                "strength": self.strength, "mode": self.mode}

    @classmethod
    def read(cls, folder: Path) -> "VideoJob":
        path = folder / "request.json"
        if folder.is_symlink() or path.is_symlink() or not path.is_file():
            raise ValueError("Invalid restoration request location.")
        with path.open("rb") as stream:
            raw = stream.read(MAX_JOB_BYTES + 1)
        if len(raw) > MAX_JOB_BYTES:
            raise ValueError("Oversized restoration request.")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
        fields = {"source", "start_ms", "end_ms", "at_ms", "adjustments", "strength", "mode"}
        if type(data) is not dict or set(data) != fields or type(data["source"]) is not str:
            raise ValueError("Unknown or missing restoration request fields.")
        return cls(Path(data["source"]), data["start_ms"], data["end_ms"], data["at_ms"],
                   VideoAdjustments.from_dict(data["adjustments"]),
                   data["strength"], data["mode"]).validated()


def validate_destination(destination: Path, protected: tuple[Path, ...]) -> Path:
    destination = _allowed_path(Path(destination).expanduser().absolute())
    if (destination.suffix.lower() != ".mp4" or not destination.parent.is_dir()
            or destination.is_symlink() or (destination.exists() and not destination.is_file())
            or any(not protects_source(source, destination) for source in protected)):
        raise ValueError("Choose a separate local MP4; source files and projects are protected.")
    return destination


def install_restored_clip(temporary: Path, destination: Path,
                          protected: tuple[Path, ...]) -> None:
    destination = validate_destination(destination, protected)
    if (temporary.is_symlink() or not temporary.is_file()
            or not 1 <= temporary.stat().st_size <= MAX_RESULT_BYTES
            or temporary.parent.parent.resolve() != destination.parent.resolve()
            or any(not protects_source(source, temporary) for source in protected)):
        raise ValueError("Invalid restoration output or staging directory.")
    # The job directory is created beside the destination, including on Windows:
    # a cross-volume move cannot accidentally turn this into a non-atomic copy.
    with temporary.open("rb") as stream:
        os.fsync(stream.fileno())
    os.replace(temporary, destination)
