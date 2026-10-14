# Video picture improvements and local restoration (0.4 development)

This documents the 0.4 source, not the historical 0.1/0.3 downloads. A source
feature, a passing test, a standalone package check and a Windows 11 product
release are different milestones. Current package evidence belongs to the
specific successful Windows alpha workflow and its `verification` directory.

## Workflow

Open Video directly in the launcher; the launcher remains open. Import a video,
select a clip and its start/end, then select **Picture → Improve picture**
(**Bild → Bild verbessern**). Existing playback shows the original source;
accepted picture corrections are visible in the comparison dialog and export,
not as live filters over Qt playback.

The dialog computes a real decoded still, up to 640 × 360, in a separate process.
Adjustments invalidate that preview. **Apply** only becomes available after the
current settings have been previewed. Compare with the original, then apply or
cancel. No original media is overwritten.

### Conventional corrections — not AI

Brightness, contrast, saturation, warmth, green/magenta tint, conventional
spatial/temporal noise smoothing and sharpening use fixed numeric FFmpeg
filters (`eq`, `colorbalance`, `hqdn3d`, `unsharp`). Presets provide an adjustable
starting point for a strong look, a dark recording or a clearer image.

These can **soften the appearance of an embedded color filter**, not recover
its unknown inverse. Clipped colors, deleted detail, beauty smoothing or
geometric edits cannot be reliably reconstructed. An Edivora correction that
has not been baked into a new file can be reset or undone exactly. Resetting
an imported, already-filtered video does not reveal its original pixels.

Corrections remain a per-clip recipe until sequence export. Temporal smoothing
cannot be assessed from one still. The preview is lower resolution, so inspect
an exported short section before processing important footage. The new HD and
Full HD sequence profiles use 1280 × 720 or 1920 × 1080, at 30 fps, MPEG-4 Part 2
video and AAC audio. Increasing output dimensions is **not AI upscaling** and
cannot recover missing detail; existing aspect-ratio-preserving letterboxing
remains. There are no new H.264 or GPU-support claims.

### Local AI — real DnCNN denoising

Enable **Local AI → AI denoising · DnCNN**, choose strength, and calculate a new
preview. **Create AI clip** then requests a separate MP4 destination, processes
the selected range, and replaces the clip reference only after successful
completion. The source audio is retained when present; existing clip volume and
mute settings remain separate. Corrections are baked once into the derived
clip and its recipe is reset to avoid double application.

Limits: **30 seconds per selected AI range**, at most **720p**, fixed **30 fps**,
CPU execution only, one frame at a time, tiled inference (160-pixel core,
20-pixel context). Frames smaller than 720p are not upscaled by the AI job.
Preview and rendering can be slow. This is a single-frame RGB denoiser, **not a
temporally trained video model, generic filter remover, deblurring model,
face restoration model or generator**. It can oversmooth detail or flicker.
A good synthetic noise test is not evidence of perceptual quality on all videos.

The model is unavailable if its fixed file/hash does not match. Conventional
corrections still work. Nothing is downloaded at application runtime. Model
profiles/Whisper proposed separately in PR #17 are not implied by this feature.

## State, undo and project compatibility

Media Undo/Redo stores at most 60 states of clip references/settings, not video
bytes. Use Ctrl+Z and Ctrl+Shift+Z / Ctrl+Y. Split, duplicate, reorder, trim,
volume/mute and corrections are recoverable within the session; media Undo is
not persisted. A saved checkpoint remains distinguishable from unsaved edits.
Missing source files are rejected before moving the history cursor.

`.edvp/.edap` writers now use **schema version 2**; readers accept strict version
1 and 2. Version 1 loads with a neutral correction recipe. Older 0.3 readers
cannot read version 2; keep a copy before saving with 0.4 when sharing with an
older application. Projects reference media files, including derived AI clips;
keep these files available. Undoing a derived clip does not delete its exported
MP4. A project is not an archive of source/derived media and can expose absolute
local paths. No autosave or automatic relinking was added.

## Window behavior and accessibility

Launcher selections and the bulk-open button are removed. Three direct actions
remain available, with Alt+1/2/3 shortcuts, and the launcher does not close when
a tool starts. Existing tools run independently.

