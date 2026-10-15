![Edivora – Create simply. Stay local.](src/local_ai_photo_editor/assets/edivora-wordmark.svg)

# Edivora

**Simple, local photo, video and audio editing with selected on-device AI features.** Edivora is being developed as a free, open-source desktop toolkit with German and English UI. **The source repository is public**, but public redistribution of Windows binaries has not yet been cleared. No account, cloud model server or runtime model downloads are needed.

**Language:** [Deutsch](README.md) · English (this page)

![Edivora Photo, Video and Audio](src/local_ai_photo_editor/assets/edivora-banner.svg)

> **Public source code does not imply approved Windows binaries.** The current `main` branch contains the 0.3.0a1 Photo/Video/Audio development suite. The earlier photo-only `v0.1.0-alpha.1` is not equivalent. Previously downloadable binaries are being withdrawn pending redistribution clearance for Qt, FFmpeg and model weights.

## Windows download status

**There is no currently approved publicly redistributable Windows ZIP.** Standalone builds include third-party binaries, Qt and model weights with separate legal terms. See [third-party notices](THIRD_PARTY_NOTICES.md), [roadmap](docs/ROADMAP.md) and [run from source](docs/GETTING_STARTED.md). Successful CI is not a license clearance or Windows 11 end-user certification.

[Repository](https://github.com/Cenn0/Edivora) · [CI status](https://github.com/Cenn0/Edivora/actions) · [Contributing](docs/CONTRIBUTING.md)

## Current source capabilities

| Workspace | Implemented | Not implemented / limit |
| --- | --- | --- |
| **Photo** | JPEG/PNG/WebP import/export, adjustments and looks, crop/rotate, original comparison and undo/redo, local U2NETP foreground selection, alpha-mask correction, editable `.laip` photo projects | No layers, RAW/HDR or generative prompt editing |
| **Video** | Single ordered lane with up to **24 clips**, trim/split/duplicate/reorder, `.edvp` linked-source projects, MP4 export, local segmentation of **one selected still frame** to PNG | No multitrack overlays, transitions, continuous full-sequence preview or full-video AI; export standardizes to 1280×720/30fps MPEG-4 Part 2 and AAC |
| **Audio** | Up to **24 clips** in one lane, trim/split/reorder, volume, optional normalization/fades, `.edap` projects, WAV/MP3 export, local **Silero VAD** speech-region suggestions | No multitrack mix, speech-to-text transcription or neural noise reduction |

One **launcher** starts Photo, Video and Audio in separate independent windows; open any one, any two or all three at once. Project files preserve editing state; exporting creates a **separate new media file**. `.edvp/.edap` reference source files rather than embedding them and may expose absolute local paths, so they are not automatically portable.

**AI scope:** Current `main` uses local, pinned **U2NETP and Silero VAD ONNX CPU** models. Classic image/audio adjustments are **not generative AI**. No application-level CUDA/DirectML/other GPU deployment has been verified; automatic GPU support should not be inferred from a compatible card. The proposed expanded model profiles in PR #17 are **not on `main`**.

## Historical photo-only alpha

The retired `v0.1.0-alpha.1` contained only the old photo editor, not the launcher or video/audio tools. The previously measured 69 Windows Server 2022 tests and offline CPU inference are retained as historical evidence, not approval of new features. [Historical verification](docs/VERIFICATION.md).

## Run the latest development source

Use **Python 3.12**. Preparing pinned model weights is an **explicit build/developer step with network access**, never a silent application download.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python tools\prepare_voice_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Directly launch a workspace:

```powershell
.venv\Scripts\python -m local_ai_photo_editor --tool photo
.venv\Scripts\python -m local_ai_photo_editor --tool video
.venv\Scripts\python -m local_ai_photo_editor --tool audio
```

The current development Windows build still names its executable **`LocalAiPhotoEditor.exe`**, despite Edivora branding. It is a **standalone directory**, not a one-file binary; keep its bundled Qt, models and FFmpeg files together.

## Contributing and safety boundaries

- **Originals are never intentionally overwritten.** Exports are validated and atomically installed after rendering. Native media decoders are **not** a sandbox; source files, project manifests and ZIP archives must be treated as untrusted.
- No account, telemetry, runtime-cloud inference or remote image/audio/video upload is built into the app. A user-selected synced export folder may still be synced by third-party software.
- Source modules: `ui/` (Qt and DE/EN strings), `core/` (Qt-free image/media logic and format validation), `ai/` (bounded, locally verified models), plus separate worker/FFmpeg processes.
- The code is **Apache-2.0**. Qt, FFmpeg and model artifacts have separate licensing, attribution and redistribution requirements; a new public Windows suite must pass those checks.

Start with [AGENTS.md](AGENTS.md), [contributor guide](docs/CONTRIBUTING.md), [architecture](docs/ARCHITECTURE.md), [media-project details](docs/MEDIA_PROJECTS_AI.md), [brand assets](docs/BRAND.md), [roadmap](docs/ROADMAP.md), and the [documentation index](docs/README.md). Distinguish implemented source, verified tests, distributed packages and official support.
