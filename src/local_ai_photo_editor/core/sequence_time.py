"""Exact non-Qt time mapping for one-lane media sequences.

A time point at a cut belongs to the next clip; the final sequence end is
valid only as an endpoint, never as a frame position. All input times use
integral milliseconds to avoid float rounding at repeated cuts.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from .media_project import MediaSequence


@dataclass(frozen=True)
class SequencePoint:
    clip_id: str
    index: int
    sequence_ms: int
    source_ms: int
    at_end: bool = False


class SequenceTimebase:
    """Stable index for a validated, ordered (non-overlapping) clip sequence."""

    def __init__(self, sequence: MediaSequence) -> None:
        sequence.validated()
        self.sequence = sequence
        self.starts = tuple(
            sum(clip.length_ms for clip in sequence.clips[:i])
            for i in range(len(sequence.clips))
        )
        self.ends = tuple(start + clip.length_ms for start, clip in zip(self.starts, sequence.clips))
        self.total_ms = self.ends[-1]
        self._indices = {clip.id: i for i, clip in enumerate(sequence.clips)}

    def at(self, sequence_ms: int) -> SequencePoint:
        if type(sequence_ms) is not int or not 0 <= sequence_ms <= self.total_ms:
            raise ValueError("Sequence position is outside the timeline.")
        at_end = sequence_ms == self.total_ms
        index = len(self.ends) - 1 if at_end else bisect_right(self.ends, sequence_ms)
        clip = self.sequence.clips[index]
        local = sequence_ms - self.starts[index]
        return SequencePoint(clip.id, index, sequence_ms, clip.start_ms + local, at_end)

    def to_sequence(self, clip_id: str, source_ms: int) -> int:
        if type(clip_id) is not str or clip_id not in self._indices:
            raise ValueError("Unknown timeline clip.")
        if type(source_ms) is not int:
            raise ValueError("Invalid source position.")
        index = self._indices[clip_id]
        clip = self.sequence.clips[index]
        if not clip.start_ms <= source_ms <= clip.end_ms:
            raise ValueError("Position is outside the selected source range.")
        return self.starts[index] + (source_ms - clip.start_ms)

    def clip_bounds(self, clip_id: str) -> tuple[int, int]:
        if clip_id not in self._indices:
            raise ValueError("Unknown timeline clip.")
        index = self._indices[clip_id]
        return self.starts[index], self.ends[index]
