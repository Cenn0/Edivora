"""An in-memory image document with a bounded, reversible edit history."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .editing import _normalise_image

DEFAULT_HISTORY_BUDGET_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class _HistoryEntry:
    image: Image.Image
    label: str

    @property
    def size_bytes(self) -> int:
        # Document images are always 8-bit RGB or RGBA.
        return self.image.width * self.image.height * len(self.image.getbands())


class ImageDocument:
    """Keep the imported pixels separate from every edit.

    ``original`` and ``current`` return defensive copies. The default 256 MiB
    budget bounds the pixel payload held by undo and redo together, excluding
    the original and current images, Pillow overhead and temporary processing
    copies. Oldest undo states are discarded first, followed by the furthest
    redo states. An explicitly smaller budget can make a large edit impossible
    to undo or redo; a zero budget disables stored pixel history.

    ``history`` contains labels of applied edits, including edits whose old
    pixel snapshots have already been discarded. Reset is an undoable edit.
    """

    def __init__(
        self,
        image: Image.Image,
        source_path: str | Path | None = None,
        *,
        history_budget_bytes: int = DEFAULT_HISTORY_BUDGET_BYTES,
    ) -> None:
        if (
            isinstance(history_budget_bytes, bool)
            or not isinstance(history_budget_bytes, int)
            or history_budget_bytes < 0
        ):
            raise ValueError("The history byte budget must be a non-negative integer.")
        self._original = _normalise_image(image)
        self._current = self._original.copy()
        self._source_path = Path(source_path).expanduser().resolve() if source_path is not None else None
        self._history_budget_bytes = history_budget_bytes
        self._history_memory_bytes = 0
        self._undo: deque[_HistoryEntry] = deque()
        self._redo: deque[_HistoryEntry] = deque()
        self._labels: list[str] = []

    @property
    def original(self) -> Image.Image:
        return self._original.copy()

    @property
    def current(self) -> Image.Image:
        return self._current.copy()

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def history(self) -> tuple[str, ...]:
        return tuple(self._labels)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def history_budget_bytes(self) -> int:
        return self._history_budget_bytes

    @property
    def history_memory_bytes(self) -> int:
        return self._history_memory_bytes

    @property
    def undo_memory_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self._undo)

    def _trim_history(self) -> None:
        while self._history_memory_bytes > self._history_budget_bytes:
            if self._undo:
                discarded = self._undo.popleft()
            else:
                discarded = self._redo.popleft()
            self._history_memory_bytes -= discarded.size_bytes

    def apply(self, result: Image.Image, label: str) -> None:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("An edit needs a non-empty history label.")
        prepared = _normalise_image(result)
        self._history_memory_bytes -= sum(entry.size_bytes for entry in self._redo)
        self._redo.clear()
        entry = _HistoryEntry(self._current, label.strip())
        self._undo.append(entry)
        self._history_memory_bytes += entry.size_bytes
        self._current = prepared
        self._labels.append(entry.label)
        self._trim_history()

    def undo(self) -> bool:
        if not self._undo:
            return False
        previous = self._undo.pop()
        following = _HistoryEntry(self._current, previous.label)
        self._redo.append(following)
        self._history_memory_bytes += following.size_bytes - previous.size_bytes
        self._current = previous.image
        self._labels.pop()
        self._trim_history()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        following = self._redo.pop()
        previous = _HistoryEntry(self._current, following.label)
        self._undo.append(previous)
        self._history_memory_bytes += previous.size_bytes - following.size_bytes
        self._current = following.image
        self._labels.append(following.label)
        self._trim_history()
        return True

    def reset(self, label: str = "Reset to original") -> None:
        """Restore the original; callers may supply a translated history label."""
        self.apply(self._original, label)
