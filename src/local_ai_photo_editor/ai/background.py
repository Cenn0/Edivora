"""U2NETP saliency inference and alpha compositing, entirely on the CPU."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image

from .models import verified_model_bytes

INPUT_SIZE = 320


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
        # Uniform predictions contain no reliable foreground information.
        # Do not silently erase the photo or report a successful empty mask.
        raise ValueError("The model could not identify a foreground in this image.")
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


def remove_background(image: Image.Image, path: Path | None = None) -> Image.Image:
    # Validate the bytes before importing/initializing the native inference engine.
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
    return apply_mask(image, output_mask(predictions[0], image.size))

