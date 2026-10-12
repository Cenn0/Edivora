"""Known local model artifacts. This module never performs network requests."""

from __future__ import annotations

import hashlib
from pathlib import Path

MODEL_FILENAME = "u2netp.onnx"
MODEL_SIZE = 4_574_861
MODEL_SHA256 = "309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8"
# The upstream rembg adapter publishes this legacy compatibility checksum.
# SHA-256 is the runtime integrity check; MD5 is not an authenticity mechanism.
UPSTREAM_MD5 = "8e83ca70e441ab06c318d82300c84806"
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"


class ModelMissingError(RuntimeError):
    """A complete offline distribution must contain the model."""


class ModelIntegrityError(RuntimeError):
    """The installed artifact does not match the reviewed artifact."""


def model_path() -> Path:
    return Path(__file__).resolve().parent.parent / "models" / MODEL_FILENAME


def available() -> bool:
    return model_path().is_file()


def verified_model_bytes(path: Path | None = None) -> bytes:
    target = model_path() if path is None else Path(path)
    try:
        with target.open("rb") as source:
            data = source.read(MODEL_SIZE + 1)
    except FileNotFoundError as exc:
        raise ModelMissingError("The offline AI package is missing its model.") from exc
    if len(data) != MODEL_SIZE or hashlib.sha256(data).hexdigest() != MODEL_SHA256:
        raise ModelIntegrityError("The local AI model failed its integrity check.")
    return data

