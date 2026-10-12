# localAiPhotoEditor

A beginner-friendly desktop photo editor that processes images on your computer.

**Status: initial development alpha.** This repository contains the architecture and the first implementation. An installer is only considered usable after the Windows package, actual model inference, and offline smoke checks succeed. Do not interpret a source checkout as a finished end-user release.

## Intended experience

Open a photo, choose a clearly named tool, compare the result, and export a copy. The source photo is never overwritten. The first target platform is **Windows 11 x64**; macOS and Linux are future packaging targets, not currently certified releases.

The initial scope is:

- Open JPEG, PNG, and WebP images, with orientation and embedded colour profiles handled at import.
- Adjust brightness, contrast, and saturation; rotate, crop, and resize.
- Remove a background using the bundled U2NETP neural network and ONNX Runtime on the CPU.
- Compare with the original, undo/redo within a bounded history, and export JPEG, PNG, or WebP.
- Use German or English task labels.

The adjustments are conventional image processing. Background removal is the AI feature. This alpha does **not** include editing from text prompts, generative object removal, RAW development, or a persistent layered project format.

## Privacy and offline use

The editor has no account, backend, cloud inference endpoint, analytics, runtime updater, or model downloader. Inference runs in a child process using a prepackaged model. Only the developer's build step downloads dependencies and the model. A complete distribution must contain the required runtime and model before installation.

Temporary inference inputs and results are stored locally and removed after a completed or cancelled job. They are not encrypted and a forced process or operating-system crash can leave temporary files. Do not assume local processing also protects against another administrator, malware, OS backups, or a cloud-synced folder chosen by the user.

## Installation

End-user delivery is planned as a Windows installer and a portable archive containing the complete app and model. There is no published, verified installer at the initial source commit. Use a download only when its build is marked successful. The developer instructions below are not the intended end-user setup.

## Development

Use Python 3.12. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

On Linux/macOS, the virtual environment interpreter is `.venv/bin/python`. Application dependencies are directly pinned in `pyproject.toml`; the build records resolved transitive dependency versions. A fully hashed transitive lock is a follow-up release-hardening task, not an existing guarantee.

The model preparation step downloads the fixed upstream release asset and requires the pinned SHA-256, original upstream MD5 compatibility value, and exact size to match. It is not called by the desktop application. The expected SHA-256 still needs an actual binary verification run in CI before the first binary can be called tested.

## Verification

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests tools
PYTHONPATH=src python -m local_ai_photo_editor --smoke-test smoke-output
```

The first command can run headless. Tests requiring unavailable Qt or the real bundled model are explicitly skipped, never reported as successful inference checks. The smoke command requires the real model and ONNX Runtime and writes an inspection report and a synthetic output image. The packaging workflow must also run that command against the built executable.

## Design

- [Project concept](docs/CONCEPT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Model decisions and evidence](docs/MODELS.md)
- [Roadmap and acceptance criteria](docs/ROADMAP.md)
- [Verification record](docs/VERIFICATION.md)
- [Third-party components](THIRD_PARTY_NOTICES.md)

## License

Application code: Apache-2.0. Dependencies and model artifacts retain their own licenses. U-2-Net's source repository uses Apache-2.0; the U2NETP ONNX export is distributed by rembg. See the model decision record for the exact provenance and the distinction between repository-level licensing and a separate statement about a converted weights artifact.

