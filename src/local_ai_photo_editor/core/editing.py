"""Local, metadata-free image operations used by the desktop application.

Images returned by this module contain 8-bit sRGB pixels, optionally with an
alpha channel. Untagged RGB, greyscale and palette images are treated as sRGB.
Other colour spaces require an embedded profile so that conversion does not
silently guess their colours.
"""

from __future__ import annotations

import math
import os
import tempfile
import warnings
from io import BytesIO
from numbers import Real
from pathlib import Path

from PIL import Image, ImageCms, ImageEnhance, ImageOps

MAX_IMAGE_PIXELS = 40_000_000
_SRGB_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
_SUPPORTED_MODES = {"1", "L", "LA", "P", "RGB", "RGBA", "CMYK", "LAB"}
_EXPORT_FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}


def _validate_dimensions(width: int, height: int) -> None:
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
    ):
        raise ValueError("Image dimensions must be positive integers.")
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError(f"Images are limited to {MAX_IMAGE_PIXELS:,} pixels.")


def _normalise_image(image: Image.Image) -> Image.Image:
    """Return owned, metadata-free sRGB pixels without modifying ``image``."""
    if not isinstance(image, Image.Image):
        raise TypeError("Expected a Pillow image.")
    _validate_dimensions(*image.size)
    if image.mode not in _SUPPORTED_MODES:
        raise ValueError(
            "This image mode is unsupported; use an 8-bit RGB or RGBA image."
        )

    # LAB's "A" band is a colour axis, not an alpha channel.
    has_alpha = image.mode in {"LA", "RGBA"} or "transparency" in image.info
    alpha = image.convert("RGBA").getchannel("A") if has_alpha else None

    if "icc_profile" in image.info:
        try:
            profile_data = image.info["icc_profile"]
            if not isinstance(profile_data, bytes) or not profile_data:
                raise ValueError("Empty or non-binary ICC profile.")
            source_profile = ImageCms.ImageCmsProfile(BytesIO(profile_data))
            if image.mode in {"CMYK", "LAB", "L"}:
                colour_image = image
            elif image.mode == "LA":
                colour_image = image.getchannel("L")
            else:
                colour_image = image.convert("RGB")
            converted = ImageCms.profileToProfile(
                colour_image,
                source_profile,
                _SRGB_PROFILE,
                outputMode="RGB",
            )
            if converted is None:
                raise ValueError("Colour conversion returned no image.")
        except (ImageCms.PyCMSError, OSError, TypeError, ValueError) as exc:
            raise ValueError(
                "The image contains an invalid or unsupported ICC colour profile."
            ) from exc
    else:
        if image.mode in {"CMYK", "LAB"}:
            raise ValueError(
                "CMYK and LAB images need a valid embedded ICC colour profile."
            )
        converted = image.convert("RGB")

    if alpha is not None:
        converted.putalpha(alpha)
    converted.info.clear()
    return converted


def load_image(path: str | Path) -> Image.Image:
    """Decode one still image, apply EXIF orientation and convert it to sRGB.

    The 40-megapixel limit is checked before decoding pixel data. Animated and
    multipage inputs are rejected instead of silently discarding their frames.
    EXIF, GPS, XMP and other input metadata are not retained in the result.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(Path(path).expanduser()) as opened:
                _validate_dimensions(*opened.size)
                if getattr(opened, "n_frames", 1) != 1:
                    raise ValueError("Open a still image; animated or multipage images are unsupported.")
                oriented = ImageOps.exif_transpose(opened)
                return _normalise_image(oriented)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError(f"Images are limited to {MAX_IMAGE_PIXELS:,} pixels.") from exc


def _validate_factor(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite, non-negative number.")
    factor = float(value)
    if not math.isfinite(factor) or factor < 0:
        raise ValueError(f"{name} must be a finite, non-negative number.")
    return factor


def adjust_image(
    image: Image.Image,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> Image.Image:
    """Apply brightness, contrast and saturation without changing alpha."""
    factors = (
        (_validate_factor(brightness, "Brightness"), ImageEnhance.Brightness),
        (_validate_factor(contrast, "Contrast"), ImageEnhance.Contrast),
        (_validate_factor(saturation, "Saturation"), ImageEnhance.Color),
    )
    prepared = _normalise_image(image)
    alpha = prepared.getchannel("A") if prepared.mode == "RGBA" else None
    result = prepared.convert("RGB")
    for factor, enhancement in factors:
        if factor != 1.0:
            result = enhancement(result).enhance(factor)
    if alpha is not None:
        result.putalpha(alpha)
    result.info.clear()
    return result


def rotate_image(image: Image.Image, quarter_turns: int = 1) -> Image.Image:
    """Rotate by exact quarter turns; positive values turn clockwise."""
    if isinstance(quarter_turns, bool) or not isinstance(quarter_turns, int):
        raise ValueError("Quarter turns must be an integer.")
    prepared = _normalise_image(image)
    operation = {
        1: Image.Transpose.ROTATE_270,
        2: Image.Transpose.ROTATE_180,
        3: Image.Transpose.ROTATE_90,
    }.get(quarter_turns % 4)
    return prepared.transpose(operation) if operation is not None else prepared


def crop_image(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Crop to an in-bounds rectangle ``(left, top, right, bottom)``."""
    if not isinstance(box, (tuple, list)) or len(box) != 4:
        raise ValueError("A crop needs four integer coordinates.")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in box):
        raise ValueError("A crop needs four integer coordinates.")
    left, top, right, bottom = box
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError("The crop must be a non-empty rectangle inside the image.")
    return _normalise_image(image).crop(box)


def resize_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize with Lanczos filtering while preserving transparency."""
    _validate_dimensions(width, height)
    return _normalise_image(image).resize((width, height), Image.Resampling.LANCZOS)


def _check_export_destination(target: Path, source: Path | None) -> None:
    if source is None:
        return
    if target.resolve() == source.resolve():
        raise ValueError("Export to a new filename; the original image is protected.")
    if target.exists() and source.exists() and target.samefile(source):
        raise ValueError("Export to a new file; this path points to the original image.")


def export_image(
    image: Image.Image,
    path: str | Path,
    source_path: str | Path | None = None,
) -> Path:
    """Atomically export PNG, JPEG or WebP without overwriting the source.

    Source aliases through symbolic links, ``..`` paths and hard links are
    protected too. JPEG transparency is composited onto white. Only a freshly
    generated sRGB ICC profile is included; input metadata is never copied.
    An existing unrelated export file is replaced only after encoding succeeds.
    """
    target = Path(path).expanduser().absolute()
    source = Path(source_path).expanduser() if source_path is not None else None
    output_format = _EXPORT_FORMATS.get(target.suffix.lower())
    if output_format is None:
        raise ValueError("Export supports PNG, JPEG and WebP filenames.")
    _check_export_destination(target, source)
    prepared = _normalise_image(image)
    if output_format == "JPEG" and prepared.mode == "RGBA":
        flattened = Image.new("RGB", prepared.size, "white")
        flattened.paste(prepared, mask=prepared.getchannel("A"))
        prepared = flattened

    options: dict[str, object] = {"icc_profile": _SRGB_PROFILE.tobytes()}
    if output_format == "JPEG":
        options.update(quality=95, subsampling=0)
    elif output_format == "WEBP":
        options.update(lossless=True, exact=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".local-ai-photo-editor-", suffix=".tmp", dir=target.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            prepared.save(stream, format=output_format, **options)
            stream.flush()
            os.fsync(stream.fileno())
        _check_export_destination(target, source)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return target
