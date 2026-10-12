"""Single-job local worker. A subprocess provides cancellation, not sandboxing."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .ai.models import ModelIntegrityError, ModelMissingError


def _write_status(directory: Path, payload: dict[str, str]) -> None:
    temporary = directory / "result.json.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    os.replace(temporary, directory / "result.json")


def run_job(directory: Path) -> int:
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        return 2
    try:
        request_path = directory / "request.json"
        if request_path.is_symlink() or request_path.stat().st_size > 4096:
            raise ValueError("Invalid job request.")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if request != {"version": 1, "operation": "remove_background"}:
            raise ValueError("Unsupported job request.")
        image_path = directory / "input.png"
        if image_path.is_symlink():
            raise ValueError("Invalid input file.")
        from .core import export_image, load_image
        from .ai.background import remove_background

        source = load_image(image_path)
        result = remove_background(source)
        if result.size != source.size:
            raise ValueError("The worker returned incorrect dimensions.")
        export_image(result, directory / "output.png", source_path=image_path)
        _write_status(directory, {"status": "ok"})
        return 0
    except ModelMissingError:
        payload = {"status": "error", "code": "MODEL_MISSING", "message": "The offline AI model is missing."}
    except ModelIntegrityError:
        payload = {"status": "error", "code": "MODEL_INVALID", "message": "The offline AI model is damaged or unsupported."}
    except Exception:
        # Do not leak paths or image metadata into process logs or error reports.
        payload = {"status": "error", "code": "INFERENCE_ERROR", "message": "The local editing job could not be completed."}
    _write_status(directory, payload)
    return 1

