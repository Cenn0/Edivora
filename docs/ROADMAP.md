# Edivora roadmap

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

## Future Edivora media toolset (not implemented)

**Edivora Photo** remains the priority until a reproducible, signed, clean-machine release is available. The following are **proposals**, not existing features or delivery commitments.

### Edivora Video

- Beginner workflow: import, trim, split, reorder clips, add titles and transitions, preview and export with understandable presets.
- Architecture: a non-destructive timeline and audio/video synchronization rather than reusing still-image snapshots as a video document model.
- Optional, locally validated AI features such as transcription/subtitles or scene assistance only after testing model licenses, latency, memory budgets and real hardware.
- Evaluate FFmpeg/libav and codecs, redistribution obligations, Windows packaging and format support before promising individual container/codec combinations.

### Edivora Audio

- Beginner workflow: open a recording, cut, fade, adjust level, listen to a non-destructive preview and export.
- Architecture: waveform caches, time-based tracks and cancellable processing with accessible scrubbing/playback.
- Evaluate optional offline noise reduction and speech models separately; a generic video/audio AI claim requires model-specific evidence.
- Avoid automatic normalization that clips audio or changes loudness unexpectedly; preview and explicit apply/revert remain mandatory.

### Shared foundations

The existing Python/Qt photo editor does **not** imply that one editing engine is suitable for all media. Share brand, task-oriented navigation, model management, import/export conventions, privacy contracts and translations; keep image, timeline and waveform domain logic modular. Benchmark video frame throughput, decoder compatibility, memory/storage use and UI responsiveness before making language/engine decisions. Preserve a local-first runtime, no account requirement and clear labels for installed features versus planned modules.

## Later, after measured demand

- Local inpainting and super-resolution models with verified redistribution terms.
- Linux and macOS packages, including notarized macOS delivery where required by the chosen distribution path.
- GPU acceleration for segmentation only when its practical speed-up outweighs package and support cost.
- RAW/16-bit workflows, batch editing and richer layers only after the basic editor is stable.

No mobile client, SaaS backend, user accounts, collaborative editing, plug-in marketplace, or external model runtime is required for the initial goal.
