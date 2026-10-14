"""Validated, non-destructive video corrections; no UI, models, or user filter syntax.

These are conventional image operations, not learned inverse filters. No operation
can recover clipped colors, erased detail, or the unknown original of a baked look.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VideoAdjustments:
    exposure: int = 0
    contrast: int = 0
    saturation: int = 0
    warmth: int = 0
    tint: int = 0
    denoise: int = 0
    sharpness: int = 0

    def validated(self) -> "VideoAdjustments":
        for key, value in asdict(self).items():
            low = 0 if key in ("denoise", "sharpness") else -100
            if type(value) is not int or not low <= value <= 100:
                raise ValueError(f"Invalid video adjustment: {key}.")
        return self

    @property
    def has_effect(self) -> bool:
        return any(asdict(self).values())

    def to_dict(self) -> dict[str, int]:
        self.validated()
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> "VideoAdjustments":
        if type(value) is not dict or set(value) != set(cls.__dataclass_fields__):
            raise ValueError("Unknown or missing video adjustment fields.")
        return cls(**value).validated()

    def filters(self) -> list[str]:
        """Only bounded numbers derived from typed fields enter the filter graph."""
        self.validated()
        result = []
        if self.exposure or self.contrast or self.saturation:
            result.append(f"eq=brightness={self.exposure / 250:.4f}:"
                          f"contrast={1 + self.contrast / 200:.4f}:"
                          f"saturation={1 + self.saturation / 100:.4f}")
        if self.warmth or self.tint:
            r = self.warmth / 800 + self.tint / 1600
            b = -self.warmth / 800 + self.tint / 1600
            g = -self.tint / 800
            values = ":".join(f"{channel}{tone}={amount:.5f}"
                              for tone in ("s", "m", "h")
                              for channel, amount in (("r", r), ("g", g), ("b", b)))
            result.append("colorbalance=" + values + ":pl=1")
        if self.denoise:
            # Spatial/temporal conventional denoising. A still preview cannot show
            # the temporal component; it is explicitly not labelled as neural AI.
            spatial = self.denoise / 20
            result.append(f"hqdn3d={spatial:.3f}:{spatial * .75:.3f}:"
                          f"{spatial * 1.5:.3f}:{spatial * 1.125:.3f}")
        if self.sharpness:
            result.append(f"unsharp=5:5:{self.sharpness / 150:.4f}:5:5:0")
        return result


PRESETS = {
    "original": VideoAdjustments(),
    "softer_look": VideoAdjustments(contrast=-15, saturation=-20),
    "clearer": VideoAdjustments(contrast=8, denoise=20, sharpness=25),
    "low_light": VideoAdjustments(exposure=15, denoise=35, sharpness=10),
}

EXPORT_SIZES = {"hd": (1280, 720), "full_hd": (1920, 1080)}


def bounded_scale(profile: str, *, preview: bool = False) -> str:
    if profile not in EXPORT_SIZES:
        raise ValueError("Unknown video size profile.")
    width, height = (640, 360) if preview else EXPORT_SIZES[profile]
    # Never upscale a small source. Round down to even dimensions for yuv420p.
    return (f"scale=w='min(iw,{width})':h='min(ih,{height})':"
            "force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1")
