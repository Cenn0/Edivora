"""Resolve FFmpeg wrapper provenance from the installed distribution."""

import base64
import hashlib
import hmac
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
    """Accept only an FFmpeg binary recorded with a matching SHA-256 in the wheel.

    get_ffmpeg_exe may select IMAGEIO_FFMPEG_EXE, Conda or system FFmpeg.
    Directory containment alone would also accept a locally injected file.
    The installed wheel's RECORD hash is a local integrity check, not proof
    that the wheel itself came from a trusted publisher.
    Refuse absent RECORD/hash data and avoid echoing paths in CI errors.
    """
    failure = "FFmpeg executable is not a verified imageio-ffmpeg wheel binary"
    try:
        package_file_path = Path(package_file).resolve(strict=True)
        package_dir = package_file_path.parent
        binaries_dir = (package_dir / "binaries").resolve(strict=True)
        candidate = Path(executable).resolve(strict=True)
        if (not package_file_path.is_file() or binaries_dir.parent != package_dir
                or candidate.parent != binaries_dir or not candidate.is_file()):
            raise RuntimeError(failure)

        distribution = metadata.distribution("imageio-ffmpeg")
        records = distribution.files
        if not records:
            raise RuntimeError(failure)
        matching = [
            entry for entry in records
            if Path(entry).parts[:2] == ("imageio_ffmpeg", "binaries")
            and distribution.locate_file(entry).resolve(strict=True) == candidate
        ]
        if len(matching) != 1:
            raise RuntimeError(failure)
        recorded_hash = matching[0].hash
        if (recorded_hash is None or recorded_hash.mode != "sha256"
                or not recorded_hash.value):
            raise RuntimeError(failure)
        digest = hashlib.sha256()
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual_hash = base64.urlsafe_b64encode(digest.digest()).decode("ascii").rstrip("=")
        if not hmac.compare_digest(actual_hash, recorded_hash.value):
            raise RuntimeError(failure)
    except (OSError, TypeError, ValueError, RuntimeError, metadata.PackageNotFoundError):
        raise RuntimeError(failure) from None
    return candidate
