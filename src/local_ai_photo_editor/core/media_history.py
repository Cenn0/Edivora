"""Bounded immutable media-edit history. Stores references/settings, not media bytes."""
from __future__ import annotations

from dataclasses import replace
import time

from .media_project import MediaSequence


def same_content(a: MediaSequence, b: MediaSequence) -> bool:
    return replace(a, selected_id=None) == replace(b, selected_id=None)


class MediaHistory:
    def __init__(self, initial: MediaSequence, limit: int = 60) -> None:
        if type(limit) is not int or not 2 <= limit <= 200:
            raise ValueError("Invalid media history limit.")
        self.limit = limit
        self.reset(initial)

    def reset(self, state: MediaSequence) -> None:
        self.states = [state]
        self.cursor = 0
        self._key = None
        self._time = 0.0

    def checkpoint(self) -> None:
        self._key = None
        self._time = 0.0

    @property
    def can_undo(self) -> bool:
        return self.cursor > 0

    @property
    def can_redo(self) -> bool:
        return self.cursor < len(self.states) - 1

    def select(self, selected_id: str | None) -> None:
        self.states[self.cursor] = replace(self.states[self.cursor], selected_id=selected_id)

    def record(self, state: MediaSequence, key: str | None = None) -> None:
        if same_content(self.states[self.cursor], state):
            self.states[self.cursor] = state
            return
        now = time.monotonic()
        coalesce = (key is not None and key == self._key and now - self._time < .65
                    and self.cursor > 0 and not self.can_redo)
        if coalesce:
            self.states[self.cursor] = state
        else:
            del self.states[self.cursor + 1:]
            self.states.append(state)
            del self.states[:-self.limit]
            self.cursor = len(self.states) - 1
        self._key, self._time = key, now

    def candidate(self, direction: int) -> MediaSequence:
        if direction not in (-1, 1):
            raise ValueError("Invalid history direction.")
        index = max(0, min(len(self.states) - 1, self.cursor + direction))
        return self.states[index]

    def undo(self) -> MediaSequence:
        if self.can_undo:
            self.cursor -= 1
        self._key = None
        return self.states[self.cursor]

    def redo(self) -> MediaSequence:
        if self.can_redo:
            self.cursor += 1
        self._key = None
        return self.states[self.cursor]
