![Edivora – Create simply. Stay local.](src/local_ai_photo_editor/assets/edivora-wordmark.svg)

# Edivora

**Simple, local photo, video and audio editing with selected on-device AI features.** Edivora is open source, with a German and English interface. **The repository is public, but redistribution of Windows packages is not approved.** Runtime processing is local; the application does not require accounts, cloud inference or automatic model downloads.

**Language:** [Deutsch](README.md) · English (this page)

![Edivora Photo, Video and Audio](src/local_ai_photo_editor/assets/edivora-banner.svg)

> **Source is not an approved binary release.** `main` contains the Photo/Video/Audio 0.4.0a1 development code. The former photo-only v0.1.0-alpha.1 package does not contain these features. Public Windows binaries remain blocked pending Qt, FFmpeg, model-weight redistribution review and clean Windows 11 acceptance.

## New in development source 0.4.0a1

**Direct launcher:** no selection checkboxes or bulk button. Open Photo, Video or Audio independently; the launcher stays open. Original local vector icons, compact toolbars, resizable previews and tabbed media settings. Long inspectors scroll instead of clipping. Minimum **640 × 480 logical pixels**.

**Improve video picture:** brightness, contrast, saturation, warmth, green/magenta tint, conventional noise smoothing and sharpening, with presets and real before/after still previews. Accepted per-clip recipes are saved in the project and applied during export; normal playback still shows the source. HD and Full HD export are selectable.

**Real local AI denoising:** DnCNN processes a selected section up to **30 seconds**, at most **720p / 30 fps**, on CPU. Adjustable strength, explicit preview/acceptance and a separate derived MP4. It may be slow, smooth detail or flicker. **Not a universal filter remover:** baked-in filters cannot be reliably reversed and missing original detail cannot be recovered exactly.

**Video and Audio:** Undo/Redo with up to 60 reference/settings states. New `.edvp/.edap` files use schema 2; schema 1 remains readable. Older applications cannot read schema 2.

[Workflow, limitations and provenance](docs/VIDEO_RESTORATION.md) · [0.4 change notes](docs/RELEASE_NOTES_RESPONSIVE_SUITE.md)

## Windows package status

**No Windows ZIP is currently approved for public redistribution.** Previously downloadable test binaries are being withdrawn until the exact Qt, FFmpeg and model-weight licensing obligations are resolved. CI results demonstrate selected technical checks only; they do not constitute legal clearance or a clean Windows 11 end-user acceptance. See [public release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Current source capabilities

| Workspace | Implemented | Not implemented / limit |
| --- | --- | --- |
| **Photo** | JPEG/PNG/WebP import/export, adjustments and looks, crop/rotate, original comparison and undo/redo, local U2NETP foreground selection, alpha-mask correction, editable `.laip` photo projects | No layers, RAW/HDR or generative prompt editing |
| **Video** | Single ordered lane with up to **24 clips**, trim/split/duplicate/reorder, `.edvp` linked-source projects, MP4 export, local segmentation of **one selected still frame** to PNG | No multitrack overlays, transitions, continuous full-sequence preview; 0.4 adds picture corrections and short-clip AI denoising, HD/Full HD at 30fps MPEG-4 Part 2 and AAC |
| **Audio** | Up to **24 clips** in one lane, trim/split/reorder, volume, optional normalization/fades, `.edap` projects, WAV/MP3 export, local **Silero VAD** speech-region suggestions | No multitrack mix, speech-to-text transcription or neural noise reduction |

One **launcher** starts Photo, Video and Audio in separate independent windows; open any one, any two or all three at once. Project files preserve editing state; exporting creates a **separate new media file**. `.edvp/.edap` reference source files rather than embedding them and may expose absolute local paths, so they are not automatically portable.

**AI scope:** The 0.4 source uses local, pinned **U2NETP, Silero VAD and DnCNN ONNX CPU** models. Classic image/audio adjustments are **not generative AI**. No application-level CUDA/DirectML/other GPU deployment has been verified; automatic GPU support should not be inferred from a compatible card. The proposed expanded model profiles in PR #17 are **not on `main`**.

## Historical photo-only alpha

The retired `v0.1.0-alpha.1` included only basic photo editing, not the Edivora launcher or media editors. Its historical Windows Server 2022 and offline checks are documented in [verification](docs/VERIFICATION.md); they do not certify the current suite.

## Run the latest development source

Use **Python 3.12**. Preparing pinned model weights is an **explicit build/developer step with network access**, never a silent application download.

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
