"""Keep model-conversion libraries out of the portable ONNX Runtime application.

This module is build-only and uses no application, Qt or inference imports.
Nuitka's report lists included modules as direct children; import-usage records
can also name intentionally excluded libraries and must not be mistaken for
included code.
"""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

BUILD_ONLY_PACKAGES = ("torch", "onnx")


def runtime_exclusion_arguments() -> list[str]:
    return [f"--nofollow-import-to={name}" for name in BUILD_ONLY_PACKAGES]


def verify_runtime_boundary(report_path: Path, package: Path) -> None:
    """Reject an incomplete report or accidentally included converter packages."""
    root = ET.parse(report_path).getroot()
    if root.tag != "nuitka-compilation-report" or root.get("completion") != "yes":
        raise RuntimeError("A completed Nuitka compilation report is required.")
    modules = {node.get("name", "") for node in root.findall("module")}
    if not modules:
        raise RuntimeError("Nuitka did not report included modules.")
    unexpected = sorted(name for name in modules
                        if any(name == excluded or name.startswith(excluded + ".")
                               for excluded in BUILD_ONLY_PACKAGES))
    if unexpected:
        raise RuntimeError("Build-only libraries entered the runtime: " + ", ".join(unexpected[:10]))
    # Extension modules/data may live outside the executable. Check directory
    # components as well, without confusing .onnx model files or onnxruntime
    # with the separate build-time 'onnx' Python package.
    for path in package.rglob("*"):
        if any(part.casefold() in BUILD_ONLY_PACKAGES for part in path.relative_to(package).parts):
            raise RuntimeError("Build-only package directory entered the runtime: "
                               + str(path.relative_to(package)))
