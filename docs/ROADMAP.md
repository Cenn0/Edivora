# Roadmap

## Vier lokale KI-Profile mit Hardwareauswahl (Entwicklung 0.4 Alpha)

Im Quellcode implementiert: eine gemeinsame Task-Modell-Registry und lokale
manuelle/automatische KI-Modellwahl für Foto/Video/Audio, mit RAM-/CPU-
Heuristik und Integritätsprüfung. Zu den bestehenden U2NETP- und Silero-VAD-
ONNX-Gewichten kommen IS-Net General Use und Whisper Tiny multilingual INT8
hinzu. Die neuen Funktionen sind stärkere Freistellung (Foto/Standbild)
und echte lokale Audio-/Videoton-Transkription nach TXT/SRT.

**Release-Gate:** gepinnte Artefakte durch Buildzeit-Downloads bereitstellen;
echte U2NETP-/IS-Net-/VAD-/Whisper-CPU-Inferenz im Windows-Standalone-Paket
testen; Quell-/Lizenz- und unveränderte Clean-Windows-11-Prüfungen abschließen.
Die Automatik bewertet **RAM/CPU und vorhandene Modelle**, nicht bloß
Dateigröße oder eine vermutete GPU-Verfügbarkeit. GPU-Inferenz ist in dieser
Stufe nicht freigegeben. Siehe [MODEL_PROFILES.md](MODEL_PROFILES.md).


## Nächster Entwicklungsschritt: Multi-Clip, Projekte, lokale Medien-KI

Im Entwicklungsbranch umgesetzt, **noch nicht als veröffentlichter Endnutzer-
Release freigegeben**:

- Ordered single-lane Video-/Audio-Arrangement für bis zu 24 Clips, Ziehen zum
  Sortieren, Teilen, Duplizieren, Löschen und clip-spezifischer Ausschnitt
- Reversible Datendateien `.edvp/.edap` mit strikt validiertem JSON, relativen
  bzw. absoluten lokalen Quelldateiverweisen und atomarem Projektspeichern
- Gemeinsamer lokaler FFmpeg-Render als MP4 oder WAV/MP3 mit harter
  Quellschutzgrenze, abbrechbarem Unterprozess und konsistenten Streams
- **Echte lokale KI:** Silero v6.2.1 ONNX zum Erkennen von Sprachabschnitten
  im Audioeditor (mit Bestätigung) und vorhandenes U2NETP-Modell zum
  Freistellen eines einzelnen Video-Standbilds als PNG
- Sprach-/Projekt-/Render- und Sicherheitsprüfungen; realer Modell- und
  Windows-Paket-Smoke-Test als eigenständiges, ausstehendes Akzeptanzkriterium

Noch offen: durchgehende Zusammenschnitt-Vorschau, Multitrack-Audio-/Video-
Mischer, frei positionierbare Clips mit Überlappungen, Übergänge,
Medien-Undo/Redo, Offline-Transkription, temporale Video-KI, Media-Relinking,
vollständige FFmpeg-/Modell-Lizenzfreigabe und Clean-Windows-11-Abnahme.
Details: [MEDIA_PROJECTS_AI.md](MEDIA_PROJECTS_AI.md).

## Media suite MVP — new source milestone (not in the legacy photo-only alpha)

- Implemented in development source: one Edivora launcher executable that starts
  the Photo, Video or Audio workspace separately; any two or all three
  can run at once.
- Video MVP: file import and Qt playback, **graphical in/out timeline with draggable handles**,
  precise range spin boxes, current-position start/end actions, volume/mute,
  MP4 export through local FFmpeg with original-file protection.
- Audio MVP: file import and Qt playback, separate waveform preview,
  **the same interactive trim range**, volume, loudness normalization and fades,
  WAV/MP3 export.
- Shared German/English visual language and task labels. Source and packaged
  Windows smoke checks exercise Qt window construction and synthetic FFmpeg exports.

**Acceptance still open:** Windows packaged source & frozen CI green on the exact
revision, real-world import/playback/export with representative codecs,
licence review of distributed FFmpeg/Qt components, fresh Windows 11
usability and offline-network acceptance, and completion of the first
new Edivora distribution. Building code is not evidence of a release.

**Later:** full clip-arrangement video timeline and draggable waveform editing, multitrack,
reversible native media-project format, H.264-quality/performance matrix,
and genuinely local AI for speech/subtitles/audio enhancement. Detailed MVP
contract: [MEDIA_MVP.md](MEDIA_MVP.md).


## 0.1 alpha — local editing and bundled background removal

- Import JPEG/PNG/WebP, honour EXIF orientation and colour profiles, protect the original.
- Brightness, contrast, saturation, rotation, cropping and resizing.
- Before/after view, bounded undo/redo, German and English labels.
- One bundled U2NETP model, ONNX CPU execution, cancellable child-process inference.
- Metadata-clean exports and readable errors.
- Windows build pipeline and a portable ZIP containing the complete application, runtime and model. The first CI build does not promise an installer.