The supported minimum is **640 × 480 logical pixels**. Qt handles physical DPI
scaling. Main commands remain in fixed chrome; previews expand, toolbars switch
to compact icons, and media settings are grouped into tabs. Larger inspector
content scrolls vertically rather than forcing controls outside the window.
Not every option can be simultaneously visible at the smallest size; all are
reachable in their tab/scroll area. Icon-only actions retain translated
accessible names and tooltips. Original vector icons are local; no icon font,
font download or CDN is required. Initial window sizing respects the available
logical desktop. A desktop smaller than the minimum is not a supported layout.

## Model provenance and developer preparation

Original author: Kai Zhang / `cszn/KAIR`, `dncnn_color_blind.pth`, release `v1.0`.
The upstream KAIR code carries an MIT licence; its complete notice is shipped
as `models/DNCNN_LICENSE.txt`. Preserve the notice and original source link.
The complete package still has separate Qt/FFmpeg/model redistribution gates.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| Author's PTH (build-only) | 2,678,121 bytes | `dfe11a6b703304df82cdf236f431fc6492766c7b9119d97e943edeb392c710a3` |
| Deterministic ONNX (runtime) | 2,677,066 bytes | `b6a7d59f4ce2ada940dcd78bd627595c59c5180a9c6d7787fa153198d2f50c12` |

`tools/prepare_restoration_model.py` downloads bounded HTTPS bytes, checks the
source hash **before** `torch.load(..., weights_only=True)`, validates every
key/shape/finite float, constructs an ONNX opset-17 / IR-8 graph and verifies the
exact output hash. Only this build tool uses PyTorch/ONNX conversion dependencies;
the desktop runtime loads verified ONNX bytes using ONNX Runtime CPU.

```powershell
.venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install onnx==1.23.2
.venv\Scripts\python tools\prepare_restoration_model.py
.venv\Scripts\python -m local_ai_photo_editor --suite-smoke-test test-results\source-suite
```

The initial conversion was executed in [run 38644618848](https://github.com/Cenn0/Edivora/actions/runs/38644618848):
maximum PyTorch/ORT CPU difference `5.5730342864990234e-06` on the specified
synthetic tensor. Re-running the preparation checks equivalence and noise
reduction and writes a fresh report; it does not merely copy that old result.

## Isolation, cancellation and tests

The UI creates a private job directory, writes strict bounded JSON and starts
the same application executable with a fixed internal operation. Worker output
is validated before acceptance; exports stage beside the chosen destination
and atomically replace only after success. Original, project, symlink and
hardlink destinations are refused. Cancellation preserves an existing output.
CPU inference and encoding do not run on the GUI event loop.

Workers own their FFmpeg processes. Normal cancellation uses a local marker and
a watchdog; forced cancellation kills only the owned Unix process group or the
Windows worker's kill-on-close Job Object. The Windows parent process is watched
through a process handle. Temporary files are removed after exit; a crash may
leave a hidden staging directory. Native codecs are **not a security sandbox**.

Regression coverage includes recipe/schema validation and v1 compatibility,
source aliases, atomic output, real CPU tiled-vs-full inference, real MP4 with
and without audio, stale-preview rejection, explicit acceptance, cancellation,
worker/encoder ownership, undo/save checkpoints, and DE/EN layout geometry.
`--suite-smoke-test` adds actual source/standalone model discovery, real preview,
project round-trip, audio-preserving AI render and UI screenshots. Windows CI
runs source and standalone checks plus 100/150/200% scale cases. A configured
workflow is not proof of a successful run; inspect its actual conclusion and
`verification/*/suite-smoke.json` for the exact package.

Primary references: [author's architecture](https://github.com/cszn/KAIR/blob/master/models/network_dncnn.py),
[author's inference configuration](https://github.com/cszn/KAIR/blob/master/main_test_dncnn.py),
[upstream release](https://github.com/cszn/KAIR/releases/tag/v1.0),
[MIT notice](https://github.com/cszn/KAIR/blob/master/LICENSE),
[FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html),
[Qt high DPI](https://doc.qt.io/qt-6/highdpi.html),
[Windows job objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
