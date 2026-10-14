"""Offline-only registry for the four independently packaged AI model families.

Model selection ranks *tasks*, not raw file size. Bigger models are not
guaranteed to improve every image or inference latency. Only CPU execution
is supported in this implementation; GPU detection does not imply support.
"""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Literal

from .models import MODEL_FILENAME, MODEL_SHA256, MODEL_SIZE, model_path
from .voice import VOICE_MODEL_NAME, VOICE_MODEL_SHA256, VOICE_MODEL_SIZE, voice_model_path

ISNET_FILENAME = "isnet-general-use.onnx"
ISNET_SHA256 = "60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a"
ISNET_SOURCE_URL = (
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
    "isnet-general-use.onnx"
)
WHISPER_SOURCE_ROOT = (
    "https://huggingface.co/csukuangfj/sherpa-onnx-whisper-tiny/resolve/65176e2"
)
WHISPER_FILES = {
    "tiny-encoder.int8.onnx": "d24fb083ae3b1041fc24e97971d60e280c9342201fbb67b0ab428a8b4a51a434",
    "tiny-decoder.int8.onnx": "d2fece8dd42771f1df975c6c0445770d0c292bf7547c2cae04a6c0cc57540925",
    # The tokenizer is pinned to the same immutable upstream git revision.
    # Its SHA-256 is stored in a build-generated manifest after downloading,
    # rather than claiming an unverified upstream checksum.
    "tiny-tokens.txt": None,
}
WHISPER_TOKEN_MIN = 700_000
WHISPER_TOKEN_MAX = 950_000
ISNET_MAX_BYTES = 230_000_000
WHISPER_MAX_BYTES = 120_000_000
MANIFEST_NAME = "whisper-assets.json"
TASK_IMAGE = "segmentation"
TASK_VOICE = "voice_detection"
TASK_TRANSCRIBE = "transcription"
TASKS = (TASK_IMAGE, TASK_VOICE, TASK_TRANSCRIBE)
MODEL_IDS = ("u2netp", "isnet-general-use", "silero-vad", "whisper-tiny")
AI_FOLDER = Path(__file__).resolve().parent.parent / "models"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    display_name: str
    task: str
    quality_rank: int
    min_total_gib: int
    min_free_gib: int
    min_cpu_cores: int
    artifact_names: tuple[str, ...]
    note: str


SPECS = {
    "u2netp": ModelSpec("u2netp", "U2NETP · Schnell", TASK_IMAGE, 1, 1, 1, 1, (MODEL_FILENAME,),
                        "Schnelle Freistellung für Bilder und einzelne Videoframes."),
    "isnet-general-use": ModelSpec("isnet-general-use", "IS-Net · Detailreich", TASK_IMAGE, 2, 8, 3, 4,
                                    (ISNET_FILENAME,),
                                    "Aufwendigere Freistellung; bessere Ergebnisse nicht bei jedem Motiv garantiert."),
    "silero-vad": ModelSpec("silero-vad", "Silero VAD · Sprachabschnitte", TASK_VOICE, 1, 2, 1, 1,
                            (VOICE_MODEL_NAME,), "Erkennt Sprachbereiche, schreibt keinen Text."),
    "whisper-tiny": ModelSpec("whisper-tiny", "Whisper Tiny · Transkription", TASK_TRANSCRIBE, 1, 4, 2, 2,
                              tuple(WHISPER_FILES), "Lokale Transkription, keine Wort-für-Wort-Zeitkorrektur."),
}


@dataclass(frozen=True)
class SystemMemory:
    total_bytes: int
    available_bytes: int
    logical_cpu_count: int
    measurement_available: bool = True

    @property
    def total_gib(self) -> float:
        return self.total_bytes / (1024 ** 3)

    @property
    def available_gib(self) -> float:
        return self.available_bytes / (1024 ** 3)


def detect_hardware() -> SystemMemory:
    """Best effort OS memory reading; never guess extra resources if unknown."""
    cpu = max(1, os.cpu_count() or 1)
    if sys.platform == "win32":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        data = MEMORYSTATUSEX()
        data.dwLength = ctypes.sizeof(data)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(data)):
                return SystemMemory(data.ullTotalPhys, data.ullAvailPhys, cpu)
        except (AttributeError, OSError):
            pass
    else:
        try:
            page = os.sysconf("SC_PAGE_SIZE")
            total = os.sysconf("SC_PHYS_PAGES")
            free = os.sysconf("SC_AVPHYS_PAGES")
            if min(page, total, free) > 0:
                return SystemMemory(int(page * total), int(page * free), cpu)
        except (ValueError, OSError, AttributeError):
            pass
    return SystemMemory(0, 0, cpu, False)


