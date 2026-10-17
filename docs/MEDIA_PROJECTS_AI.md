# Edivora 0.4 – Clips, media projects and offline AI

Status: **implemented in current `main` source (0.4.0a1)**. The 0.4 source adds per-clip picture recipes, HD/Full HD rendering, bounded DnCNN CPU denoising, media Undo/Redo and strict project schema 2 with schema-1 compatibility. Ordinary playback remains the original source. See [the current 0.4 behavior and model limits](VIDEO_RESTORATION.md). The historical photo-only `v0.1.0-alpha.1` package does not contain these capabilities; public Windows binaries remain unapproved.
A passing Windows Server CI build is not clean Windows 11 or licensing approval.

## 1. Clip timeline (Video and Audio)

Each editor now supports an **ordered, draggable, single-lane arrangement of up
to 24 clips**. Import more files using **+ Clip** or drag and drop one local file
into the window. Select a card to preview that source in the Qt player. The
existing range timeline and start/end spin boxes always trim the *selected*
clip; controls remain non-destructive. The cards show sequence order, source
name, and their accepted trim range.

- Drag a card left/right to reorder, or use **Move left / Move right**.
- **Split at playhead** creates two adjacent ranges from the selected clip
  without changing the source. The playhead must be at least 100 ms from both
  ends. **Duplicate** copies the selected range with a unique ID.
- **Remove** removes only the reference from the session, not its media file.
- **Export** renders *all clips in the visible order*, not only the selected
  preview. Export selection is the complete arranged sequence.

The player previews **one selected clip at a time**. It does not yet play the
whole arrangement continuously, show one continuous composited A/V waveform,
overlay graphics, mix tracks, add transitions, or offer professional multi-
track editing. The list is a simple first timeline, not an NLE timeline.
There is no cut transition effect beyond hard cuts.

Video rendering standardizes each clip to selectable **HD (1280 × 720) or
Full HD (1920 × 1080), 30 fps, YUV420p, MPEG-4 Part 2** and AAC stereo. Inputs are scaled preserving aspect ratio and
letterboxed as needed. When a source has no audio (or is muted) the exporter
inserts local silence so the assembled output has consistent video/audio
streams. A standardized render can reduce image quality and frame rate compared with
the originals. This does not promise H.264 encoding or mobile compatibility.

Audio rendering resamples each selected segment to **48 kHz stereo**, applies
its individual volume setting, concatenates the segments, and applies
optional *global* loudness normalization and fades to the assembled output.
Export format is WAV PCM16 or MP3 at 192 kbit/s. All formats require an
available Qt playback decoder as well as the actual pinned FFmpeg encoder.

Both use one FFmpeg child process without a command shell. Cancel terminates
that encoder. Sources are guarded against direct, alias and hardlink
overwriting; successful render output replaces a temporary file in the chosen
directory atomically. Interrupted renders can leave a hidden
`.edivora-sequence-*.mp4/.wav/.mp3` file; successful and handled cancellations
delete their temporary files. Input multimedia decoding is not a security
sandbox.

MVP limits: max **24 clips**, individual reference max **2 h** and 20 GiB,
combined selected duration max **4 h**. Rendering can use significant CPU,
disk and memory; actual performance and video quality depend on hardware.

## 2. Editable projects

- **Video:** `.edvp` (Edivora Video Project)
- **Audio:** `.edap` (Edivora Audio Project)

Use **Save project** or **Save as** to persist the clip order, file references,
full source durations, in/out boundaries, per-clip volume/mute flags, selected
clip, audio master fades and normalization. **Open project** reconstructs
these settings. **Export** is separate and produces a regular media file.
When switching projects or closing with unsaved changes, the UI offers
**Save / Discard / Cancel**. A cancelled Save As dialog or unsuccessful write
blocks the switch/close instead of dropping edits.

