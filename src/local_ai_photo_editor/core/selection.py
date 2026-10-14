"""Independent, reversible selections. Never changes photo RGB or alpha.

The journal stores bounded brush coordinates rather than full-size snapshots.
A grayscale rasterizer avoids constructing artificial full-size RGBA photos.
"""
from __future__ import annotations

import math
from typing import Callable

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .mask import MAX_MASK_STROKES, MaskStroke, _validate
from .recipes import _check_cancel
from .subject import validate_subject_mask

SelectionAction = MaskStroke | str
MAX_SELECTION_ACTIONS = MAX_MASK_STROKES
_COMMANDS = {"invert", "clear", "reset"}


def _validate_action(action: SelectionAction) -> None:
    if isinstance(action, MaskStroke):
        _validate(action)
    elif not isinstance(action, str) or action not in _COMMANDS:
        raise ValueError("Unknown selection action.")


class SelectionHistory:
    """Bounded undo/redo journal. Invalid writes must preserve existing redo."""
    def __init__(self) -> None:
        self._actions: list[SelectionAction] = []
        self._redo: list[SelectionAction] = []

    @property
    def actions(self) -> tuple[SelectionAction, ...]:
        return tuple(self._actions)

    @property
    def can_undo(self) -> bool:
        return bool(self._actions)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def push(self, action: SelectionAction) -> None:
        _validate_action(action)
        if len(self._actions) >= MAX_SELECTION_ACTIONS:
            raise ValueError("Selection correction limit reached.")
        self._actions.append(action)
        self._redo.clear()

    def undo(self) -> bool:
        if not self._actions:
            return False
        self._redo.append(self._actions.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._actions.append(self._redo.pop())
        return True


def _paint(mask: Image.Image, stroke: MaskStroke) -> None:
    """Paint into an owned L mask; share the established alpha brush geometry."""
    points, diameter, feather = _validate(stroke)
    width, height = mask.size
    centers = [(x * (width - 1), y * (height - 1)) for x, y in points]
    radius = max(.5, min(mask.size) * diameter * .5)
    blur = radius * feather * .5
    inner = max(.5, radius - blur)
    padding = radius + 4 * blur + 2
    left = max(0, math.floor(min(x for x, _ in centers) - padding))
    top = max(0, math.floor(min(y for _, y in centers) - padding))
    right = min(width, math.ceil(max(x for x, _ in centers) + padding + 1))
    bottom = min(height, math.ceil(max(y for _, y in centers) + padding + 1))
    box = (left, top, right, bottom)
    local = [(x - left, y - top) for x, y in centers]

    def coverage(r: float) -> Image.Image:
        image = Image.new("L", (right - left, bottom - top))
        draw = ImageDraw.Draw(image)
        if len(local) > 1:
            draw.line(local, fill=255, width=max(1, round(r * 2)), joint="curve")
        for x, y in local:
            draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        return image

    brush = coverage(inner)
    if blur > 0:
        brush = ImageChops.lighter(brush.filter(ImageFilter.GaussianBlur(blur)),
                                  coverage(max(.85, radius - blur * 1.5)))
    target = Image.new("L", brush.size, 255 if stroke.mode == "restore" else 0)
    mask.paste(Image.composite(target, mask.crop(box), brush), box)


def render_selection(baseline: Image.Image, actions: tuple[SelectionAction, ...], *,
                     cancelled: Callable[[], bool] | None = None) -> Image.Image:
    """Replay a validated journal at preview or full resolution on owned pixels."""
    if not isinstance(baseline, Image.Image):
        raise ValueError("Expected an 8-bit grayscale selection.")
    validate_subject_mask(baseline, baseline.size)
    if not isinstance(actions, tuple) or len(actions) > MAX_SELECTION_ACTIONS:
        raise ValueError("Invalid selection journal.")
    for action in actions:
        _validate_action(action)
    _check_cancel(cancelled)
    result = baseline.copy()
    result.info.clear()
    for action in actions:
        _check_cancel(cancelled)
        if isinstance(action, MaskStroke):
            _paint(result, action)
        elif action == "invert":
            result = ImageOps.invert(result)
        elif action == "clear":
            result.paste(0, (0, 0, result.width, result.height))
        else:
            result = baseline.copy()
            result.info.clear()
    _check_cancel(cancelled)
    return result
