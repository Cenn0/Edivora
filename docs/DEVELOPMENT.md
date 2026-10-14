# Development quickstart

This guide is for **running, understanding and testing the source checkout**. It does not install a stable end-user release. For the no-code Windows alpha, use the [main README](../README.md). For contributions, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Requirements

- **Git** and **Python 3.12**, with `venv` and `pip`. CI currently tests Python 3.12. The broader `requires-python` interval in `pyproject.toml` is not evidence of tested compatibility on every platform.
- Internet access **during initial development setup** to install pinned dependencies. Running the editor afterward does not require internet.
- Windows 11 x64 is the intended desktop target; automated source tests also run on Ubuntu 24.04 and Windows Server 2022. macOS packages and general cross-platform support have **not** been verified.
- You do **not** need Docker, a GPU, CUDA, an API key or an external model server.

### Windows (PowerShell)

From a shell with Python 3.12 available:

```powershell
git clone https://github.com/Cenn0/LocalAiPhotoEditor.git
cd LocalAiPhotoEditor
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m local_ai_photo_editor
```

### Linux (shell; source use, not a supported package)

```bash
git clone https://github.com/Cenn0/LocalAiPhotoEditor.git
cd LocalAiPhotoEditor
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m local_ai_photo_editor
```

The GUI requires an actual desktop display and Qt system libraries. On Ubuntu CI, additional headless libraries are installed by [python-checks.yml](../.github/workflows/python-checks.yml), including `libegl1`, `libopengl0`, `libgl1` and `libxkbcommon0`. A `QT_QPA_PLATFORM=offscreen` test invocation does **not** display a usable application window.

`pip install -e .` uses the direct dependencies pinned in [pyproject.toml](../pyproject.toml): Pillow, NumPy, PySide6 and ONNX Runtime. Editable installation exposes the package; setting `PYTHONPATH` is unnecessary in this workflow. The `.venv/` directory is ignored by Git.

## Enable the real local AI model (optional for non-AI work)

The model binary is intentionally not stored in Git. Source inference needs an explicit preparation step:

```powershell
# Windows, from the repository directory:
.\.venv\Scripts\python.exe tools\prepare_model.py
```

```bash
# Linux:
.venv/bin/python tools/prepare_model.py
```

`tools/prepare_model.py` downloads the **one pinned U2NETP ONNX artifact** via HTTPS if it is missing, then checks its expected file size and SHA-256 (and an upstream compatibility digest). An already-present model is checked without downloading. It is stored in `src/local_ai_photo_editor/models/u2netp.onnx` and must **not** be committed.

**Separation of concerns:** dependency installation and model preparation may access the network; the desktop runtime and its worker do not fetch a model and must not send photos to a cloud service. A model checksum is an integrity check, not a comprehensive third-party supply-chain or license audit. See [MODELS.md](MODELS.md).

## Run the tests

Use the venv's interpreter for each command.

**Windows PowerShell (headless Qt):**

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src tests tools
Remove-Item Env:QT_QPA_PLATFORM
```

**Linux (headless Qt):**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q src tests tools
```

To run one test module, replace the discovery pattern, e.g.:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_recipes.py' -v
```

Windows equivalent: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_recipes.py -v`.

**Interpret results correctly:**

- `OK` means the tests **actually executed** passed; review the `skipped=...` count separately. Optional Qt tests can be skipped if PySide6 or native libraries are unavailable.
- Unit tests with synthetic inputs/mocked masks do **not** validate real model output quality.
- Compilation checks syntax/import-independent bytecode generation; they do not exercise the whole UI or distribution.
- A passing source suite does **not** certify a portable Windows ZIP or a fresh Windows 11 install.

CI source checks live in [python-checks.yml](../.github/workflows/python-checks.yml). Existing workflows may not start for docs-only changes because of path filters.

## Optional smoke tests

After preparing the real model, test **actual separate-process inference** with a synthetic image:

