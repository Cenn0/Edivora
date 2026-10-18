"""Bounded, local, explicit portable folders for Edivora audio/video projects.

No archive extraction or network access. A new directory contains a regular
.edap/.edvp manifest and unique media copies with relative paths. The original
project and all media sources remain untouched.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Callable

from .media import validate_source
from .media_project import (
    MediaSequence, PROJECT_EXTENSIONS, fingerprint, load_media_project,
    save_media_project,
)

MAX_PORTABLE_BYTES = 2 * 1024**3
_BLOCK_BYTES = 1024 * 1024


def _target_directory(destination: str | Path) -> Path:
    raw = str(destination)
    if raw.startswith(("\\\\", "//")) or "://" in raw or "\x00" in raw:
        raise ValueError("Portable folders must be on an explicitly selected local drive.")
    if any(ord(c) < 32 for c in raw) or len(raw) > 4096:
        raise ValueError("Invalid portable destination.")
    target = Path(destination).expanduser().absolute()
    if target.is_symlink() or target.exists():
        raise FileExistsError("Portable destination must not already exist.")
    if not target.name or len(target.name) > 128:
        raise ValueError("Invalid portable folder name.")
    if not target.parent.is_dir():
        raise ValueError("Portable destination parent does not exist.")
    return target


def _copy_verified(source: Path, destination: Path, *,
                   cancelled: Callable[[], bool] | None) -> None:
    """Copy exact source bytes and re-read source to detect mid-copy mutations."""
    before = source.stat()
    sampled_before = fingerprint(source)
    written_hash = hashlib.sha256()
    copied_bytes = 0
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        while True:
            if cancelled is not None and cancelled():
                raise InterruptedError("Portable export cancelled.")
            block = incoming.read(_BLOCK_BYTES)
            if not block:
                break
            copied_bytes += len(block)
            if copied_bytes > before.st_size:
                raise ValueError("Source grew while creating portable media.")
            outgoing.write(block)
            written_hash.update(block)
        outgoing.flush()
        os.fsync(outgoing.fileno())

    # The entire source is read once more, not just its beginning and end.
    source_hash = hashlib.sha256()
    with source.open("rb") as incoming:
        while True:
            if cancelled is not None and cancelled():
                raise InterruptedError("Portable export cancelled.")
            block = incoming.read(_BLOCK_BYTES)
            if not block:
                break
            source_hash.update(block)
    after = source.stat()
    if (before.st_size != destination.stat().st_size
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or sampled_before != fingerprint(source)
            or written_hash.digest() != source_hash.digest()):
        raise ValueError("A source file changed while creating the portable project.")


def create_portable_media_folder(
    sequence: MediaSequence, destination: str | Path, *,
    max_total_bytes: int = MAX_PORTABLE_BYTES,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Publish a new project folder only after copies and manifest all validate.

    The destination is reserved with an exclusive mkdir; its manifest is
    published last after verified staging. Errors/cancellation clean only
    exporter-owned files. No existing project or source is replaced. Imported folders are opened normally through the existing
    strict media-project loader; there is no ZIP extraction step.
    """
    seq = sequence.validated()
    target = _target_directory(destination)
    if (type(max_total_bytes) is not int or not 1 <= max_total_bytes <= MAX_PORTABLE_BYTES):
        raise ValueError("Portable size quota must be a positive bounded integer.")

    unique_sources: dict[Path, Path] = {}
    originals: list[Path] = []
    total_bytes = 0
    for clip in seq.clips:
        source = validate_source(clip.source, seq.kind).resolve(strict=True)
        originals.append(source)
        if source not in unique_sources:
            total_bytes += source.stat().st_size
            if total_bytes > max_total_bytes:
                raise ValueError("Portable media exceeds the selected size quota.")
            unique_sources[source] = source

    with tempfile.TemporaryDirectory(prefix=".edivora-portable-", dir=target.parent) as staging:
        root = Path(staging)
        media_dir = root / "media"
        media_dir.mkdir()
        copied: dict[Path, Path] = {}
        for index, source in enumerate(unique_sources, start=1):
            if cancelled is not None and cancelled():
                raise InterruptedError("Portable export cancelled.")
            dest = media_dir / f"{index:02d}{source.suffix.lower()}"
            _copy_verified(source, dest, cancelled=cancelled)
            copied[source] = dest
        portable = replace(
            seq, clips=tuple(replace(clip, source=copied[src])
                             for clip, src in zip(seq.clips, originals)),
        )
        manifest = root / f"project{PROJECT_EXTENSIONS[seq.kind]}"
        save_media_project(portable, manifest)
        if load_media_project(manifest) != portable:
            raise ValueError("Portable project validation failed.")
        if cancelled is not None and cancelled():
            raise InterruptedError("Portable export cancelled.")
        # Reserving the destination with exclusive mkdir is critical:
        # os.rename(staging, destination) could overwrite an empty directory
        # on POSIX after a race, despite an earlier exists() check.
        _target_directory(target)
        target.mkdir(mode=0o700, exist_ok=False)
        published_media = target / "media"
        published_project = target / manifest.name
        try:
            # Keep the manifest as the last publication step. Without the
            # manifest, an interrupted folder is not a loadable project.
            media_dir.rename(published_media)
            manifest.rename(published_project)
        except BaseException:
            # Remove only files created by this exporter; never delete
            # unrelated files that someone placed in the target meanwhile.
            published_project.unlink(missing_ok=True)
            if published_media.is_dir() and not published_media.is_symlink():
                for source_copy in copied.values():
                    (published_media / source_copy.name).unlink(missing_ok=True)
                try:
                    published_media.rmdir()
                except OSError:
                    pass
            try:
                target.rmdir()
            except OSError:
                pass
            raise
    return target / f"project{PROJECT_EXTENSIONS[seq.kind]}"
