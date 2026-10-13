# Roadmap

## 0.1 alpha — local editing and bundled background removal

- Import JPEG/PNG/WebP, honour EXIF orientation and colour profiles, protect the original.
- Brightness, contrast, saturation, rotation, cropping and resizing.
- Before/after view, bounded undo/redo, German and English labels.
- One bundled U2NETP model, ONNX CPU execution, cancellable child-process inference.
- Metadata-clean exports and readable errors.
- Windows build pipeline and a portable ZIP containing the complete application, runtime and model. The first CI build does not promise an installer.

Acceptance: actual packaged model inference works without developer tools; the first launch and edit/export succeed with networking disabled on a clean Windows 11 x64 machine. Unit tests alone do not satisfy this gate. An unsigned build artifact may be offered explicitly as a test alpha while remaining checks are recorded in [VERIFICATION.md](VERIFICATION.md). Such an artifact must not be described as a verified end-user release.

## 0.2 — editing precision and project persistence

Progress after the published v0.1.0-alpha.1: a first version of durable project archives has been implemented in source. It stores the original, accepted result and retained Undo/Redo snapshots with versioning, checksums, size bounds and atomic writes. Source paths are intentionally not persisted. See [PROJECT_FORMAT.md](PROJECT_FORMAT.md). Native package acceptance for this newer implementation remains outstanding.

- User-correctable foreground mask: **manual alpha-only restore/erase brush with size, feather, stroke preview and Undo/Redo implemented in source**; automatic hair matting, background-colour replacement and blur remain planned. The current tool does not reconstruct missing RGB pixels or clean contaminated edge colors. See [MASK_REFINEMENT.md](MASK_REFINEMENT.md).
- Evaluate BiRefNet lite against U2NETP on an appropriately licensed image set, including hair, glass, fur and low-contrast boundaries.
- Save/reopen a versioned project containing original, accepted results, masks and operations; local recovery and cache management.
- Keyboard navigation, high-DPI checks and tested light/dark themes.

Acceptance: unwanted mask pixels can be corrected without regenerating protected foreground detail; saved projects open deterministically and exports match the accepted preview.

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

