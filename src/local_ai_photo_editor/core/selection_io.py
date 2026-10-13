"""Bounded file protocol for a local subject-selection worker, without Qt/AI."""
from __future__ import annotations

import hashlib
import hmac
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile

from PIL import Image

from .editing import MAX_IMAGE_PIXELS, _validate_dimensions
from .subject import validate_subject_mask

MAX_MASK_FILE_BYTES = MAX_IMAGE_PIXELS * 2 + 2 * 1024 * 1024
_STATUS_KEYS = {"version", "status", "operation", "width", "height", "sha256"}


class SubjectJobError(ValueError):
    """Public error category only; no paths or image metadata in the message."""
    def __init__(self, code: str = "INFERENCE_ERROR") -> None:
        self.code = code if isinstance(code, str) and code in {
            "MODEL_MISSING", "MODEL_INVALID", "NO_SUBJECT"
        } else "INFERENCE_ERROR"
        super().__init__(self.code)


def write_subject_result(mask: Image.Image, directory: Path) -> dict[str, object]:
    """Write the fixed mask artifact atomically, returning its success manifest."""
    validate_subject_mask(mask, mask.size)
    directory = Path(directory)
    descriptor, name = tempfile.mkstemp(prefix=".selection-", suffix=".tmp", dir=directory)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            # Own the descriptor before allocating pixels so MemoryError also
            # closes it before cleanup (important for Windows file locking).
            clean = Image.frombytes("L", mask.size, mask.tobytes())
            clean.save(stream, format="PNG")
            stream.flush()
            os.fsync(stream.fileno())
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        os.replace(temporary, directory / "mask.png")
    finally:
        temporary.unlink(missing_ok=True)
    return {"version": 1, "status": "ok", "operation": "select_subject",
            "width": mask.width, "height": mask.height, "sha256": digest}


def read_subject_result(directory: Path, size: tuple[int, int], exit_code: int) -> Image.Image:
    """Validate success, image type, dimensions, size bounds and the exact bytes."""
    _validate_dimensions(*size)
    status_path = Path(directory) / "result.json"
    if status_path.is_symlink() or not status_path.is_file() or status_path.stat().st_size > 4096:
        raise SubjectJobError()
    with status_path.open("rb") as stream:
        raw_status = stream.read(4097)
    if len(raw_status) > 4096:
        raise SubjectJobError()
    try:
        status = json.loads(raw_status)
    except (ValueError, UnicodeError) as exc:
        raise SubjectJobError() from exc
    if not isinstance(status, dict):
        raise SubjectJobError()
    if status.get("status") == "error":
        raise SubjectJobError(status.get("code"))
    if (exit_code != 0 or set(status) != _STATUS_KEYS
            or type(status.get("version")) is not int or status["version"] != 1
            or status["status"] != "ok" or status["operation"] != "select_subject"
            or type(status["width"]) is not int or type(status["height"]) is not int
            or (status["width"], status["height"]) != size
            or not isinstance(status["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", status["sha256"]) is None):
        raise SubjectJobError()
    path = Path(directory) / "mask.png"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MASK_FILE_BYTES:
        raise SubjectJobError()
    with path.open("rb") as stream:
        raw = stream.read(MAX_MASK_FILE_BYTES + 1)
    if len(raw) > MAX_MASK_FILE_BYTES or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), status["sha256"]):
        raise SubjectJobError()
    with Image.open(BytesIO(raw)) as opened:
        if opened.format != "PNG" or getattr(opened, "n_frames", 1) != 1 or opened.info:
            raise SubjectJobError()
        validate_subject_mask(opened, size)
        opened.load()
        result = opened.copy()
    result.info.clear()
    return result
