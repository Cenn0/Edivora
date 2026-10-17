"""Fail-closed, deterministic file inventory for private Windows package review.

This is artifact evidence, NOT an SBOM with resolved licenses, malware
assurance, binary provenance certification or permission to distribute.
Manifest stays outside the package it hashes to avoid recursive digests.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

MAX_FILES = 100_000
MAX_TOTAL_BYTES = 20 * 1024 ** 3
CHUNK_SIZE = 1024 * 1024


def category(relative: str) -> str:
    path = Path(relative)
    extension = path.suffix.casefold()
    if extension in {".onnx", ".safetensors", ".gguf", ".pth", ".pt"}:
        return "model"
    if extension in {".dll", ".pyd", ".so", ".dylib"}:
        return "native-library"
    if extension in {".exe", ".com", ".bat", ".cmd"}:
        return "executable"
    if path.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")):
        return "notice"
    if extension in {".md", ".rst", ".txt"}:
        return "documentation"
    return "other"


def _hash_regular_file(path: Path) -> tuple[int, str]:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Non-regular package file: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    after = path.lstat()
    if (not stat.S_ISREG(after.st_mode)
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        raise ValueError(f"Package file changed while hashing: {path.name}")
    return before.st_size, digest.hexdigest()


def build_inventory(package_dir: Path | str) -> dict:
    """Enumerate exact package bytes with bounded size, no absolute paths."""
    root = Path(package_dir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Package root must be a directory.")
    rows: list[dict] = []
    total = 0
    chain = hashlib.sha256()
    for entry in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        # Reject symlinks including directory links before entering native files.
        if entry.is_symlink():
            raise ValueError(f"Package contains a symbolic link: {entry.name}")
        if entry.is_dir():
            continue
        if not entry.is_file():
            raise ValueError(f"Package contains a special filesystem entry: {entry.name}")
        relative = entry.relative_to(root).as_posix()
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError("Unsafe relative package path.")
        if len(rows) >= MAX_FILES:
            raise ValueError("Package contains too many files.")
        size, digest = _hash_regular_file(entry)
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Package exceeds the audited size budget.")
        rows.append({"path": relative, "bytes": size, "sha256": digest,
                     "category": category(relative)})
        chain.update(relative.encode("utf-8") + b"\x00" + str(size).encode("ascii")
                     + b"\x00" + digest.encode("ascii") + b"\n")
    if not rows:
        raise ValueError("Package is empty.")
    return {
        "schema_version": 1,
        "scope": "exact files under packaged directory at inventory time",
        "sha256_manifest": chain.hexdigest(),
        "file_count": len(rows),
        "total_bytes": total,
        "public_redistribution_approved": False,
        "license_compliance": "NOT_REVIEWED",
        "caveats": [
            "Does not prove legal redistribution rights for Qt, FFmpeg or AI weights.",
            "Does not certify absence of vulnerabilities or unwanted network access.",
            "Manifest is external to scanned package; later added files require a new scan.",
        ],
        "files": rows,
    }


def write_inventory(package_dir: Path | str, manifest_path: Path | str) -> dict:
    """Write an evidence manifest atomically, outside the scanned directory."""
    root = Path(package_dir).expanduser().resolve(strict=True)
    requested = Path(manifest_path).expanduser().absolute()
    if requested.is_symlink() or not requested.parent.is_dir():
        raise ValueError("Inventory destination is invalid or a symlink.")
    # A Windows 8.3 temp directory (RUNNER~1) and its long spelling may
    # represent the SAME folder, even though Path equality says otherwise.
    # Canonicalize the parent before enforcing the outside-root invariant.
    target = requested.parent.resolve(strict=True) / requested.name
    if root == target or root == target.parent or root in target.parents:
        raise ValueError("Binary inventory must be written outside the package.")
    inventory = build_inventory(root)
    payload = (json.dumps(inventory, ensure_ascii=True, sort_keys=True, indent=2)
               + "\n").encode("utf-8")
    handle, temporary = tempfile.mkstemp(prefix=".edivora-inventory-",
                                         suffix=".json", dir=target.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise ValueError("Inventory destination changed into a symlink.")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return inventory


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("Usage: python tools/binary_inventory.py <package_dir> <out.json>")
    inventory = write_inventory(sys.argv[1], sys.argv[2])
    print(f"Inventory: {inventory['file_count']} files, {inventory['total_bytes']} bytes; "
          f"public redistribution NOT approved.")
