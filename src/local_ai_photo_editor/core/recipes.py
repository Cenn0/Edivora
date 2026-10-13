"""Validated, non-destructive editing recipes. No Qt, inference or networking.

Colour corrections are display-referred 8-bit sRGB adjustments, not RAW/HDR
recovery. Every render starts from the supplied accepted image. Float arrays
are processed in bounded tiles rather than allocating several full-image arrays.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from math import ceil
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .editing import _normalise_image

LOOKS = ("none", "natural", "vivid", "soft", "warm", "mono", "sepia")
ASPECTS = {"original": None, "square": (1, 1), "4:3": (4, 3), "3:2": (3, 2),
           "16:9": (16, 9), "4:5": (4, 5), "9:16": (9, 16)}
_SIGNED = {"exposure", "contrast", "warmth", "saturation"}
_UNSIGNED = {"automatic", "shadows", "highlights", "sharpness", "vignette",
             "look_strength", "focus_x", "focus_y", "background_blur"}


class RenderCancelled(Exception):
    """A cooperative cancellation; no partial image should be accepted."""


@dataclass(frozen=True, slots=True)
class EditRecipe:
    exposure: int = 0
    contrast: int = 0
    automatic: int = 0
    shadows: int = 0
    highlights: int = 0
    warmth: int = 0
    saturation: int = 0
    sharpness: int = 0
    vignette: int = 0
    look: str = "none"
    look_strength: int = 100
    mirror: bool = False
    flip: bool = False
    quarter_turns: int = 0
    aspect: str = "original"
    focus_x: int = 50
    focus_y: int = 50
    background: str = "keep"
    background_color: tuple[int, int, int] = (255, 255, 255)
    background_blur: int = 0

    def __post_init__(self) -> None:
        for name in _SIGNED | _UNSIGNED | {"quarter_turns"}:
            value = getattr(self, name)
            low, high = (-100, 100) if name in _SIGNED else (0, 100)
            if name == "quarter_turns":
                high = 3
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer between {low} and {high}.")
        for name in ("mirror", "flip"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean.")
        if not isinstance(self.look, str) or self.look not in LOOKS:
            raise ValueError("Unknown look.")
        if not isinstance(self.aspect, str) or self.aspect not in ASPECTS:
            raise ValueError("Unknown crop ratio.")
        if self.background not in ("keep", "solid", "photo"):
            raise ValueError("Unknown background mode.")
        color = self.background_color
        if (not isinstance(color, tuple) or len(color) != 3
                or any(type(v) is not int or not 0 <= v <= 255 for v in color)):
            raise ValueError("Background color must contain three integer RGB values.")

    @property
    def has_effect(self) -> bool:
        tonal = _SIGNED | {"automatic", "shadows", "highlights", "sharpness", "vignette"}
        return (any(getattr(self, name) != 0 for name in tonal)
                or (self.look != "none" and self.look_strength > 0)
                or self.mirror or self.flip or self.quarter_turns != 0
                or self.aspect != "original" or self.background != "keep")

    def reset_section(self, section: str) -> EditRecipe:
        names = {
            "light": _SIGNED | {"automatic", "shadows", "highlights", "sharpness"},
            "look": {"look", "look_strength", "vignette"},
            "shape": {"mirror", "flip", "quarter_turns", "aspect", "focus_x", "focus_y"},
            "background": {"background", "background_color", "background_blur"},
        }.get(section)
        if names is None:
            raise ValueError("Unknown editing section.")
        defaults = EditRecipe()
        return EditRecipe(**{f.name: getattr(defaults if f.name in names else self, f.name)
                             for f in fields(self)})


def _check_cancel(cancel: Callable[[], bool] | None) -> None:
    if cancel is not None and cancel():
        raise RenderCancelled()


def auto_levels(image: Image.Image) -> tuple[int, int]:
    """Analyse visible pixels once so thumbnail and full renders share levels.

    Empty/near-constant histograms deliberately do nothing. Clipped pixels
    cannot be reconstructed. Fully transparent RGB values do not skew levels.
    """
    mask = image.getchannel("A") if image.mode == "RGBA" else None
    histogram = image.convert("L").histogram(mask=mask)
    total = sum(histogram)
    if total == 0:
        return (0, 255)
    cutoff = total * 0.005
    count, low, high = 0, 0, 255
    for index, value in enumerate(histogram):
        count += value
        if count > cutoff:
            low = index
            break
    count = 0
    for index in range(255, -1, -1):
        count += histogram[index]
        if count > cutoff:
            high = index
            break
    if high - low < 32:
        return (0, 255)
    return min(low, 48), max(high, 207)


def crop_box(size: tuple[int, int], recipe: EditRecipe) -> tuple[int, int, int, int]:
    """Largest in-bounds exact-ratio crop, positioned by beginner focus controls."""
    width, height = size
    if type(width) is not int or type(height) is not int or min(size) < 1:
        raise ValueError("Crop dimensions must be positive integers.")
    ratio = ASPECTS[recipe.aspect]
    if ratio is None:
        return (0, 0, width, height)
    rx, ry = ratio
    scale = min(width // rx, height // ry)
    if scale < 1:
        raise ValueError("The image is too small for this crop ratio.")
    crop_width, crop_height = scale * rx, scale * ry
    left = round((width - crop_width) * recipe.focus_x / 100)
    top = round((height - crop_height) * recipe.focus_y / 100)
    return left, top, left + crop_width, top + crop_height


def output_size(size: tuple[int, int], recipe: EditRecipe) -> tuple[int, int]:
    if recipe.quarter_turns % 2:
        size = size[::-1]
    left, top, right, bottom = crop_box(size, recipe)
    return right - left, bottom - top


def _look(pixels: np.ndarray, name: str) -> np.ndarray:
    if name == "none":
        return pixels
    luminance = (pixels[..., 0] * .2126 + pixels[..., 1] * .7152
                 + pixels[..., 2] * .0722)[..., None]
    if name == "mono":
        return np.repeat(luminance, 3, axis=2)
    if name == "sepia":
        matrix = np.array([[.393, .349, .272], [.769, .686, .534],
                           [.189, .168, .131]], dtype=np.float32)
        return np.clip(pixels @ matrix, 0, 1)
    if name == "soft":
        return (luminance + (pixels - luminance) * .9) * .88 + .06
    if name == "warm":
        return np.clip(pixels * np.array([1.09, 1.01, .91], dtype=np.float32), 0, 1)
    contrast, saturation = (1.06, 1.05) if name == "natural" else (1.12, 1.2)
    return np.clip((luminance + (pixels - luminance) * saturation - .5) * contrast + .5, 0, 1)


def _tiles(size: tuple[int, int]):
    """At most 262144 pixels per float tile, including extremely wide inputs."""
    width, height = size
    for top in range(0, height, 256):
        for left in range(0, width, 1024):
            yield left, top, min(width, left + 1024), min(height, top + 256)


def _tone(image: Image.Image, recipe: EditRecipe, levels: tuple[int, int],
          cancel: Callable[[], bool] | None) -> Image.Image:
    active = any(getattr(recipe, name) for name in
                 _SIGNED | {"automatic", "shadows", "highlights", "vignette"})
    active = active or (recipe.look != "none" and recipe.look_strength > 0)
    if not active:
        return image
    rgb = image.convert("RGB")
    result = Image.new("RGB", image.size)
    height, width = image.height, image.width
    for left, top, right, bottom in _tiles(image.size):
        _check_cancel(cancel)
        p = np.asarray(rgb.crop((left, top, right, bottom)), dtype=np.float32) / 255
        if recipe.automatic:
            low, high = levels
            corrected = np.clip((p * 255 - low) / (high - low), 0, 1)
            p += (corrected - p) * (recipe.automatic / 100)
        if recipe.exposure:
            p = np.clip(p * (2 ** (recipe.exposure / 100 * 1.5)), 0, 1)
        luminance = (p[..., 0] * .2126 + p[..., 1] * .7152 + p[..., 2] * .0722)[..., None]
        if recipe.shadows:
            p += (1 - luminance) ** 3 * (.42 * recipe.shadows / 100) * (1 - p)
        if recipe.highlights:
            p -= luminance ** 3 * (.45 * recipe.highlights / 100) * p
        if recipe.contrast:
            p = (p - .5) * (1 + recipe.contrast / 100 * .75) + .5
        if recipe.warmth:
            p[..., 0] *= 1 + recipe.warmth / 100 * .18
            p[..., 2] *= 1 - recipe.warmth / 100 * .18
        if recipe.saturation:
            luminance = (p[..., 0] * .2126 + p[..., 1] * .7152 + p[..., 2] * .0722)[..., None]
            p = luminance + (p - luminance) * (1 + recipe.saturation / 100)
        p = np.clip(p, 0, 1)
        if recipe.look != "none" and recipe.look_strength:
            p += (_look(p, recipe.look) - p) * (recipe.look_strength / 100)
        if recipe.vignette:
            x = (np.arange(left, right, dtype=np.float32) / (width - 1) * 2 - 1
                 if width > 1 else np.zeros(right - left, np.float32))[None, :]
            y = (np.arange(top, bottom, dtype=np.float32) / (height - 1) * 2 - 1
                 if height > 1 else np.zeros(bottom - top, np.float32))[:, None]
            falloff = ((x * x + y * y) / 2) ** 2
            p *= (1 - .65 * recipe.vignette / 100 * falloff)[..., None]
        band = Image.fromarray(np.clip(np.rint(p * 255), 0, 255).astype(np.uint8))
        result.paste(band, (left, top))
    if image.mode == "RGBA":
        result.putalpha(image.getchannel("A"))
    return result


def _sharpen(image: Image.Image, amount: int, cancel: Callable[[], bool] | None) -> Image.Image:
    """Alpha-aware unsharp masking; hidden colours cannot bleed into the subject."""
    if not amount:
        return image
    radius = max(.5, min(image.size) * .0015)
    margin = ceil(radius * 4) + 4
    result = Image.new(image.mode, image.size)
    for left, top, right, bottom in _tiles(image.size):
        _check_cancel(cancel)
        band_left, band_right = max(0, left - margin), min(image.width, right + margin)
        band_top, band_bottom = max(0, top - margin), min(image.height, bottom + margin)
        region = image.crop((band_left, band_top, band_right, band_bottom))
        working = region.convert("RGBa") if image.mode == "RGBA" else region
        blurred = working.filter(ImageFilter.GaussianBlur(radius))
        if image.mode == "RGBA":
            blurred = blurred.convert("RGBA")
        box = (left - band_left, top - band_top, right - band_left, bottom - band_top)
        original = region.crop(box)
        pixels = np.asarray(original.convert("RGB"), dtype=np.float32)
        difference = pixels - np.asarray(blurred.crop(box).convert("RGB"), dtype=np.float32)
        difference[np.abs(difference) < 3] = 0
        sharpened = Image.fromarray(np.clip(np.rint(pixels + difference * amount / 100 * 1.2), 0, 255).astype(np.uint8))
        if image.mode == "RGBA":
            alpha = original.getchannel("A")
            sharpened.paste(original.convert("RGB"), mask=alpha.point(lambda a: 255 if a == 0 else 0))
            sharpened.putalpha(alpha)
        result.paste(sharpened, (left, top))
    return result


def render_recipe(image: Image.Image, recipe: EditRecipe, *,
                  background_image: Image.Image | None = None,
                  levels: tuple[int, int] | None = None,
                  cancelled: Callable[[], bool] | None = None) -> Image.Image:
    """Render a fresh image. Cancellation raises without publishing partial pixels."""
    if not isinstance(recipe, EditRecipe):
        raise ValueError("Expected an EditRecipe.")
    _check_cancel(cancelled)
    prepared = _normalise_image(image)
    if levels is None:
        levels = auto_levels(prepared) if recipe.automatic else (0, 255)
    if (not isinstance(levels, tuple) or len(levels) != 2
            or any(type(v) is not int for v in levels)
            or not 0 <= levels[0] < levels[1] <= 255):
        raise ValueError("Automatic levels must be two ordered 8-bit integers.")
    if recipe.background != "keep":
        if prepared.mode != "RGBA" or prepared.getchannel("A").getextrema()[0] == 255:
            raise ValueError("Remove the background before replacing it.")
        if recipe.background == "photo" and background_image is None:
            raise ValueError("Choose a background photo first.")
    result = _tone(prepared, recipe, levels, cancelled)
    result = _sharpen(result, recipe.sharpness, cancelled)
    _check_cancel(cancelled)
    if recipe.mirror:
        result = ImageOps.mirror(result)
    if recipe.flip:
        result = ImageOps.flip(result)
    rotations = {1: Image.Transpose.ROTATE_270, 2: Image.Transpose.ROTATE_180,
                 3: Image.Transpose.ROTATE_90}
    if recipe.quarter_turns:
        result = result.transpose(rotations[recipe.quarter_turns])
    if recipe.aspect != "original":
        result = result.crop(crop_box(result.size, recipe))
    _check_cancel(cancelled)
    if recipe.background != "keep":
        if recipe.background == "solid":
            backdrop = Image.new("RGBA", result.size, (*recipe.background_color, 255))
        else:
            backdrop = _normalise_image(background_image).convert("RGBA")
            backdrop = ImageOps.fit(backdrop, result.size, method=Image.Resampling.LANCZOS)
            _check_cancel(cancelled)
            if recipe.background_blur:
                radius = min(result.size) * .04 * recipe.background_blur / 100
                backdrop = backdrop.convert("RGBa").filter(ImageFilter.GaussianBlur(radius)).convert("RGBA")
        _check_cancel(cancelled)
        result = Image.alpha_composite(backdrop, result.convert("RGBA"))
        if result.getchannel("A").getextrema() == (255, 255):
            result = result.convert("RGB")
    _check_cancel(cancelled)
    result.info.clear()
    return result
