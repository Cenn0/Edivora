"""Single-job local worker. A subprocess provides cancellation, not sandboxing."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .ai.models import ModelIntegrityError, ModelMissingError
from .ai.background import NoSubjectError


def _write_status(directory: Path, payload: dict[str, object]) -> None:
    temporary = directory / "result.json.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    os.replace(temporary, directory / "result.json")


def run_job(directory: Path) -> int:
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        return 2
    try:
        request_path = directory / "request.json"
        if request_path.is_symlink() or not request_path.is_file() or request_path.stat().st_size > 4096:
            raise ValueError("Invalid job request.")
        with request_path.open("rb") as stream:
            raw_request = stream.read(4097)
        if len(raw_request) > 4096:
            raise ValueError("Invalid job request.")
        request = json.loads(raw_request)
        if (not isinstance(request, dict)
                or set(request) not in ({"version", "operation"}, {"version", "operation", "model"})
                or type(request["version"]) is not int or request["version"] != 1
                or request["operation"] not in ("remove_background", "select_subject")):
            raise ValueError("Unsupported job request.")
        # The original two-field protocol remains backward compatible; it
        # always uses U2NETP. UI requests explicitly carry their chosen mode.
        model_requested = request.get("model", "u2netp")
        if "model" in request:
            from .ai.catalog import TASK_IMAGE, choose_model
            selected_model = choose_model(TASK_IMAGE, model_requested, verify=True)
            if selected_model is None:
                raise ModelMissingError("No installed segmentation model fits this machine.")
        else:
            selected_model = "u2netp"
        image_path = directory / "input.png"
        if image_path.is_symlink():
            raise ValueError("Invalid input file.")
        from .core import export_image, load_image
        from .ai.background import predict_subject, remove_background
        from .core.selection_io import write_subject_result

        source = load_image(image_path)
        if request["operation"] == "select_subject":
            mask = (predict_subject(source) if selected_model == "u2netp"
                    else predict_subject(source, model_id=selected_model))
            if mask.size != source.size:
                raise ValueError("The worker returned incorrect dimensions.")
            status = write_subject_result(mask, directory)
        else:
            result = (remove_background(source) if selected_model == "u2netp"
                      else remove_background(source, model_id=selected_model))
            if result.size != source.size:
                raise ValueError("The worker returned incorrect dimensions.")
            export_image(result, directory / "output.png", source_path=image_path)
            status = {"status": "ok"}
        _write_status(directory, status)
        return 0
    except (ModelMissingError, FileNotFoundError):
        payload = {"status": "error", "code": "MODEL_MISSING", "message": "The offline AI model is missing."}
    except ModelIntegrityError:
        payload = {"status": "error", "code": "MODEL_INVALID", "message": "The offline AI model is damaged or unsupported."}
    except NoSubjectError:
        payload = {"status": "error", "code": "NO_SUBJECT", "message": "No usable subject selection was found."}
    except Exception:
        payload = {"status": "error", "code": "INFERENCE_ERROR", "message": "The local editing job could not be completed."}
    _write_status(directory, payload)
    return 1
