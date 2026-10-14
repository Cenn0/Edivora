"""Pinned, offline DnCNN color denoiser. CPU only; never a generic filter inverter."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

import numpy as np

MODEL_NAME = "dncnn_color_blind.onnx"
MODEL_BYTES = 2_677_066
MODEL_SHA256 = "b6a7d59f4ce2ada940dcd78bd627595c59c5180a9c6d7787fa153198d2f50c12"
MAX_PIXELS = 1280 * 720
TILE = 160
HALO = 20  # Twenty 3x3 convolutions: exact receptive-field radius.


def model_path() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / MODEL_NAME


def verified_bytes() -> bytes:
    path = model_path()
    if not path.is_file() or path.is_symlink() or path.stat().st_size != MODEL_BYTES:
        raise ValueError("The bundled DnCNN model is missing or invalid. No model is downloaded at runtime.")
    with path.open("rb") as stream:
        data = stream.read(MODEL_BYTES + 1)
    if len(data) != MODEL_BYTES or hashlib.sha256(data).hexdigest() != MODEL_SHA256:
        raise ValueError("The bundled DnCNN model checksum is invalid.")
    return data


def model_available() -> bool:
    try:
        verified_bytes()
        return True
    except (OSError, ValueError):
        return False


class Denoiser:
    def __init__(self) -> None:
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_mem_pattern = False
        self.session = ort.InferenceSession(verified_bytes(), sess_options=options,
                                            providers=["CPUExecutionProvider"])

    def apply(self, rgb: np.ndarray, strength: int,
              cancelled: Callable[[], bool] = lambda: False) -> np.ndarray:
        if (type(strength) is not int or not 0 <= strength <= 100
                or not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8
                or rgb.ndim != 3 or rgb.shape[2] != 3
                or not 1 <= rgb.shape[0] * rgb.shape[1] <= MAX_PIXELS):
            raise ValueError("Invalid neural denoising input or strength.")
        if not strength:
            return rgb.copy()
        height, width = rgb.shape[:2]
        source = rgb.astype(np.float32) / 255
        output = np.empty_like(rgb)
        for top in range(0, height, TILE):
            for left in range(0, width, TILE):
                if cancelled():
                    raise InterruptedError("Video restoration cancelled.")
                bottom, right = min(top + TILE, height), min(left + TILE, width)
                t, l = max(0, top - HALO), max(0, left - HALO)
                b, r = min(height, bottom + HALO), min(width, right + HALO)
                tile = np.ascontiguousarray(source[t:b, l:r].transpose(2, 0, 1)[None])
                result = self.session.run(["output"], {"input": tile})[0]
                if result.shape != tile.shape or not np.isfinite(result).all():
                    raise ValueError("Invalid output from the neural denoiser.")
                restored = result[0].transpose(1, 2, 0)[top-t:bottom-t, left-l:right-l]
                original = source[top:bottom, left:right]
                mixed = original + (restored - original) * (strength / 100)
                output[top:bottom, left:right] = np.rint(np.clip(mixed, 0, 1) * 255).astype(np.uint8)
        return output
