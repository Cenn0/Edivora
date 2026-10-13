"""Versioned, local-only, atomic photo project archives.

Projects contain the accepted pixels, imported original and the *retained*
undo/redo snapshots. They deliberately contain no original filesystem path,
EXIF, GPS or user account identifiers. They are not editable scene graphs.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import warnings
from zipfile import BadZipFile, ZIP_STORED, ZipFile

from PIL import Image

from .document import DEFAULT_HISTORY_BUDGET_BYTES, ImageDocument, _HistoryEntry
from .editing import MAX_IMAGE_PIXELS, _check_export_destination, _normalise_image, _validate_dimensions

FORMAT_ID = "local-ai-photo-editor-project"
PROJECT_VERSION = 1
MAX_PROJECT_BYTES = 768 * 1024 * 1024
MAX_FRAME_BYTES = 4 * MAX_IMAGE_PIXELS + 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SNAPSHOTS = 8192
MAX_LABELS = 100_000


def _checked_label(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 512:
        raise ValueError("Invalid project history label.")
    return value


def _checked_labels(values: object) -> list[str]:
    if not isinstance(values, list) or len(values) > MAX_LABELS:
        raise ValueError("Invalid project history.")
    return [_checked_label(value) for value in values]


def _write_frame(archive: ZipFile, filename: str, image: Image.Image, total: list[int]) -> dict:
    prepared = _normalise_image(image)
    buffer = BytesIO()
    prepared.save(buffer, format="PNG")
    payload = buffer.getvalue()
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError("Project frame is too large.")
    total[0] += len(payload)
    if total[0] > MAX_PROJECT_BYTES:
        raise ValueError("Project exceeds the supported archive size.")
    archive.writestr(filename, payload, compress_type=ZIP_STORED)
    return {
        "name": filename,
        "sha256": sha256(payload).hexdigest(),
        "width": prepared.width,
        "height": prepared.height,
        "mode": prepared.mode,
    }


def save_project(document: ImageDocument, path: str | Path) -> Path:
    """Write a complete, versioned snapshot beside the destination, then replace.

    Saving an archive does not modify the imported photo and never writes to
    an original path or its hardlink/symlink alias. On failure the existing
    project is unchanged. The working images remain in memory.
    """
    if not isinstance(document, ImageDocument):
        raise TypeError("A project needs an image document.")
    target = Path(path).expanduser().absolute()
    if target.suffix.lower() != ".laip":
        raise ValueError("Project files must use the .laip extension.")
    _check_export_destination(target, document.source_path)
    if document.history_budget_bytes > DEFAULT_HISTORY_BUDGET_BYTES:
        raise ValueError("This project uses an unsupported history budget.")
    if len(document._undo) + len(document._redo) > MAX_SNAPSHOTS:
        raise ValueError("The project has too many retained snapshots.")
    labels = _checked_labels(list(document.history))
    for entry in (*document._undo, *document._redo):
        _checked_label(entry.label)

    descriptor, temp_name = tempfile.mkstemp(
        prefix=".local-ai-photo-project-", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w+b") as stream:
            with ZipFile(stream, mode="w", compression=ZIP_STORED, allowZip64=True) as archive:
                total = [0]
                manifest = {
                    "format": FORMAT_ID,
                    "version": PROJECT_VERSION,
                    "history_budget_bytes": document.history_budget_bytes,
                    "history_labels": labels,
                    "original": _write_frame(archive, "frames/original.png", document.original, total),
                    "current": _write_frame(archive, "frames/current.png", document.current, total),
                    "undo": [
                        {
                            "label": entry.label,
                            "frame": _write_frame(archive, f"frames/undo-{i}.png", entry.image, total),
                        }
                        for i, entry in enumerate(document._undo)
                    ],
                    "redo": [
                        {
                            "label": entry.label,
                            "frame": _write_frame(archive, f"frames/redo-{i}.png", entry.image, total),
                        }
                        for i, entry in enumerate(document._redo)
                    ],
                }
                payload = json.dumps(
                    manifest, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
                if len(payload) > MAX_MANIFEST_BYTES or total[0] + len(payload) > MAX_PROJECT_BYTES:
                    raise ValueError("Project metadata is too large.")
                archive.writestr("manifest.json", payload, compress_type=ZIP_STORED)
            stream.flush()
            os.fsync(stream.fileno())
        _check_export_destination(target, document.source_path)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def _read_frame(archive: ZipFile, descriptor: object, filename: str) -> Image.Image:
    if (
        not isinstance(descriptor, dict)
        or set(descriptor) != {"name", "sha256", "width", "height", "mode"}
        or descriptor["name"] != filename
        or not isinstance(descriptor["sha256"], str)
        or len(descriptor["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in descriptor["sha256"])
        or descriptor["mode"] not in ("RGB", "RGBA")
    ):
        raise ValueError("Invalid project frame descriptor.")
    width, height = descriptor["width"], descriptor["height"]
    _validate_dimensions(width, height)
    info = archive.getinfo(filename)
    if info.file_size > MAX_FRAME_BYTES:
        raise ValueError("Project frame is too large.")
    payload = archive.read(filename)
    if sha256(payload).hexdigest() != descriptor["sha256"]:
        raise ValueError("Project frame checksum mismatch.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(payload)) as decoded:
            if decoded.format != "PNG" or decoded.size != (width, height) or decoded.mode != descriptor["mode"]:
                raise ValueError("Project frame has unexpected format or dimensions.")
            if decoded.info:
                raise ValueError("Project frames may not contain imported metadata.")
            decoded.load()
            return _normalise_image(decoded)


def _snapshot_descriptors(items: object, prefix: str) -> tuple[list[tuple[str, object, str]], set[str]]:
    if not isinstance(items, list) or len(items) > MAX_SNAPSHOTS:
        raise ValueError("Invalid project snapshots.")
    entries = []
    names = set()
    for index, entry in enumerate(items):
        if not isinstance(entry, dict) or set(entry) != {"label", "frame"}:
            raise ValueError("Invalid project snapshot entry.")
        label = _checked_label(entry["label"])
        name = f"frames/{prefix}-{index}.png"
        entries.append((label, entry["frame"], name))
        names.add(name)
    return entries, names


def load_project(path: str | Path) -> ImageDocument:
    """Validate an untrusted .laip file before restoring a memory-only document.

    No archived paths are extracted. All stored frame names are exact allowlist
    entries and all data is bounded and checksum-verified before decoding.
    The original source *path* is intentionally not preserved.
    """
    target = Path(path).expanduser()
    if target.stat().st_size > MAX_PROJECT_BYTES:
        raise ValueError("Project archive is too large.")
    try:
        with ZipFile(target, "r") as archive:
            info = archive.infolist()
            names = [item.filename for item in info]
            if (
                len(names) != len(set(names))
                or not names
                or len(names) > MAX_SNAPSHOTS + 3
                or any(item.is_dir() or item.flag_bits & 1 for item in info)
                or any(item.file_size > MAX_FRAME_BYTES for item in info if item.filename != "manifest.json")
                or sum(item.file_size for item in info) > MAX_PROJECT_BYTES
            ):
                raise ValueError("Invalid or oversized project archive.")
            if names.count("manifest.json") != 1 or archive.getinfo("manifest.json").file_size > MAX_MANIFEST_BYTES:
                raise ValueError("Missing or oversized project metadata.")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if (
                not isinstance(manifest, dict)
                or set(manifest) != {
                    "format", "version", "history_budget_bytes", "history_labels",
                    "original", "current", "undo", "redo",
                }
                or manifest["format"] != FORMAT_ID
                or type(manifest["version"]) is not int
                or manifest["version"] != PROJECT_VERSION
            ):
                raise ValueError("Unsupported or invalid project version.")
            budget = manifest["history_budget_bytes"]
            if type(budget) is not int or not (0 <= budget <= DEFAULT_HISTORY_BUDGET_BYTES):
                raise ValueError("Invalid project history budget.")
            labels = _checked_labels(manifest["history_labels"])
            undo, undo_names = _snapshot_descriptors(manifest["undo"], "undo")
            redo, redo_names = _snapshot_descriptors(manifest["redo"], "redo")
            if len(undo) + len(redo) > MAX_SNAPSHOTS:
                raise ValueError("Too many project snapshots.")
            if len(undo) > len(labels) or (
                undo and [entry[0] for entry in undo] != labels[-len(undo):]
            ):
                raise ValueError("Project history is inconsistent.")
            expected = {"manifest.json", "frames/original.png", "frames/current.png"} | undo_names | redo_names
            if set(names) != expected:
                raise ValueError("Project has missing or unexpected entries.")

            original = _read_frame(archive, manifest["original"], "frames/original.png")
            current = _read_frame(archive, manifest["current"], "frames/current.png")
            undo_entries = [_HistoryEntry(_read_frame(archive, frame, name), label) for label, frame, name in undo]
            redo_entries = [_HistoryEntry(_read_frame(archive, frame, name), label) for label, frame, name in redo]

        document = ImageDocument(original, history_budget_bytes=budget)
        consumed = sum(item.size_bytes for item in (*undo_entries, *redo_entries))
        if consumed > budget:
            raise ValueError("Project history exceeds its stored memory budget.")
        document._current = current
        document._labels = labels
        document._undo = deque(undo_entries)
        document._redo = deque(redo_entries)
        document._history_memory_bytes = consumed
        return document
    except (BadZipFile, EOFError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Invalid or corrupted project archive.") from exc
