"""Resolve FFmpeg wrapper provenance from the installed distribution."""

from importlib import metadata


def installed_ffmpeg_provenance() -> tuple[str, str]:
    """Return package and engine labels using the wheel installed for this build.

    Propagate PackageNotFoundError: packaging without this distribution must fail.
    """
    version = metadata.version("imageio-ffmpeg")
    if not version or not version.strip():
        raise RuntimeError("Installed imageio-ffmpeg distribution has no version metadata")
    return f"imageio-ffmpeg=={version}", f"imageio-ffmpeg {version} standalone binary"
