"""U2NETP saliency inference and alpha compositing, entirely on the CPU."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image

from .models import verified_model_bytes

INPUT_SIZE = 320


class NoSubjectError(ValueError):
    """The model produced no usable foreground/background separation."""


def prepare_input(image: Image.Image) -> np.ndarray:
    """Match U2NETP's documented image normalization; handle all-black input."""
    rgb = image.convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.LANCZOS)
    pixels = np.asarray(rgb, dtype=np.float32)
    maximum = float(pixels.max())
    if maximum > 0.0:
        pixels = pixels / maximum
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    scale = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (pixels - mean) / scale
    return np.ascontiguousarray(normalized.transpose(2, 0, 1)[None, ...])


def output_mask(prediction: np.ndarray, size: tuple[int, int]) -> Image.Image:
    """Convert only the expected saliency output, rejecting invalid model output."""
    prediction = np.asarray(prediction, dtype=np.float32)
    if prediction.shape != (1, 1, INPUT_SIZE, INPUT_SIZE):
        raise ValueError("The model produced an unexpected mask shape.")
    plane = prediction[0, 0]
    if not np.isfinite(plane).all():
        raise ValueError("The model produced a non-finite mask.")
    low, high = float(plane.min()), float(plane.max())
    if high - low <= np.finfo(np.float32).eps:
        raise NoSubjectError("The model could not identify a foreground in this image.")
    values = np.rint((plane - low) / (high - low) * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(values).resize(size, Image.Resampling.LANCZOS)


def apply_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    if image.size != mask.size:
        raise ValueError("Mask and photo dimensions must match.")
    result = image.convert("RGBA")
    alpha = np.asarray(result.getchannel("A"), dtype=np.uint16)
    foreground = np.asarray(mask.convert("L"), dtype=np.uint16)
    combined = ((alpha * foreground + 127) // 255).astype(np.uint8)
    result.putalpha(Image.fromarray(combined))
    return result


def _predict_isnet(image: Image.Image) -> Image.Image:
    """Run the larger pinned IS-Net/DIS model on the CPU only.

    The source's RGB is preserved; the result is a subject-alpha mask.
    ONNX input/output contracts match the upstream 1024-pixel rembg export.
    """
    import hashlib
    from .catalog import ISNET_MAX_BYTES, ISNET_SHA256, model_file

    path = model_file("isnet-general-use")
    with path.open("rb") as input_file:
        data = input_file.read(ISNET_MAX_BYTES + 1)
    if not data or len(data) > ISNET_MAX_BYTES or hashlib.sha256(data).hexdigest() != ISNET_SHA256:
        from .models import ModelIntegrityError
        raise ModelIntegrityError("The pinned IS-Net model is invalid.")
    import onnxruntime as ort

    ort.disable_telemetry_events()
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = max(1, min(4, os.cpu_count() or 2))
    opts.inter_op_num_threads = 1
    opts.log_severity_level = 3
    session = ort.InferenceSession(data, sess_options=opts, providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    if len(inputs) != 1 or inputs[0].shape != [1, 3, 1024, 1024]:
        raise ValueError("IS-Net model input dimensions changed.")
    rgb = image.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    floats = np.asarray(rgb, dtype=np.float32)
    maximum = float(floats.max())
    if maximum > 0:
        floats /= maximum
    floats -= 0.5
    tensor = np.ascontiguousarray(floats.transpose(2, 0, 1)[None])
    prediction = session.run([session.get_outputs()[0].name], {inputs[0].name: tensor})[0]
    values = np.asarray(prediction, dtype=np.float32)
    if values.shape != (1, 1, 1024, 1024) or not np.isfinite(values).all():
        raise ValueError("IS-Net returned an invalid subject map.")
    plane = values[0, 0]
    low, high = float(plane.min()), float(plane.max())
    if high - low <= np.finfo(np.float32).eps:
        raise NoSubjectError("IS-Net did not detect a separable foreground.")
    alpha = np.rint((plane - low) / (high - low) * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(alpha).resize(image.size, Image.Resampling.LANCZOS)


def predict_subject(image: Image.Image, path: Path | None = None,
                    *, model_id: str = "u2netp") -> Image.Image:
    """Infer a local selection; model may be higher quality but not generative.

    Selection is performed by the worker process, never directly in the GUI.
    """
    if model_id == "isnet-general-use":
        if path is not None:
            raise ValueError("Custom IS-Net model paths are not supported.")
        return _predict_isnet(image)
    if model_id != "u2netp":
        raise ValueError("Unsupported segmentation model.")
    data = verified_model_bytes(path)
    import onnxruntime as ort

    ort.disable_telemetry_events()
    options = ort.SessionOptions()
    options.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 2) // 2))
    options.inter_op_num_threads = 1
    options.log_severity_level = 3
    session = ort.InferenceSession(data, sess_options=options, providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    if len(inputs) != 1 or inputs[0].shape != [1, 3, INPUT_SIZE, INPUT_SIZE]:
        raise ValueError("The bundled model has an unsupported input contract.")
    predictions = session.run([session.get_outputs()[0].name], {inputs[0].name: prepare_input(image)})
    return output_mask(predictions[0], image.size)


def remove_background(image: Image.Image, path: Path | None = None,
                      *, model_id: str = "u2netp") -> Image.Image:
    return apply_mask(image, predict_subject(image, path, model_id=model_id))
