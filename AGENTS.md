# localAiPhotoEditor contributor rules

- Read `README.md`, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md` before changing the application.
- Preserve local processing: application runtime must not upload photos, prompts, metadata, or diagnostics, and must not contact model hosts. Downloads belong in explicit build-time tooling.
- Never overwrite the imported source image. Export to a different file and write atomically.
- Keep UI code under `ui/`, reusable image operations under `core/`, and model adapters under `ai/`. Core modules must not import Qt or initialize an inference runtime.
- Run inference outside the UI process. Preserve cancellation, bounded input sizes, and cleanup of temporary job data.
- Load only the bundled, checksum-pinned ONNX model. Never introduce pickle model loading, downloaded executable Python code, or `trust_remote_code=True`.
- A mocked test does not prove model quality, native installation, or GPU compatibility. Report exactly which checks ran and which remain blocked.
- Keep user-facing strings in the UI's translation dictionary, with German and English available. Use plain labels describing tasks rather than model parameters.
- Run `PYTHONPATH=src python -m unittest discover -s tests -v` and `python -m compileall -q src tests tools` after substantive changes. Run the real-model and packaged smoke checks when changing inference or packaging.
- Do not commit private photos, generated build outputs, model binaries, credentials, or account administration instructions.

