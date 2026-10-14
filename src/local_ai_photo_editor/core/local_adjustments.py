"""Conventional local adjustments on either an AI or a painted selection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import Image

from .editing import _normalise_image
from .recipes import EditRecipe, _check_cancel, render_recipe
from .subject import (SUBJECT_MODES, SubjectEdit, effective_subject_mask,
                      render_subject, validate_subject_mask)

LOCAL_MODES = (*SUBJECT_MODES, "warm", "cool", "vivid", "muted")
DEFAULT_STRENGTH = {"blur": 60, "color_pop": 100, "light": 35, "dim": 45,
                    "cutout": 100, "crop": 100, "warm": 35, "cool": 35,
                    "vivid": 35, "muted": 50}


@dataclass(frozen=True, slots=True)
class LocalEdit:
    mode: str = "light"
    strength: int = 35
    feather: int = 0
    padding: int = 12

    def __post_init__(self) -> None:
        if not isinstance(self.mode, str) or self.mode not in LOCAL_MODES:
            raise ValueError("Unknown local effect.")
        # Reuse the existing bounds and strict integer checks.
        SubjectEdit(strength=self.strength, feather=self.feather, padding=self.padding)

    @property
    def has_effect(self) -> bool:
        return self.mode in {"cutout", "crop"} or self.strength > 0


def render_local(image: Image.Image, mask: Image.Image, edit: LocalEdit, *,
                 cancelled: Callable[[], bool] | None = None) -> Image.Image:
    """Apply one effect, leaving unselected and hidden colors exact.

    Existing background effects intentionally act on the complement of the
    selection. New warmth/color controls always act on the selected region.
    """
    if not isinstance(edit, LocalEdit):
        raise ValueError("Expected a LocalEdit.")
    validate_subject_mask(mask, image.size)
    _check_cancel(cancelled)
    if edit.mode in SUBJECT_MODES:
        return render_subject(image, mask, SubjectEdit(edit.mode, edit.strength, edit.feather, edit.padding),
                              cancelled=cancelled)
    prepared = _normalise_image(image)
    if not edit.has_effect:
        return prepared
    recipe = {
        "warm": EditRecipe(warmth=edit.strength),
        "cool": EditRecipe(warmth=-edit.strength),
        "vivid": EditRecipe(saturation=round(edit.strength * .8)),
        "muted": EditRecipe(saturation=-edit.strength),
    }[edit.mode]
    corrected = render_recipe(prepared, recipe, cancelled=cancelled)
    _check_cancel(cancelled)
    selection = effective_subject_mask(mask, edit.feather)
    result = Image.composite(corrected.convert("RGB"), prepared.convert("RGB"), selection)
    if prepared.mode == "RGBA":
        alpha = prepared.getchannel("A")
        result.paste(prepared.convert("RGB"), mask=alpha.point(lambda value: 255 if value == 0 else 0))
        result.putalpha(alpha)
    _check_cancel(cancelled)
    result.info.clear()
    return result
