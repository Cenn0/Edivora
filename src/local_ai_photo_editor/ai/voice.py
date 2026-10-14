"""Pinned local Silero VAD 6.2.1 ONNX inference (voice activity, not speech-to-text).

This module intentionally has no Qt, Torch, cloud, runtime download or generic
model loader. Invoke it from a cancellable child process only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from ..core.media import ffmpeg_executable, validate_source

VOICE_MODEL_VERSION = "v6.2.1"
VOICE_MODEL_NAME = "silero_vad_v6.2.1.onnx"
VOICE_MODEL_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/v6.2.1/"
    "src/silero_vad/data/silero_vad.onnx"
)
VOICE_MODEL_SIZE = 2_327_524
VOICE_MODEL_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
MAX_ANALYSIS_MS = 15 * 60 * 1000
MAX_AUDIO_OUTPUT_BYTES = MAX_ANALYSIS_MS * 16_000 * 2 // 1000 + 4096
SAMPLE_RATE = 16_000
FRAME_SAMPLES = 512
CONTEXT_SAMPLES = 64


def voice_model_path() -> Path:
    return Path(__file__).resolve().parent.parent / "models" / VOICE_MODEL_NAME


def verified_voice_model(path: Path | None = None) -> bytes:
    model = voice_model_path() if path is None else Path(path)
    with model.open("rb") as stream:
        data = stream.read(VOICE_MODEL_SIZE + 1)
    if len(data) != VOICE_MODEL_SIZE or hashlib.sha256(data).hexdigest() != VOICE_MODEL_SHA256:
        raise ValueError("Local speech-detection model did not pass SHA-256 verification.")
    return data


def model_available() -> bool:
    return voice_model_path().is_file()


def detect_speech(probabilities: list[float] | np.ndarray, *,
                  frame_ms: int = 32, length_ms: int | None = None,
                  threshold: float = 0.55, min_speech_ms: int = 192,
                  pad_ms: int = 120, min_silence_ms: int = 256) -> list[tuple[int, int]]:
    """Conservative hysteresis + trailing-silence segmentation over model output.

    Return proposed ranges only; speech detection does not automatically edit
    an accepted project. The minimums are UX choices, not model quality claims.
    """
    values = np.asarray(probabilities, dtype=np.float32).reshape(-1)
    if not np.isfinite(values).all() or np.any(values < 0) or np.any(values > 1):
        raise ValueError("Invalid speech model probability sequence.")
    if length_ms is None:
        length_ms = len(values) * frame_ms
    if type(length_ms) is not int or length_ms < 0:
        raise ValueError("Invalid audio length.")
    segments: list[tuple[int, int]] = []
    start: int | None = None
    silence_start: int | None = None
    for idx, probability in enumerate(values):
        clock = idx * frame_ms
        if start is None:
            if probability >= threshold:
                start = clock
                silence_start = None
        elif probability < threshold - 0.15:
            if silence_start is None:
                silence_start = clock
            elif clock - silence_start >= min_silence_ms:
                if silence_start - start >= min_speech_ms:
                    segments.append((start, min(length_ms, silence_start)))
                start = None
                silence_start = None
        else:
            silence_start = None
    if start is not None and length_ms - start >= min_speech_ms:
        segments.append((start, length_ms))

    padded: list[tuple[int, int]] = []
    for start, end in segments:
        start = max(0, start - pad_ms)
        end = min(length_ms, end + pad_ms)
        if end - start < 100:
            continue
        if padded and start - padded[-1][1] <= 200:
            padded[-1] = (padded[-1][0], max(end, padded[-1][1]))
        else:
            padded.append((start, end))
    return padded


def _read_pcm(source: Path, start_ms: int, end_ms: int, binary: str) -> np.ndarray:
    duration = end_ms - start_ms
    if not 100 <= duration <= MAX_ANALYSIS_MS:
        raise ValueError("Select between 0.1 seconds and 15 minutes for local voice detection.")
    args = [
        binary, "-nostdin", "-hide_banner", "-loglevel", "error",
        "-protocol_whitelist", "file,pipe,data",
        "-ss", f"{start_ms / 1000:.3f}", "-i", str(source),
        "-t", f"{duration / 1000:.3f}", "-vn", "-sn", "-dn",
        "-map", "0:a:0", "-ac", "1", "-ar", "16000",
        "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1",
    ]
    process = subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=120)
        if process.returncode != 0:
            raise RuntimeError("Audio decoding failed: " + stderr[-400:].decode("utf-8", "replace"))
        if len(stdout) < FRAME_SAMPLES * 2 or len(stdout) > MAX_AUDIO_OUTPUT_BYTES:
            raise ValueError("Decoded audio size is outside the safe voice-analysis range.")
        return np.frombuffer(stdout[: len(stdout) // 2 * 2], dtype="<i2").astype(np.float32) / 32768
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def analyze_voice(source: Path, start_ms: int, end_ms: int,
                  *, ffmpeg: str | None = None, model: Path | None = None) -> list[tuple[int, int]]:
    source = validate_source(source, "audio")
    if (type(start_ms) is not int or type(end_ms) is not int
            or start_ms < 0 or end_ms <= start_ms):
        raise ValueError("Invalid requested voice-analysis time range.")
    # No external ONNX assets are accepted. Only the bundled pinned artifact.
    model_data = verified_voice_model(model)
    import onnxruntime as ort

    ort.disable_telemetry_events()
    opts = ort.SessionOptions()
    opts.inter_op_num_threads = 1
    opts.intra_op_num_threads = 1
    opts.log_severity_level = 3
    session = ort.InferenceSession(model_data, providers=["CPUExecutionProvider"], sess_options=opts)
    if {x.name for x in session.get_inputs()} != {"input", "state", "sr"}:
        raise ValueError("Bundled voice model has unexpected inputs.")
    if len(session.get_outputs()) != 2:
        raise ValueError("Bundled voice model has unexpected outputs.")

    samples = _read_pcm(source, start_ms, end_ms, ffmpeg or ffmpeg_executable())
    state = np.zeros((2, 1, 128), dtype=np.float32)
    context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)
    scores = []
    for cursor in range(0, len(samples), FRAME_SAMPLES):
        block = samples[cursor: cursor + FRAME_SAMPLES]
        if len(block) != FRAME_SAMPLES:
            block = np.pad(block, (0, FRAME_SAMPLES - len(block)))
        padded = np.concatenate((context, block.reshape(1, -1)), axis=1).astype(np.float32)
        score, state = session.run(None, {
            "input": padded, "state": state, "sr": np.array(SAMPLE_RATE, dtype=np.int64),
        })
        probability = float(np.asarray(score).reshape(-1)[0])
        scores.append(probability)
        context = padded[:, -CONTEXT_SAMPLES:]
    found = detect_speech(scores, length_ms=min(len(samples) * 1000 // SAMPLE_RATE, end_ms - start_ms))
    return [(start_ms + a, start_ms + b) for a, b in found]


def voice_worker(job_directory: Path, executable: str | None = None) -> int:
    """Read a small, private request and write bounded machine-readable results."""
    job_directory = Path(job_directory)
    request = job_directory / "request.json"
    status = job_directory / "result.json"
    try:
        if request.stat().st_size > 8192:
            raise ValueError("Voice job request is too large.")
        data = json.loads(request.read_text("utf-8"))
        if type(data) is not dict or set(data) != {"source", "start_ms", "end_ms"}:
            raise ValueError("Invalid voice job request.")
        segments = analyze_voice(
            Path(data["source"]), data["start_ms"], data["end_ms"],
            ffmpeg=ffmpeg_executable(executable),
        )
        status.write_text(json.dumps({
            "ok": True, "segments": segments[:50],
            "too_many": len(segments) > 50,
        }), encoding="utf-8")
        return 0
    except Exception as exc:
        status.write_text(json.dumps({
            "ok": False, "message": f"{type(exc).__name__}: {str(exc)[:250]}",
        }), encoding="utf-8")
        return 1
