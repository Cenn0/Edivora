"""Collect installed distribution notices into the build, never at app runtime."""

from __future__ import annotations

from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import sys


def collect(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    for distribution in sorted(metadata.distributions(), key=lambda d: d.metadata.get("Name", "").lower()):
        name = distribution.metadata.get("Name", "unknown")
        directory = destination / re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        copied = []
        for entry in distribution.files or ():
            parts = [part for part in entry.parts if part not in ("..", ".")]
            if not parts:
                continue
            basename = entry.name.upper()
            if not (basename.startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")) or "licenses" in entry.parts):
                continue
            source = Path(distribution.locate_file(entry))
            if not source.is_file():
                continue
            target = directory.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(target.relative_to(destination).as_posix())
        inventory.append({
            "name": name,
            "version": distribution.version,
            "license_expression": distribution.metadata.get("License-Expression"),
            "project_urls": distribution.metadata.get_all("Project-URL") or [],
            "notice_files": copied,
        })
    # Python itself is not a pip distribution.
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, destination / "PYTHON-LICENSE.txt")
    (destination / "installed-distributions.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/collect_licenses.py <output-directory>")
    collect(Path(sys.argv[1]))
