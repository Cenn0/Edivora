"""Record installed Python package versions without local or credentialed source URLs.

This is a version-only diagnostic inventory, not a reproducible lockfile,
package SBOM, or evidence of redistribution rights.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
import re
from typing import Iterable


_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+!-]*\Z")


def render_version_inventory(distributions: Iterable | None = None) -> str:
    """Render only validated distribution names and versions, never origins."""
    if distributions is None:
        distributions = metadata.distributions()

    versions: dict[str, str] = {}
    for distribution in distributions:
        name = distribution.metadata.get("Name")
        version = distribution.version
        if (not isinstance(name, str) or not _NAME_RE.fullmatch(name)
                or not isinstance(version, str) or not _VERSION_RE.fullmatch(version)):
            raise ValueError("Invalid installed distribution name or version")
        canonical_name = re.sub(r"[-_.]+", "-", name).lower()
        if canonical_name in versions and versions[canonical_name] != version:
            raise ValueError("Conflicting installed distribution versions")
        versions[canonical_name] = version

    if not versions:
        raise ValueError("No installed distributions were found")
    header = (
        "# Installed Python package names and versions only.\n"
        "# Local paths, direct URLs, package origins and credentials are omitted.\n"
        "# This diagnostic inventory is not a lockfile or redistribution approval.\n"
    )
    return header + "".join(f"{name}=={versions[name]}\n" for name in sorted(versions))


def write_version_inventory(destination: Path) -> None:
    """Write the sanitized inventory; never invoke pip freeze for a package."""
    destination.write_text(render_version_inventory(), encoding="utf-8")