def model_file(model_id: str, name: str | None = None) -> Path:
    if model_id not in SPECS:
        raise ValueError("Unknown bundled model.")
    spec = SPECS[model_id]
    if name is None:
        if len(spec.artifact_names) != 1:
            raise ValueError("This model requires multiple artifacts.")
        name = spec.artifact_names[0]
    if name not in spec.artifact_names:
        raise ValueError("Unexpected model artifact.")
    return AI_FOLDER / name


def _digest(path: Path, *, limit: int | None = None) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    if limit is not None and not 0 < path.stat().st_size <= limit:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _whisper_integrity() -> bool:
    manifest = AI_FOLDER / MANIFEST_NAME
    try:
        if manifest.is_symlink() or manifest.stat().st_size > 2048:
            return False
        data = json.loads(manifest.read_text("utf-8"))
        if not isinstance(data, dict) or set(data) != {"version", "token_sha256"} or data["version"] != 1:
            return False
        token_hash = data["token_sha256"]
        if not isinstance(token_hash, str) or len(token_hash) != 64 or any(c not in "0123456789abcdef" for c in token_hash):
            return False
        for name, expected in WHISPER_FILES.items():
            file = model_file("whisper-tiny", name)
            if name == "tiny-tokens.txt":
                if not WHISPER_TOKEN_MIN <= file.stat().st_size <= WHISPER_TOKEN_MAX:
                    return False
                expected = token_hash
            if _digest(file, limit=WHISPER_MAX_BYTES) != expected:
                return False
        return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def model_installed(model_id: str, *, verify: bool = False) -> bool:
    if model_id not in SPECS:
        return False
    if not verify:
        return all(model_file(model_id, name).is_file() for name in SPECS[model_id].artifact_names)
    if model_id == "whisper-tiny":
        return _whisper_integrity()
    sha = {
        "u2netp": MODEL_SHA256,
        "isnet-general-use": ISNET_SHA256,
        "silero-vad": VOICE_MODEL_SHA256,
    }[model_id]
    limit = ISNET_MAX_BYTES if model_id == "isnet-general-use" else (
        MODEL_SIZE + 1 if model_id == "u2netp" else VOICE_MODEL_SIZE + 1
    )
    file = model_file(model_id)
    size = file.stat().st_size if file.is_file() else 0
    if model_id == "u2netp" and size != MODEL_SIZE:
        return False
    if model_id == "silero-vad" and size != VOICE_MODEL_SIZE:
        return False
    return _digest(file, limit=limit) == sha


def recommended(model_id: str, memory: SystemMemory) -> bool:
    spec = SPECS[model_id]
    if not memory.measurement_available:
        return model_id in ("u2netp", "silero-vad")
    return (memory.total_gib >= spec.min_total_gib
            and memory.available_gib >= spec.min_free_gib
            and memory.logical_cpu_count >= spec.min_cpu_cores)


def choose_model(task: str, requested: str = "auto", *,
                 hardware: SystemMemory | None = None, verify: bool = False) -> str | None:
    """Select highest *supported for this task*, with explicit manual override.

    verify=True checks package hashes; call on job start rather than every
    UI repaint. Missing/corrupt artifacts are never silently downloaded.
    """
    if task not in TASKS:
        raise ValueError("Unknown AI operation.")
    candidates = sorted(
        (spec for spec in SPECS.values() if spec.task == task),
        key=lambda item: item.quality_rank, reverse=True,
    )
    if requested != "auto":
        spec = SPECS.get(requested)
        if spec is None or spec.task != task:
            raise ValueError("The selected model is not supported for this task.")
        if not model_installed(requested, verify=verify):
            raise FileNotFoundError(f"The selected model is missing or invalid: {requested}")
        return requested
    memory = detect_hardware() if hardware is None else hardware
    for spec in candidates:
        if model_installed(spec.id, verify=verify) and recommended(spec.id, memory):
            return spec.id
    # If measurement could not confirm even a lightweight model, do not
    # choose an unverified high-memory model.
    return None
