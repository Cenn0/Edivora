"""Local, bounded multilingual Whisper Tiny transcription (CPU, offline).

Uses the pinned ONNX encoder/decoder with the documented sherpa-onnx API.
This is a distinct ASR model from Silero VAD (speech activity only).
SRT timecodes, if selected, refer to 20-second decoding chunks and are
*not* accurate word-/sentence-aligned subtitle timings.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import uuid

import numpy as np

from .catalog import model_file, model_installed
from .voice import SAMPLE_RATE, _read_pcm
from ..core.media import protects_source, validate_source

MAX_TRANSCRIBE_MS = 3 * 60 * 1000
CHUNK_MS = 20_000
MAX_CHUNKS = 9


def _srt_clock(ms: int) -> str:
    hours, remainder = divmod(ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def transcribe(source: Path, kind: str, start_ms: int, end_ms: int,
               language: str, *, ffmpeg: str | None = None) -> list[dict[str, object]]:
    if language not in ("de", "en"):
        raise ValueError("Choose German or English for transcription.")
    if (type(start_ms) is not int or type(end_ms) is not int
            or start_ms < 0 or not 100 <= end_ms - start_ms <= MAX_TRANSCRIBE_MS):
        raise ValueError("Select a 0.1 second to 3 minute region for transcription.")
    source = validate_source(source, kind)
    if not model_installed("whisper-tiny", verify=True):
        raise FileNotFoundError("The bundled Whisper Tiny ASR model is missing or corrupt.")
    import sherpa_onnx
    from ..core.media import ffmpeg_executable

    audio = _read_pcm(source, start_ms, end_ms, ffmpeg or ffmpeg_executable())
    recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(model_file("whisper-tiny", "tiny-encoder.int8.onnx")),
        decoder=str(model_file("whisper-tiny", "tiny-decoder.int8.onnx")),
        tokens=str(model_file("whisper-tiny", "tiny-tokens.txt")),
        language=language, task="transcribe", num_threads=2,
        provider="cpu", debug=False,
    )
    chunks: list[dict[str, object]] = []
    count = min(MAX_CHUNKS, (len(audio) + SAMPLE_RATE * CHUNK_MS // 1000 - 1)
                // (SAMPLE_RATE * CHUNK_MS // 1000))
    for idx in range(count):
        lo = idx * (CHUNK_MS * SAMPLE_RATE // 1000)
        hi = min(len(audio), (idx + 1) * (CHUNK_MS * SAMPLE_RATE // 1000))
        if hi - lo < 1600:
            continue
        stream = recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, np.ascontiguousarray(audio[lo:hi], dtype=np.float32))
        recognizer.decode_stream(stream)
        result_text = str(stream.result.text or "").strip()
        if result_text:
            chunks.append({
                "start_ms": start_ms + (lo * 1000 // SAMPLE_RATE),
                "end_ms": start_ms + (hi * 1000 // SAMPLE_RATE),
                "text": result_text[:4000],
            })
    return chunks


def _export_text(rows: list[dict[str, object]], target: Path) -> None:
    if target.suffix.lower() == ".srt":
        text = "\n\n".join(
            f"{index}\n{_srt_clock(row['start_ms'])} --> {_srt_clock(row['end_ms'])}\n{row['text']}"
            for index, row in enumerate(rows, 1)
        ) + "\n"
    else:
        text = "\n\n".join(
            f"[{_srt_clock(row['start_ms'])} – {_srt_clock(row['end_ms'])}] {row['text']}"
            for row in rows
        ) + "\n"
    # Simple transcription does not embed source audio/video.
    target.write_text(text, encoding="utf-8")


def transcribe_to_file(
    source: Path, kind: str, start_ms: int, end_ms: int, language: str,
    destination: Path, *, ffmpeg: str | None = None,
) -> Path:
    source = validate_source(source, kind)
    target = Path(destination).expanduser().absolute()
    if (target.suffix.lower() not in (".txt", ".srt")
            or not target.parent.is_dir() or target.is_symlink()
            or not protects_source(source, target)):
        raise ValueError("Choose a different new .txt or .srt output.")
    chunks = transcribe(source, kind, start_ms, end_ms, language, ffmpeg=ffmpeg)
    temp = target.parent / f".edivora-transcribe-{uuid.uuid4().hex}{target.suffix.lower()}"
    try:
        _export_text(chunks, temp)
        if not protects_source(source, target) or target.is_symlink():
            raise ValueError("Original source protection failed.")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def transcription_worker(folder: Path, executable: str | None = None) -> int:
    folder = Path(folder)
    response = folder / "result.json"
    try:
        request = folder / "request.json"
        if request.is_symlink() or request.stat().st_size > 4096:
            raise ValueError("Invalid transcript request.")
        data = json.loads(request.read_text("utf-8"))
        if type(data) is not dict or set(data) != {
            "source", "kind", "start_ms", "end_ms", "language", "destination", "model"
        }:
            raise ValueError("Invalid transcript job fields.")
        from .catalog import TASK_TRANSCRIBE, choose_model
        selected = choose_model(TASK_TRANSCRIBE, data["model"], verify=True)
        if selected != "whisper-tiny":
            raise ValueError("No verified local transcription model available.")
        from ..core.media import ffmpeg_executable
        path = transcribe_to_file(
            Path(data["source"]), data["kind"], data["start_ms"], data["end_ms"],
            data["language"], Path(data["destination"]),
            ffmpeg=ffmpeg_executable(executable),
        )
        response.write_text(
            json.dumps({"ok": True, "name": path.name, "model": selected}), encoding="utf-8"
        )
        return 0
    except Exception as exc:
        response.write_text(json.dumps({
            "ok": False, "message": f"{type(exc).__name__}: {str(exc)[:220]}",
        }), encoding="utf-8")
        return 1
