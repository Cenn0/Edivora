# localAiPhotoEditor contributor rules

- Read `README.md`, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md` before changing the application.
- Preserve local processing: application runtime must not upload photos, prompts, metadata, or diagnostics, and must not contact model hosts. Downloads belong in explicit build-time tooling.
- Never overwrite the imported source image. Export to a different file and write atomically.
- Project archives are untrusted input: retain exact ZIP member allowlists, strict size/pixel/format limits, checksums, history validation and atomic replacement. Never extract archive paths or persist original absolute source paths. Reopened projects must not overwrite pre-existing image exports where the original path is unknown.
- Keep UI code under `ui/`, reusable image operations under `core/`, and model adapters under `ai/`. Core modules must not import Qt or initialize an inference runtime.
- Foreground brush and mask correction must only modify alpha; original RGB pixels and source files must not be changed. Keep normalized brush coordinates, validated stroke/point limits, explicit preview/accept/discard semantics, and reversible history.
- Run inference outside the UI process. Preserve cancellation, bounded input sizes, and cleanup of temporary job data.
- Load only the bundled, checksum-pinned ONNX models for photo/video
  foreground segmentation and audio voice activity. New models must have
  pinned byte sizes, SHA-256, reviewed licensing and build-time-only
  downloads; no generic runtime model paths or remote calls.
- Media projects are untrusted small JSON manifests; validate all keys,
  sizes, source references, fingerprint and time limits before replacing
  the active editor. Do not overwrite or modify linked media sources.
- Export multi-clip sequences via validated fixed FFmpeg arguments (never
  a shell) and a cancellable direct encoder process; explicitly account for
  silent video sources, consistent audio/video streams and atomic output.
- Never introduce pickle model loading, downloaded executable Python code, or `trust_remote_code=True`. Never introduce pickle model loading, downloaded executable Python code, or `trust_remote_code=True`.
- A mocked test does not prove model quality, native installation, or GPU compatibility. Report exactly which checks ran and which remain blocked.
- Keep user-facing strings in the UI's translation dictionary, with German and English available. Use plain labels describing tasks rather than model parameters.
- Run `PYTHONPATH=src python -m unittest discover -s tests -v` and `python -m compileall -q src tests tools` after substantive changes. Run the real-model and packaged smoke checks when changing inference or packaging.
- Do not commit private photos, generated build outputs, model binaries, credentials, or account administration instructions.

