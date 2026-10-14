"""Build-only deterministic conversion of a pinned, author-published DnCNN model.

Install torch==2.14.1 (CPU wheels), onnx==1.23.2 and the app dependencies first.
Neither PyTorch, .pth parsing nor network acquisition is used by the application.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from local_ai_photo_editor.ai.restoration import (  # noqa: E402
    MODEL_BYTES, MODEL_SHA256, model_path,
)

SOURCE_URL = "https://github.com/cszn/KAIR/releases/download/v1.0/dncnn_color_blind.pth"
SOURCE_BYTES = 2_678_121
SOURCE_SHA256 = "dfe11a6b703304df82cdf236f431fc6492766c7b9119d97e943edeb392c710a3"


def convert(data: bytes) -> tuple[bytes, dict]:
    """No deserialization until the exact reviewed bytes have been verified."""
    if len(data) != SOURCE_BYTES or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("DnCNN source model size or SHA-256 mismatch.")
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    import onnxruntime as ort
    import torch
    import torch.nn.functional as functional

    if torch.__version__.split("+")[0] != "2.14.1" or onnx.__version__ != "1.23.2":
        raise RuntimeError("Use the reviewed build-only torch 2.14.1 and onnx 1.23.2 versions.")
    state = torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)
    expected = {f"model.{i*2}.{part}" for i in range(20) for part in ("weight", "bias")}
    if set(state) != expected:
        raise ValueError("Unexpected DnCNN tensors.")
    nodes, initializers = [], []
    current = "input"
    for i in range(20):
        wn, bn = f"model.{i*2}.weight", f"model.{i*2}.bias"
        channels = 3 if i == 19 else 64
        if (tuple(state[wn].shape) != (channels, 3 if i == 0 else 64, 3, 3)
                or tuple(state[bn].shape) != (channels,)):
            raise ValueError("Unexpected tensor shape.")
        for name in (wn, bn):
            array = state[name].numpy()
            if array.dtype != np.float32 or not np.isfinite(array).all():
                raise ValueError("Invalid tensor data.")
            initializers.append(numpy_helper.from_array(array.astype("<f4"), name=name))
        conv = f"conv_{i}"
        nodes.append(helper.make_node("Conv", [current, wn, bn], [conv],
            kernel_shape=[3, 3], pads=[1, 1, 1, 1], strides=[1, 1]))
        current = conv
        if i < 19:
            current = f"relu_{i}"
            nodes.append(helper.make_node("Relu", [conv], [current]))
    nodes.append(helper.make_node("Sub", ["input", current], ["output"]))
    graph = helper.make_graph(nodes, "edivora_dncnn_color_blind",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, "height", "width"])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, "height", "width"])],
        initializer=initializers)
    model = helper.make_model(graph, producer_name="Edivora", producer_version="1",
        opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    encoded = model.SerializeToString(deterministic=True)
    if len(encoded) != MODEL_BYTES or hashlib.sha256(encoded).hexdigest() != MODEL_SHA256:
        raise ValueError("Converted model does not match the reviewed ONNX bytes.")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(encoded, sess_options=options, providers=["CPUExecutionProvider"])
    clean = np.full((1, 3, 64, 64), .5, dtype=np.float32)
    noisy = np.clip(clean + np.random.default_rng(7).normal(0, .08, clean.shape).astype(np.float32), 0, 1)
    actual = session.run(["output"], {"input": noisy})[0]
    torch.set_num_threads(2)
    original = torch.from_numpy(noisy)
    x = original
    for i in range(20):
        x = functional.conv2d(x, state[f"model.{i*2}.weight"], state[f"model.{i*2}.bias"], padding=1)
        if i < 19:
            x = functional.relu(x)
    error = float(np.max(np.abs(actual - (original - x).numpy())))
    before, after = float(np.mean((noisy-clean)**2)), float(np.mean((actual-clean)**2))
    if error >= 1e-5 or after >= before * .5:
        raise RuntimeError("Converted model failed real CPU equivalence / synthetic denoising test.")
    return encoded, {"source_url": SOURCE_URL, "source_bytes": SOURCE_BYTES,
        "source_sha256": SOURCE_SHA256, "onnx_bytes": len(encoded), "onnx_sha256": MODEL_SHA256,
        "cpu_max_difference": error, "synthetic_mse_before": before, "synthetic_mse_after": after,
        "torch": torch.__version__, "onnx": onnx.__version__, "onnxruntime": ort.__version__,
        "scope": "conversion and synthetic CPU inference, not real-world quality or Windows 11 acceptance"}


def main() -> int:
    destination = model_path()
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Insecure model download redirect.")
        data = response.read(SOURCE_BYTES + 1)
    encoded, report = convert(data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".dncnn-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    evidence = ROOT / "test-results" / "restoration-model-conversion.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