Acceptance: actual packaged model inference works without developer tools; the first launch and edit/export succeed with networking disabled on a clean Windows 11 x64 machine. Unit tests alone do not satisfy this gate. An unsigned build artifact may be offered explicitly as a test alpha while remaining checks are recorded in [VERIFICATION.md](VERIFICATION.md). Such an artifact must not be described as a verified end-user release.

## 0.2 — editing precision, subject-aware AI tools and project persistence

Progress after the published v0.1.0-alpha.1: durable project archives, manual mask correction, guided image tools and a subject-aware AI workspace have been implemented in source. Individual development packages and their verification must be tied to their exact source revision; the old released ZIP is unchanged.

- **AI subject tools:** automatically select a subject with the existing U2NETP model, then soften the existing background, keep only the subject in color, brighten the subject, dim the background, crop to the subject or preview a cutout. The selection is reused per dialog session. Selection overlay, strength/edge/margin controls, explicit acceptance, Undo/Redo, separate-process inference, timeout and cleanup are implemented. This does not add a stronger model, depth estimation, generative reconstruction or an in-dialog selection brush. See [AI_SUBJECT_TOOLS.md](AI_SUBJECT_TOOLS.md).
- User-correctable foreground mask: **manual alpha-only restore/erase brush with size, feather, stroke preview and Undo/Redo implemented in source**. Automatic hair matting remains planned. The current tool does not reconstruct missing RGB pixels or clean contaminated edge colors. See [MASK_REFINEMENT.md](MASK_REFINEMENT.md).
- **Guided light/color corrections, gentle automatic correction, six adjustable looks, sharpening, vignette, exact-ratio crops, mirror/rotation and background design are implemented in source.** The workspace provides DE/EN guidance, before/after previews, per-control/section/all resets and explicit Apply/Cancel. Full-resolution rendering runs in a cancellable worker thread and produces one Undo/Redo snapshot. Background colors, local background photos and background-only blur require an existing cutout. See [EDITING_TOOLS.md](EDITING_TOOLS.md).
- Evaluate BiRefNet lite against U2NETP on an appropriately licensed image set, including hair, glass, fur and low-contrast boundaries. This evaluation and model replacement remain open; additional uses of U2NETP do not constitute a model-quality improvement.
- Save/reopen a versioned project containing original, accepted results, masks and operations; local recovery and cache management. Snapshot persistence with checksums, size limits and atomic writes is implemented; editable adjustment layers, reusable AI selections and recovery/cache management remain future work. Source paths are intentionally not persisted. See [PROJECT_FORMAT.md](PROJECT_FORMAT.md).
- Keyboard navigation, high-DPI checks and tested light/dark themes. Guided controls expose accessible names, keyboard controls and reset actions; comprehensive high-DPI and interactive accessibility acceptance remains open.

Acceptance: unwanted mask pixels can be corrected without regenerating protected foreground detail; saved projects open deterministically and exports use the accepted full-resolution result. Reduced-size previews may differ slightly at filtered edges and integer crop boundaries; source UI tests do not replace packaged or interactive usability acceptance.

## 0.3 — optional instruction-based local editing

- Validate FLUX.2 klein 4B with the complete inference pipeline and all model artifacts.
- Benchmark a published NVIDIA hardware matrix, including a separately tested 12 GB configuration if feasible.
- Select a validated precision/quantization configuration, and define RAM, disk and driver requirements from measurements.
- Package an optional generative component; enable it only when installed and supported.
- Prompt plus mask, preview, accept/reject, actual-result history, cancellation and out-of-memory recovery.

Acceptance: no implicit network access, no account/API key, reliable failure recovery, measured limits, and explicit disclosure that generative edits can alter unmasked content unless composited with the original.

## Before the first stable end-user release

- Sign the Windows package and complete the clean-machine offline acceptance checks for the exact distributed build.
- Publish the tested platform, dependency/model versions, known limits and corresponding verification evidence.
- Add an installer if it demonstrably simplifies delivery; the tested portable package remains a valid distribution format.

No signing certificate is assumed to be available during initial development. Signing is a stable-release requirement, not a prerequisite for a clearly labelled test-alpha artifact.

## Later, after measured demand

- Local inpainting and super-resolution models with verified redistribution terms.
- Linux and macOS packages, including notarized macOS delivery where required by the chosen distribution path.
- GPU acceleration for segmentation only when its practical speed-up outweighs package and support cost.
- RAW/16-bit workflows, batch editing and richer layers only after the basic editor is stable.

No mobile client, SaaS backend, user accounts, collaborative editing, plug-in marketplace, or external model runtime is required for the initial goal.
