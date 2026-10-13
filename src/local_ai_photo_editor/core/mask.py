"""Non-destructive foreground mask correction using locally rasterized brush strokes.

This module does not import Qt, inference engines, or networking modules.
Each stroke changes *only* the alpha channel. In particular, restoring a
portion of the foreground never synthesizes or paints RGB detail.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter

from .editing import _normalise_image

MAX_MASK_STROKES = 128
MAX_STROKE_POINTS = 2048
MODES = frozenset({"restore", "erase"})


@dataclass(frozen=True)
class MaskStroke:
    """One brush drag, in normalized image coordinates.

    diameter is a fraction of the shorter full-resolution image dimension;
    feather is the proportion of the edge that is softened (0 to 1).
    This representation keeps mouse strokes independent of preview scaling.
    """

    points: tuple[tuple[float, float], ...]
    mode: str
    diameter: float
    feather: float = 0.0


def _fraction(value: object, *, inclusive_zero: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("Brush settings and coordinates must be finite numbers.")
    result = float(value)
    if not math.isfinite(result) or result > 1 or (result < 0 if inclusive_zero else result <= 0):
        raise ValueError("Brush settings and coordinates must be in range.")
    return result


def _validate(stroke: MaskStroke) -> tuple[tuple[tuple[float, float], ...], float, float]:
    if not isinstance(stroke, MaskStroke) or not isinstance(stroke.mode, str) or stroke.mode not in MODES:
        raise ValueError("Invalid foreground brush mode.")
    if not isinstance(stroke.points, tuple) or not 1 <= len(stroke.points) <= MAX_STROKE_POINTS:
        raise ValueError("Invalid number of brush points.")
    diameter = _fraction(stroke.diameter, inclusive_zero=False)
    if diameter > 0.20:
        raise ValueError("Brush diameter is limited to 20% of the shorter image side.")
    feather = _fraction(stroke.feather, inclusive_zero=True)
    points: list[tuple[float, float]] = []
    for point in stroke.points:
        if not isinstance(point, tuple) or len(point) != 2:
            raise ValueError("Invalid brush coordinate.")
        x = _fraction(point[0], inclusive_zero=True)
        y = _fraction(point[1], inclusive_zero=True)
        points.append((x, y))
    return tuple(points), diameter, feather


def paint_alpha_strokes(image: Image.Image, strokes: Sequence[MaskStroke]) -> Image.Image:
    """Apply validated brush drags to alpha; preserve input and RGB pixels.

    Strokes are composited in order. A blurred brush blends alpha toward 255
    for restore or 0 for erase; the center of a hard brush is fully opaque.
    Undo or cancel is handled by the controller before this pure operation.
    The caller commits the final full-resolution image as one history step.
    """
    if not isinstance(strokes, (list, tuple)) or len(strokes) > MAX_MASK_STROKES:
        raise ValueError("Too many foreground brush strokes.")
    # Validate *all* strokes before allocating or processing image data.
    validated = [(s.mode, *_validate(s)) for s in strokes]
    prepared = _normalise_image(image)
    if prepared.mode != "RGBA":
        raise ValueError("Foreground mask editing requires an image with an alpha channel.")
    if not validated:
        return prepared

    alpha = prepared.getchannel("A")
    width, height = prepared.size
    for mode, points, diameter, feather in validated:
        # Coordinates are mapped to pixel centers, including the right/bottom
        # edge. They can be drawn in a smaller preview without changing meaning.
        centers = [(x * (width - 1), y * (height - 1)) for x, y in points]
        radius = max(0.5, min(width, height) * diameter * 0.5)
        blur = radius * feather * 0.5
        inner = max(0.5, radius - blur)
        # GaussianBlur has a nonzero tail; include enough padding to avoid
        # clipping visible pixels at the patch boundary.
        padding = radius + 4 * blur + 2
        x0 = max(0, math.floor(min(p[0] for p in centers) - padding))
        y0 = max(0, math.floor(min(p[1] for p in centers) - padding))
        x1 = min(width, math.ceil(max(p[0] for p in centers) + padding + 1))
        y1 = min(height, math.ceil(max(p[1] for p in centers) + padding + 1))
        box = (x0, y0, x1, y1)
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        draw = ImageDraw.Draw(mask)
        local = [(x - x0, y - y0) for x, y in centers]
        # Draw the centerline and circular end caps. Pillow performs raster
        # work natively; there are no Python loops over image pixels.
        if len(local) > 1:
            draw.line(local, fill=255, width=max(1, round(inner * 2)), joint="curve")
        for x, y in local:
            draw.ellipse((x - inner, y - inner, x + inner, y + inner), fill=255)
        if blur > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(blur))

        old_alpha = alpha.crop(box)
        target = Image.new("L", mask.size, 255 if mode == "restore" else 0)
        edited = Image.composite(target, old_alpha, mask)
        alpha.paste(edited, box)

    prepared.putalpha(alpha)
    return prepared
