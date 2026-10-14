"""BUILD-TIME ONLY: fetch and verify the reviewed Silero VAD v6.2.1 ONNX file.

No application runtime downloads. The exact upstream tag, size and SHA-256
are pinned; incompatible or changed assets fail the build.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_ai_photo_editor.ai.voice import (  # noqa: E402
    VOICE_MODEL_SIZE, VOICE_MODEL_URL, verified_voice_model, voice_model_path,
)


class HttpsOnlyRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        if urlsplit(new_url).scheme != "https":
            raise ValueError("Refusing to fetch an AI model using non-HTTPS redirects.")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def main() -> int:
    target = voice_model_path()
    if target.is_file():
        verified_voice_model(target)
        print("Pinned Silero VAD model already present.")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".partial")
    try:
        opener = urllib.request.build_opener(HttpsOnlyRedirects())
        with opener.open(VOICE_MODEL_URL, timeout=90) as response:
            payload = response.read(VOICE_MODEL_SIZE + 1)
        if len(payload) != VOICE_MODEL_SIZE:
            raise ValueError("Unexpected Silero model file size.")
        temporary.write_bytes(payload)
        verified_voice_model(temporary)
        os.replace(temporary, target)
        print("Verified Silero v6.2.1 ONNX model for offline audio analysis.")
        return 0
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
