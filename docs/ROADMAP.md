# Roadmap

## 0.1 alpha — local editing and bundled background removal

- Import JPEG/PNG/WebP, honour EXIF orientation and colour profiles, protect the original.
- Brightness, contrast, saturation, rotation, cropping and resizing.
- Before/after view, bounded undo/redo, German and English labels.
- One bundled U2NETP model, ONNX CPU execution, cancellable child-process inference.
- Metadata-clean exports and readable errors.
- Windows build pipeline and a portable package; generate an installer when the build tools are available.

Acceptance: actual packaged model inference works without developer tools; the first launch and edit/export succeed with networking disabled on a clean Windows 11 x64 machine. Unit tests alone do not satisfy this gate. No end-user release is claimed until it is verified.

## 0.2 — editing precision and project persistence

- User-correctable foreground mask, edge refinement and background colour/blur.
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

## Later, after measured demand

- Local inpainting and super-resolution models with verified redistribution terms.
- Linux and macOS packages, signed Windows installation and notarized macOS delivery as appropriate.
- GPU acceleration for segmentation only when its practical speed-up outweighs package and support cost.
- RAW/16-bit workflows, batch editing and richer layers only after the basic editor is stable.

No mobile client, SaaS backend, user accounts, collaborative editing, plug-in marketplace, or external model runtime is required for the initial goal.