```powershell
.\.venv\Scripts\python.exe -m local_ai_photo_editor --smoke-test test-results/my-worker-run-1
```

Linux equivalent: `.venv/bin/python -m local_ai_photo_editor --smoke-test test-results/my-worker-run-1`.

The target output directory must **not already exist**; use a fresh name on every run. The resulting `smoke-result.json` reports success or a failed phase. This proves the limited worker/inference path, **not** portrait quality or Windows package compatibility.

For UI rendering checks, the repository includes `tools/capture_editing_ui.py` (synthetic images, DE/EN views) and the `--ui-smoke-test <new-directory>` CLI entry point. Run these only in an environment with the necessary Qt/native graphical dependencies. Do not upload screenshots of private photos.

For changes to model request/response behavior, consult [AI_SUBJECT_TOOLS.md](AI_SUBJECT_TOOLS.md) and `tools/verify_subject_tools.py`. For changes to Windows packaging, review [windows-alpha.yml](../.github/workflows/windows-alpha.yml), [offline-package-check.yml](../.github/workflows/offline-package-check.yml), and [VERIFICATION.md](VERIFICATION.md). Packaging uses a **separately pinned Nuitka 4.2.2** toolchain. A local unit test is not a substitute for packaged real-model and offline verification.

## Where should I make my change?

| Change area | Start reading | Closest tests |
| --- | --- | --- |
| Import/export, history, basic image edits | `src/local_ai_photo_editor/core/document.py`, `editing.py` | `tests/test_core.py` |
| Guided looks, lighting, crops, background | `core/recipes.py` and `ui/editing_dialog.py` | `test_recipes.py`, `test_editing_ui.py` |
| Mask painting/canvas interaction | `core/mask.py`, `ui/canvas.py` | `test_mask.py`, `test_ui.py` |
| Local AI selection/effects | `ai/background.py`, `core/subject.py`, `ui/subject_dialog.py` | `test_ai.py`, `test_subject.py`, `test_subject_ui.py` |
| Separate worker, model integrity | `worker.py`, `ai/models.py` | `test_ai.py` |
| Saving/loading local projects | `core/project.py` | `test_project.py` |
| User-facing DE/EN text | `ui/strings.py`, `ui/editing_strings.py`, `ui/subject_strings.py` | relevant UI tests |
| Windows delivery/release | `tools/build_windows.py`, `tools/publish_alpha.py`, CI workflows | `test_publish_alpha.py` and package smoke runs |

All `core/` functions should remain usable without importing Qt or an inference runtime. The GUI coordinates edits but must not become the only home of reusable pixel logic. See [ARCHITECTURE.md](ARCHITECTURE.md) and [AGENTS.md](../AGENTS.md).

## Common setup problems

| Symptom | Check |
| --- | --- |
| `py -3.12` or `python3.12` not found | Install Python 3.12 and ensure the launcher/interpreter is available in your shell. |
| `ModuleNotFoundError: local_ai_photo_editor` | Use the venv interpreter and rerun `-m pip install -e .` from the repository root. |
| Local AI function reports missing model | Run `tools/prepare_model.py` explicitly, confirm the model passes integrity checks. |
| Qt platform plugin / `xcb` / OpenGL error | Ensure PySide6 and native Qt dependencies are installed; compare with the Ubuntu CI dependencies. Do not treat skipped Qt tests as GUI verification. |
| No GUI window appears after running tests | Remove the `QT_QPA_PLATFORM=offscreen` environment variable before launching the interactive editor. |
| Smoke test fails because output path exists | Use a new results directory; the smoke CLI intentionally requires an absent one. |
| A PR check is missing | Inspect workflow path filters and what actually ran. No check is not a green check. |

## Before opening a PR

Run the relevant tests, inspect your diff, check DE/EN strings, and accurately document any privacy/original-file, format, model, or packaging impact. Distinguish **source changes** from **published ZIP contents**. [CONTRIBUTING.md](../CONTRIBUTING.md) includes a complete submission checklist.
