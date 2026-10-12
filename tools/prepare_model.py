"""BUILD-TIME ONLY: obtain and verify the single model included in the package."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_ai_photo_editor.ai.models import (  # noqa: E402
    MODEL_SIZE, MODEL_URL, UPSTREAM_MD5, model_path, verified_model_bytes,
)


class HttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        if urlsplit(new_url).scheme != "https":
            raise ValueError("Refusing a model download redirect outside HTTPS.")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def main() -> int:
    target = model_path()
    if target.exists():
        verified_model_bytes(target)
        print("Bundled model already verified.")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".onnx.partial")
    try:
        opener = urllib.request.build_opener(HttpsRedirectHandler())
        with opener.open(MODEL_URL, timeout=90) as response:
            data = response.read(MODEL_SIZE + 1)
        if len(data) != MODEL_SIZE:
            raise ValueError("The model download has an unexpected size.")
        # Compatibility with the upstream rembg artifact; runtime uses SHA-256.
        if hashlib.md5(data, usedforsecurity=False).hexdigest() != UPSTREAM_MD5:
            raise ValueError("The download differs from the upstream rembg model.")
        temporary.write_bytes(data)
        verified_model_bytes(temporary)
        os.replace(temporary, target)
        print("Verified U2NETP model prepared for the offline package.")
        return 0
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