The format is a small, versioned **UTF-8 JSON file**, *not* an archive
containing media payloads. Media files are never duplicated or modified.
References under the project directory are saved as simple relative paths.
Sources outside that directory are saved with absolute local paths; such
projects are **not portable**, and the project file may reveal personal folder
names. Save a project alongside its media (or organize clips into a sibling
subfolder) to keep relative references. Projects with moved or changed media now offer explicit **file relinking** when opened. Replacement files must match the recorded file size and first/last-64-KiB SHA-256 sample fingerprint; matching names are not sufficient. Cancelling or selecting a mismatched file leaves the active project intact. Relinked paths remain **unsaved changes** until the user saves the project. A sampled fingerprint is not a whole-file integrity proof. No automatic scanning or network search is performed.

On reopening, the application checks strict JSON fields, version and project
kind, a 256 KiB project size cap, max clip count, each source's type and path,
size and a SHA-256 fingerprint of the **first/last 64 KiB plus file size**.
This is a light changed-file check, **not a full-file integrity hash** and
not cryptographic proof that the middle of a large media file is unchanged.
An invalid or missing source fails closed without replacing the active
project. UNC/network file references and URL-like sources are rejected;
untrusted media files still reach native decoders when explicitly loaded.
Saves are written to a temporary local file and atomically replaced.

The project stores **accepted settings**, not a bitmap snapshot or an
undo/redo journal. It has no autosave or recovery log. Opening another
project or closing an editor after edits asks for confirmation if its
project was not saved.

## 3. Local AI: two genuinely model-backed workflows

**Audio – Detect speech segments (Silero VAD ONNX 6.2.1).** The app
decodes a selected audio region to mono 16 kHz using the bundled FFmpeg and
runs Silero's recurrent voice activity model **with local ONNX Runtime CPU**,
in a separate process. Detection is limited to **15 minutes per request**;
the audio is not transcribed. The UI shows the number of detected regions
and asks explicitly before replacing the selected clip with separate
speech-only ranges. Edges can still be refined manually afterwards. The
model can mistake breathing, music and noise for speech or miss quiet speech;
its detected cuts should be reviewed before export. It never edits source
audio until a new media file is exported.

**Video – Remove background from current still frame (U2NETP ONNX).** The
app extracts the *current frame*, runs the already bundled CPU foreground
segmentation model locally, and writes an independent transparent **PNG**.
It does **not** remove the background from the whole video, animate a mask,
track motion, or perform temporal video generation. The existing photo
editor can open and refine the resulting still image.

Both require their **bundled, checksum-verified** ONNX artifact; missing models
show an unavailable operation. A build-time tool retrieves the pinned
Silero model under HTTPS, validates its fixed length and SHA-256, and packages
the verified file and upstream MIT notice. There are **no runtime downloads,
subscriptions, external APIs, logins or telemetry**.

Silero model origin:
`snakers4/silero-vad@v6.2.1`,
`src/silero_vad/data/silero_vad.onnx`,
2,327,524 bytes, SHA-256
`1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.
Sources: [upstream source tag](https://github.com/snakers4/silero-vad/tree/v6.2.1),
[upstream MIT license](https://github.com/snakers4/silero-vad/blob/v6.2.1/LICENSE).
The existing U2NETP model has separate provenance limitations; see
[MODELS.md](MODELS.md) and [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## 4. Reproducibility and verification

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e . Nuitka==4.2.2
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
.venv\Scripts\python tools/prepare_model.py
.venv\Scripts\python tools/prepare_voice_model.py
.venv\Scripts\python -m local_ai_photo_editor --media-smoke-test test-results/media-suite
.venv\Scripts\python tools/build_windows.py
```

The **Windows alpha** GitHub workflow must pass both source and packaged
smoke tests with real synthetic clip concatenation, project round trips and
real local ONNX inference. The packaged runtime and exact artifact SHA should
be reviewed before even an unsigned development test distribution.
Clean Windows 11 validation, FFmpeg GPL/LGPL source/binary compliance, U2NETP
redistribution rights, DPI/accessibility and real-world codecs are separate
uncompleted release gates. Do not equate passing mocked unit tests with
real-model inference or package readiness.
