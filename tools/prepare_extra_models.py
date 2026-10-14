"""BUILD TIME ONLY: retrieve and verify the optional-in-old-build, bundled AI tiers.

No runtime download happens. Fail the Windows build if a required model cannot
be retrieved or its pinned digest differs. Tokenizer comes from an immutable
upstream git revision; its build-time SHA-256 is written to the manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from local_ai_photo_editor.ai.catalog import (  # noqa: E402
    AI_FOLDER, ISNET_FILENAME, ISNET_MAX_BYTES, ISNET_SHA256,
    ISNET_SOURCE_URL, MANIFEST_NAME, WHISPER_FILES, WHISPER_MAX_BYTES,
    WHISPER_SOURCE_ROOT, WHISPER_TOKEN_MIN, WHISPER_TOKEN_MAX,
    model_file, model_installed,
)


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        if urlsplit(new_url).scheme != "https":
            raise ValueError("Refusing an insecure model download redirect.")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def _download(url: str, path: Path, expected: str | None, max_bytes: int) -> str:
    if path.is_symlink():
        raise ValueError("Refusing a symlink as model output.")
    if path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected is None or digest == expected:
            if 0 < path.stat().st_size <= max_bytes:
                return digest
        raise ValueError(f"Existing model artifact failed verification: {path.name}")
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.partial")
    digest = hashlib.sha256()
    length = 0
    try:
        opener = urllib.request.build_opener(HTTPSRedirects())
        with opener.open(url, timeout=180) as response, temporary.open("xb") as stream:
            while chunk := response.read(1024 * 1024):
                length += len(chunk)
                if length > max_bytes:
                    raise ValueError("Model exceeds its configured size limit.")
                digest.update(chunk)
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if length == 0 or (expected is not None and digest.hexdigest() != expected):
            raise ValueError(f"Downloaded artifact has wrong checksum: {path.name}")
        os.replace(temporary, path)
        return digest.hexdigest()
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    AI_FOLDER.mkdir(parents=True, exist_ok=True)
    _download(ISNET_SOURCE_URL, model_file("isnet-general-use"), ISNET_SHA256, ISNET_MAX_BYTES)
    token_sha = ""
    for name, sha in WHISPER_FILES.items():
        downloaded_sha = _download(
            WHISPER_SOURCE_ROOT + "/" + name,
            model_file("whisper-tiny", name), sha, WHISPER_MAX_BYTES,
        )
        if name == "tiny-tokens.txt":
            tokens = model_file("whisper-tiny", name)
            if not WHISPER_TOKEN_MIN <= tokens.stat().st_size <= WHISPER_TOKEN_MAX:
                raise ValueError("Unexpected Whisper tokenizer size.")
            token_sha = downloaded_sha
    manifest = AI_FOLDER / MANIFEST_NAME
    destination = manifest.with_name(manifest.name + ".partial")
    try:
        destination.write_text(
            json.dumps({"version": 1, "token_sha256": token_sha}, indent=2), encoding="utf-8"
        )
        os.replace(destination, manifest)
    finally:
        destination.unlink(missing_ok=True)
    for name in ("isnet-general-use", "whisper-tiny"):
        if not model_installed(name, verify=True):
            raise RuntimeError(f"Bundled model integrity check failed: {name}")
    print("Verified stronger IS-Net and multilingual Whisper Tiny for offline packaging.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
