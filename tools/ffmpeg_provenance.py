"""Resolve FFmpeg wrapper provenance from the installed distribution."""

from importlib import metadata
from pathlib import Path


def installed_ffmpeg_provenance() -> tuple[str, str]:
    """Return package and engine labels using the wheel installed for this build.

    Propagate PackageNotFoundError: packaging without this distribution must fail.
    """
    version = metadata.version("imageio-ffmpeg")
    if not version or not version.strip():
        raise RuntimeError("Installed imageio-ffmpeg distribution has no version metadata")
    return f"imageio-ffmpeg=={version}", f"imageio-ffmpeg {version} standalone binary"


def verified_bundled_ffmpeg_path(executable: str | Path, package_file: str | Path) -> Path:
    """Require the actual FFmpeg executable to originate from the installed wheel.

    get_ffmpeg_exe may select IMAGEIO_FFMPEG_EXE, Conda or system FFmpeg.
    None of those may be attributed to the imageio-ffmpeg wheel in manifests.
    Resolve symlinks before checking containment; never reveal candidate paths
    in public CI diagnostics.
    """
    failure = "FFmpeg executable is not a regular file in the installed imageio-ffmpeg wheel binaries"
    try:
        package_file_path = Path(package_file).resolve(strict=True)
        package_dir = package_file_path.parent
        binaries_dir = (package_dir / "binaries").resolve(strict=True)
        candidate = Path(executable).resolve(strict=True)
        if (not package_file_path.is_file() or binaries_dir.parent != package_dir
                or candidate.parent != binaries_dir or not candidate.is_file()):
            raise RuntimeError(failure)
    except (OSError, RuntimeError):
        raise RuntimeError(failure) from None
    return candidate
