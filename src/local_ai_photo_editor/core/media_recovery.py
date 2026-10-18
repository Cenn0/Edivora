"""Strict local recovery checkpoints for previously saved media projects.

Checkpoints are atomically written .edvp/.edap sidecars, never replacing the
user's authoritative saved project; restored versions require explicit consent.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .media_project import (
    PROJECT_EXTENSIONS, MediaSequence, load_media_project, save_media_project,
)


@dataclass(frozen=True)
class RecoveryCandidate:
    original: Path
    checkpoint: Path
    original_mtime_ns: int
    checkpoint_mtime_ns: int


def _paths(project_file: str | Path) -> tuple[Path, Path]:
    original = Path(project_file).expanduser().absolute()
    if original.suffix.lower() not in PROJECT_EXTENSIONS.values():
        raise ValueError("Not an Edivora media project.")
    if original.is_symlink():
        raise ValueError("Cannot create recovery for a symlink project.")
    if not original.is_file():
        raise FileNotFoundError("Saved project does not exist.")
    original = original.resolve(strict=True)
    sidecar = original.with_name(
        f".{original.stem}.edivora-recovery{original.suffix.lower()}"
    )
    if len(sidecar.name) > 245:
        raise ValueError("Recovery checkpoint filename is too long.")
    if sidecar.is_symlink():
        raise ValueError("Recovery checkpoint must not be a symlink.")
    if sidecar.exists() and os.path.samefile(original, sidecar):
        raise ValueError("Recovery checkpoint must never alias the saved project.")
    if sidecar.exists() and not sidecar.is_file():
        raise ValueError("Recovery checkpoint must be a regular file.")
    return original, sidecar



def _verify_sidecar(original: Path, sidecar: Path) -> None:
    """Fail closed for unrelated or corrupt files at the reserved checkpoint name.

    Even a hidden filename is not proof that the file belongs to Edivora.
    A damaged checkpoint must be removed manually, never silently clobbered.
    """
    if not sidecar.exists():
        return
    try:
        checkpoint = load_media_project(sidecar)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(
            "Existing recovery checkpoint is invalid; move it aside manually."
        ) from exc
    expected = "audio" if original.suffix.lower() == ".edap" else "video"
    if checkpoint.kind != expected:
        raise ValueError("Recovery checkpoint has the wrong media kind.")



def write_recovery(sequence: MediaSequence, project_file: str | Path) -> Path:
    """Write a checkpoint after the first explicit save."""
    original, sidecar = _paths(project_file)
    if original.suffix.lower() != PROJECT_EXTENSIONS[sequence.kind]:
        raise ValueError("Recovery project kind mismatch.")
    _verify_sidecar(original, sidecar)
    save_media_project(sequence, sidecar)
    return sidecar


def candidate_recovery(project_file: str | Path) -> RecoveryCandidate | None:
    """Return a newer, *valid* checkpoint without applying it."""
    original, sidecar = _paths(project_file)
    if not sidecar.is_file():
        return None
    saved = original.stat().st_mtime_ns
    recovery = sidecar.stat().st_mtime_ns
    if recovery <= saved:
        return None
    recovered = load_media_project(sidecar)
    if recovered.kind != ("audio" if original.suffix.lower() == ".edap" else "video"):
        raise ValueError("Recovery checkpoint has the wrong media kind.")
    return RecoveryCandidate(original, sidecar, saved, recovery)


def clear_recovery(project_file: str | Path) -> None:
    """Remove only the exact derived sidecar, refusing aliases/symlinks."""
    original, sidecar = _paths(project_file)
    _verify_sidecar(original, sidecar)
    sidecar.unlink(missing_ok=True)
