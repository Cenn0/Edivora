![Edivora – Create simply. Stay local.](src/local_ai_photo_editor/assets/edivora-wordmark.svg)

# Edivora

**Edit photos, video and audio locally, with selected on-device AI tools.**

**Language:** **English** · [Deutsch](README.de.md)

![Edivora photo, video and audio editors](src/local_ai_photo_editor/assets/edivora-banner.svg)

Edivora is an open-source desktop suite with English and German interfaces. Editing happens locally, without an account or cloud AI. Models must be prepared separately before use; the application does not download them at runtime.

> **Development source: 0.4.0a1.** **No Windows package of the current suite has been approved for public redistribution.** Release approval requires, among other things, Qt/FFmpeg/model-license reviews and Windows 11 acceptance. Historical photo-only test packages do not include the current launcher or the video/audio editors.

## Features

| Editor | Implemented in the current source | Main limitations |
| --- | --- | --- |
| **Photo** | JPEG/PNG/WebP, color and light adjustments, looks, crop/rotate, before/after, undo/redo, local U2NETP subject masking and `.laip` projects | No layers, RAW/HDR or prompt-based generative editing |
| **Video** | Arrange, trim, split and duplicate up to 24 clips in one lane; picture adjustments, `.edvp` projects and MP4 export; local still-frame subject masking and short-clip DnCNN denoising | No multitrack editing, transitions or continuous full-sequence preview |
| **Audio** | Up to 24 clips in one lane; trimming, levels, fades, WAV/MP3 export, `.edap` projects and local Silero VAD speech-region suggestions | No multitrack mixing, transcription or neural noise reduction |

The launcher can open Photo, Video and Audio in **separate windows** while remaining open. Export creates a separate file rather than intentionally overwriting the original.

**AI boundaries:** On CPU, DnCNN processes selected video sections of up to **30 seconds, 720p and 30 fps**. Processing may remove detail or cause flicker. Baked-in filters and lost image detail cannot be reliably reversed. **GPU/CUDA/DirectML operation has not been verified by this project.** `.edvp` and `.edap` project files reference source media and may contain absolute local paths.

## Run from source

The current development instructions use **Python 3.12**. From the repository root on Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python tools\prepare_voice_model.py
.venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install onnx==1.23.2
.venv\Scripts\python tools\prepare_restoration_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Model preparation requires network access and checks pinned model artifacts. The final command launches the editor selection window. Use `--tool photo`, `--tool video` or `--tool audio` to launch one editor directly.

The Windows development build is still called `LocalAiPhotoEditor.exe` and needs its accompanying directory. An approved downloadable `Edivora.exe` is **not** claimed. See [Getting started](docs/GETTING_STARTED.md).

## Develop and test

The main stack is **Python 3.12**, **PySide6/Qt**, **Pillow/NumPy**, **ONNX Runtime (CPU)** and **FFmpeg** for media export.

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
```

Automated checks cover specific cases; they do not establish model quality, safe media decoding or approval for redistributed Windows binaries. Treat incoming media as **untrusted**.

## Documentation

[Getting started](docs/GETTING_STARTED.md) · [Media projects and AI](docs/MEDIA_PROJECTS_AI.md) · [Models](docs/MODELS.md) · [Video restoration](docs/VIDEO_RESTORATION.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](docs/CONTRIBUTING.md) · [Security policy](SECURITY.md)

## License and distribution

Application source code is licensed under [Apache-2.0](LICENSE). **Qt, FFmpeg, AI models and other third-party components have separate terms.** Public binary distribution requires a further compliance review. See [third-party notices](THIRD_PARTY_NOTICES.md) and the [public release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).
