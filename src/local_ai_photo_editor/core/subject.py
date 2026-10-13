"""Local image effects driven by a separately inferred subject selection."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps

from .editing import _normalise_image, _validate_dimensions
from .recipes import _check_cancel, _tiles

SUBJECT_MODES = ("blur", "color_pop", "light", "dim", "cutout", "crop")


@dataclass(frozen=True, slots=True)
class SubjectEdit:
    mode: str = "blur"
    strength: int = 60
    feather: int = 0
    padding: int = 12

    def __post_init__(self) -> None:
        if not isinstance(self.mode, str) or self.mode not in SUBJECT_MODES:
            raise ValueError("Unknown subject effect.")
        for name, maximum in (("strength", 100), ("feather", 100), ("padding", 40)):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError(f"{name} must be an integer from 0 to {maximum}.")

    @property
    def has_effect(self) -> bool:
        return self.mode in {"cutout", "crop"} or self.strength > 0


def validate_subject_mask(mask: Image.Image, size: tuple[int, int]) -> None:
    _validate_dimensions(*size)
    if not isinstance(mask, Image.Image) or mask.mode != "L" or mask.size != size:
        raise ValueError("A subject mask must be an 8-bit grayscale image matching the photo.")


def subject_bounds(mask: Image.Image, padding: int = 12, alpha: Image.Image | None = None) -> tuple[int, int, int, int]:
    """Enclose all selected visible regions, with a relative safety margin.

    Values >=128 define crop support; this is not a confidence score or a
    face/person-specific composition algorithm.
    """
    validate_subject_mask(mask, mask.size)
    SubjectEdit(mode="crop", padding=padding)
    support = mask.point(lambda value: 255 if value >= 128 else 0)
    if alpha is not None:
        validate_subject_mask(alpha, mask.size)
        support = ImageChops.multiply(support, alpha.point(lambda value: 255 if value else 0))
    box = support.getbbox()
    if box is None:
        raise ValueError("The selection contains no visible subject.")
    left, top, right, bottom = box
    margin = math.ceil(max(right - left, bottom - top) * padding / 100)
    return (max(0, left - margin), max(0, top - margin),
            min(mask.width, right + margin), min(mask.height, bottom + margin))


def effective_subject_mask(mask: Image.Image, feather: int = 0) -> Image.Image:
    validate_subject_mask(mask, mask.size)
    SubjectEdit(feather=feather)
    if not feather:
        return mask.copy()
    return mask.filter(ImageFilter.GaussianBlur(min(mask.size) * .006 * feather / 100))


def selection_overlay(image: Image.Image, mask: Image.Image) -> Image.Image:
    """Visual selection cue only; never used as final image data."""
    validate_subject_mask(mask, image.size)
    prepared = _normalise_image(image)
    overlay = Image.new("RGB", image.size, (161, 105, 240))
    result = Image.composite(overlay, prepared.convert("RGB"), mask.point(lambda value: round(value * .4)))
    if prepared.mode == "RGBA":
        result.putalpha(prepared.getchannel("A"))
    return result


def _blur_background(image: Image.Image, mask: Image.Image, strength: int,
                     cancelled: Callable[[], bool] | None) -> Image.Image:
    """Blur observed background colors without pulling opaque subject colors out.

    Premultiplied background colors and their weights are blurred together,
    then unpremultiplied. This reduces halos; it does not reconstruct occluded
    background or remove mask errors. Work is tiled with a filtering halo.
    """
    radius = min(image.size) * .02 * strength / 100
    margin = math.ceil(radius * 4) + 4
    rgb = image.convert("RGB")
    weights = ImageOps.invert(mask)
    if image.mode == "RGBA":
        weights = ImageChops.multiply(weights, image.getchannel("A"))
    result = Image.new("RGB", image.size)
    for left, top, right, bottom in _tiles(image.size):
        _check_cancel(cancelled)
        bounds = (max(0, left - margin), max(0, top - margin),
                  min(image.width, right + margin), min(image.height, bottom + margin))
        region = rgb.crop(bounds).convert("RGBA")
        region.putalpha(weights.crop(bounds))
        blurred = region.convert("RGBa").filter(ImageFilter.GaussianBlur(radius)).convert("RGBA")
        local = (left - bounds[0], top - bounds[1], right - bounds[0], bottom - bounds[1])
        blurred = blurred.crop(local)
        old = rgb.crop((left, top, right, bottom))
        valid = blurred.getchannel("A").point(lambda value: 255 if value else 0)
        backdrop = Image.composite(blurred.convert("RGB"), old, valid)
        result.paste(Image.composite(old, backdrop, mask.crop((left, top, right, bottom))), (left, top))
    return result


def render_subject(image: Image.Image, mask: Image.Image, edit: SubjectEdit, *,
                   cancelled: Callable[[], bool] | None = None) -> Image.Image:
    """Propose an edit without mutating the source image or its AI selection."""
    if not isinstance(edit, SubjectEdit):
        raise ValueError("Expected a SubjectEdit.")
    validate_subject_mask(mask, image.size)
    _check_cancel(cancelled)
    prepared = _normalise_image(image)
    if not edit.has_effect:
        return prepared
    selection = effective_subject_mask(mask, edit.feather)
    _check_cancel(cancelled)
    if edit.mode == "crop":
        alpha = prepared.getchannel("A") if prepared.mode == "RGBA" else None
        return prepared.crop(subject_bounds(selection, edit.padding, alpha))
    if edit.mode == "cutout":
        result = prepared.convert("RGBA")
        # Round alpha multiplication consistently with the existing AI adapter.
        alpha = np.asarray(result.getchannel("A"), dtype=np.uint16)
        selected = np.asarray(selection, dtype=np.uint16)
        result.putalpha(Image.fromarray(((alpha * selected + 127) // 255).astype(np.uint8)))
        return result
    if edit.mode == "blur":
        result = _blur_background(prepared, selection, edit.strength, cancelled)
    else:
        rgb = prepared.convert("RGB")
        result = Image.new("RGB", rgb.size)
        for box in _tiles(rgb.size):
            _check_cancel(cancelled)
            old = rgb.crop(box)
            if edit.mode == "color_pop":
                corrected = Image.blend(old, ImageOps.grayscale(old).convert("RGB"), edit.strength / 100)
                chosen = ImageOps.invert(selection.crop(box))
            else:
                factor = (2 ** (edit.strength / 100) if edit.mode == "light"
                          else 1 - .8 * edit.strength / 100)
                values = np.asarray(old, dtype=np.float32)
                corrected = Image.fromarray(np.clip(np.rint(values * factor), 0, 255).astype(np.uint8))
                chosen = selection.crop(box) if edit.mode == "light" else ImageOps.invert(selection.crop(box))
            result.paste(Image.composite(corrected, old, chosen), (box[0], box[1]))
    if prepared.mode == "RGBA":
        # Effects select colors, not opacity; hidden RGB values stay untouched.
        alpha = prepared.getchannel("A")
        result.paste(prepared.convert("RGB"), mask=alpha.point(lambda value: 255 if value == 0 else 0))
        result.putalpha(alpha)
    _check_cancel(cancelled)
    result.info.clear()
    return result
