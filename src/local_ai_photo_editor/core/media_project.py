"""Non-destructive Edivora media clip sequence and bounded .edvp/.edap projects.

Unlike .laip photo archives, media project files link to existing local media.
No archive extraction, code execution, network access, or source modification.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import uuid

from .media import AUDIO_OUTPUTS, MAX_SOURCE_BYTES, MIN_SELECTION_MS, protects_source, validate_source

PROJECT_MAGIC = "edivora-media"
PROJECT_VERSION = 1
MAX_CLIPS = 24
MAX_PROJECT_BYTES = 256 * 1024
MAX_SEQUENCE_MS = 4 * 60 * 60 * 1000
MAX_SINGLE_MS = 2 * 60 * 60 * 1000
FINGERPRINT_SAMPLE = 65536
PROJECT_EXTENSIONS = {"audio": ".edap", "video": ".edvp"}


def _int(value: object, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Invalid {name}.")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"Invalid {name}.")
    return value


def _exact_dict(value: object, fields: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"Invalid {name} fields.")
    return value


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate keys are forbidden in media projects.")
        result[key] = value
    return result


def _allowed_path(path: Path) -> Path:
    raw = str(path)
    # Windows UNC, mapped network devices and URLs are not local-only media.
    if raw.startswith(("\\\\", "//")) or "://" in raw or "\x00" in raw:
        raise ValueError("Remote and special file references are not allowed.")
    if any(ord(ch) < 32 for ch in raw) or len(raw) > 4096:
        raise ValueError("Unsafe or excessively long media path.")
    return path


def fingerprint(path: Path) -> dict[str, object]:
    file = _allowed_path(Path(path)).resolve(strict=True)
    info = file.stat()
    if not file.is_file() or not 0 < info.st_size <= MAX_SOURCE_BYTES:
        raise ValueError("The media source is not a supported regular file.")
    checksum = hashlib.sha256()
    checksum.update(str(info.st_size).encode("ascii") + b"\x00")
    with file.open("rb") as stream:
        checksum.update(stream.read(FINGERPRINT_SAMPLE))
        if info.st_size > FINGERPRINT_SAMPLE:
            stream.seek(max(0, info.st_size - FINGERPRINT_SAMPLE))
            checksum.update(stream.read(FINGERPRINT_SAMPLE))
    return {"size": info.st_size, "sample_sha256": checksum.hexdigest()}


@dataclass(frozen=True)
class MediaClip:
    id: str
    source: Path
    duration_ms: int
    start_ms: int
    end_ms: int
    volume_percent: int = 100
    mute: bool = False
    has_audio: bool = True

    @classmethod
    def create(cls, kind: str, source: str | Path, duration_ms: int,
               *, start_ms: int = 0, end_ms: int | None = None,
               volume_percent: int = 100, mute: bool = False,
               has_audio: bool = True) -> "MediaClip":
        clip = cls(uuid.uuid4().hex, validate_source(_allowed_path(Path(source)), kind),
                   duration_ms, start_ms,
                   duration_ms if end_ms is None else end_ms, volume_percent, mute, has_audio)
        return clip.validated(kind)

    @property
    def length_ms(self) -> int:
        return self.end_ms - self.start_ms

    def validated(self, kind: str) -> "MediaClip":
        if not isinstance(self.id, str) or len(self.id) != 32:
            raise ValueError("Invalid clip ID.")
        try:
            if uuid.UUID(hex=self.id).hex != self.id:
                raise ValueError()
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid clip ID.") from exc
        validate_source(_allowed_path(self.source), kind)
        _int(self.duration_ms, MIN_SELECTION_MS, MAX_SINGLE_MS, "source duration")
        _int(self.start_ms, 0, self.duration_ms - MIN_SELECTION_MS, "start")
        _int(self.end_ms, self.start_ms + MIN_SELECTION_MS, self.duration_ms, "end")
        _int(self.volume_percent, 0, 200, "clip volume")
        _bool(self.mute, "mute")
        _bool(self.has_audio, "audio presence")
        if kind == "audio" and (self.mute or not self.has_audio):
            raise ValueError("Audio clips cannot be muted or have no audio.")
        return self


@dataclass(frozen=True)
class MediaSequence:
    kind: str
    clips: tuple[MediaClip, ...]
    selected_id: str | None = None
    normalize: bool = False
    fade_in_ms: int = 0
    fade_out_ms: int = 0

    def validated(self) -> "MediaSequence":
        if self.kind not in PROJECT_EXTENSIONS or not 1 <= len(self.clips) <= MAX_CLIPS:
            raise ValueError("Choose between 1 and 24 clips of one media kind.")
        ids = set()
        total = 0
        for clip in self.clips:
            clip.validated(self.kind)
            if clip.id in ids:
                raise ValueError("Duplicate clip IDs are not allowed.")
            ids.add(clip.id)
            total += clip.length_ms
        if total > MAX_SEQUENCE_MS:
            raise ValueError("The sequence exceeds the four-hour MVP limit.")
        if self.selected_id is not None and self.selected_id not in ids:
            raise ValueError("Selected clip does not exist.")
        _bool(self.normalize, "normalization")
        _int(self.fade_in_ms, 0, 60_000, "fade-in")
        _int(self.fade_out_ms, 0, 60_000, "fade-out")
        if self.kind == "video" and (self.normalize or self.fade_in_ms or self.fade_out_ms):
            raise ValueError("Audio-only master effects are not available on video projects.")
        if self.fade_in_ms + self.fade_out_ms > total:
            raise ValueError("Master fades cannot exceed the output duration.")
        return self

    @property
    def length_ms(self) -> int:
        return sum(clip.length_ms for clip in self.clips)

    def with_clips(self, clips: list[MediaClip], selected_id: str | None = None) -> "MediaSequence":
        return replace(self, clips=tuple(clips), selected_id=selected_id).validated()


def _source_reference(source: Path, project: Path) -> str:
    source = source.resolve(strict=True)
    directory = project.parent.resolve()
    try:
        return source.relative_to(directory).as_posix()
    except ValueError:
        # Explicit absolute external reference: editable, but not portable.
        return str(source)


def _resolve_reference(reference: object, project: Path) -> Path:
    if type(reference) is not str or not reference or len(reference) > 4096:
        raise ValueError("Invalid referenced media path.")
    _allowed_path(Path(reference))
    path = Path(reference)
    if not path.is_absolute():
        if "\\" in reference or ":" in reference:
            raise ValueError("Invalid relative media reference.")
        parts = PurePosixPath(reference).parts
        if not parts or ".." in parts or "." in parts:
            raise ValueError("Media reference must stay inside the project directory.")
        resolved = (project.parent / path).resolve(strict=True)
        if project.parent.resolve() not in resolved.parents:
            raise ValueError("Media reference escapes its project directory.")
    else:
        resolved = path.resolve(strict=True)
    return _allowed_path(resolved)


def _project_path(path: str | Path, kind: str) -> Path:
    out = _allowed_path(Path(path).expanduser().absolute())
    if kind not in PROJECT_EXTENSIONS or out.suffix.lower() != PROJECT_EXTENSIONS[kind]:
        raise ValueError("Incorrect media project filename extension.")
    if not out.parent.is_dir():
        raise ValueError("Project directory does not exist.")
    if out.is_symlink():
        raise ValueError("Refusing to replace a symlink project file.")
    return out


def save_media_project(sequence: MediaSequence, path: str | Path) -> None:
    seq = sequence.validated()
    project = _project_path(path, seq.kind)
    items = []
    for clip in seq.clips:
        source = validate_source(clip.source, seq.kind)
        items.append({
            "id": clip.id, "source": _source_reference(source, project),
            "fingerprint": fingerprint(source),
            "duration_ms": clip.duration_ms, "start_ms": clip.start_ms,
            "end_ms": clip.end_ms, "volume_percent": clip.volume_percent,
            "mute": clip.mute, "has_audio": clip.has_audio,
        })
    data = {
        "format": PROJECT_MAGIC, "version": PROJECT_VERSION,
        "kind": seq.kind, "clips": items, "selected_id": seq.selected_id,
        "normalize": seq.normalize, "fade_in_ms": seq.fade_in_ms,
        "fade_out_ms": seq.fade_out_ms,
    }
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    if len(payload) > MAX_PROJECT_BYTES:
        raise ValueError("Media project manifest is too large.")
    fd, temporary = tempfile.mkstemp(prefix=".edivora-project-", suffix=".tmp", dir=project.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if project.is_symlink():
            raise ValueError("Project destination changed into a symlink.")
        os.replace(temporary, project)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load_media_project(path: str | Path) -> MediaSequence:
    project = _allowed_path(Path(path).expanduser().absolute())
    if project.suffix.lower() not in PROJECT_EXTENSIONS.values():
        raise ValueError("Unsupported media project extension.")
    if not project.is_file() or project.stat().st_size > MAX_PROJECT_BYTES:
        raise ValueError("Project is missing or exceeds the allowed size.")
    with project.open("rb") as stream:
        raw = stream.read(MAX_PROJECT_BYTES + 1)
    if len(raw) > MAX_PROJECT_BYTES:
        raise ValueError("Project is too large.")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid project JSON.") from exc
    data = _exact_dict(data, {
        "format", "version", "kind", "clips", "selected_id",
        "normalize", "fade_in_ms", "fade_out_ms",
    }, "project")
    if data["format"] != PROJECT_MAGIC:
        raise ValueError("Not an Edivora media project.")
    _int(data["version"], PROJECT_VERSION, PROJECT_VERSION, "project version")
    kind = data["kind"]
    if kind not in PROJECT_EXTENSIONS or project.suffix.lower() != PROJECT_EXTENSIONS[kind]:
        raise ValueError("Project type and filename do not match.")
    rows = data["clips"]
    if type(rows) is not list or not 1 <= len(rows) <= MAX_CLIPS:
        raise ValueError("Invalid number of clips.")
    clips = []
    for row in rows:
        row = _exact_dict(row, {
            "id", "source", "fingerprint", "duration_ms", "start_ms",
            "end_ms", "volume_percent", "mute", "has_audio",
        }, "clip")
        src = _resolve_reference(row["source"], project)
        clip = MediaClip(
            row["id"], src, row["duration_ms"], row["start_ms"],
            row["end_ms"], row["volume_percent"], row["mute"], row["has_audio"],
        ).validated(kind)
        expected = _exact_dict(row["fingerprint"], {"size", "sample_sha256"}, "fingerprint")
        _int(expected["size"], 1, MAX_SOURCE_BYTES, "media size")
        if type(expected["sample_sha256"]) is not str or len(expected["sample_sha256"]) != 64:
            raise ValueError("Invalid fingerprint digest.")
        if fingerprint(src) != expected:
            raise ValueError(f"Media source changed or was replaced: {src.name}")
        clips.append(clip)
    selected_id = data["selected_id"]
    if selected_id is not None and type(selected_id) is not str:
        raise ValueError("Invalid selection ID.")
    return MediaSequence(
        kind, tuple(clips), selected_id,
        data["normalize"], data["fade_in_ms"], data["fade_out_ms"],
    ).validated()
