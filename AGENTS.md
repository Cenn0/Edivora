# LocalAiPhotoEditor — coding agent instructions

Scope: repository root and all subdirectories. Treat **current `main`** as the baseline. Unmerged PRs, historic releases and other branches are not automatically part of the default app.

## Read efficiently

1. Read `README.en.md` (or `README.md`), `CONTRIBUTING.md` and `docs/DEVELOPMENT.md` to understand setup and contribution rules.
2. Read `docs/ARCHITECTURE.md` and the **relevant** feature document when changing behavior; check `docs/ROADMAP.md` for scope/status.
3. Inspect only files needed for the task and neighboring tests. Avoid loading all documentation/history into context without a reason. Follow `docs/AI_WORKFLOW.md` for an efficient, reviewable AI-assisted process.

## Mandatory invariants

- **Local runtime:** Never upload photos, prompts, metadata or diagnostics. No model-host calls, telemetry, implicit runtime downloads or new always-on services. Explicit, verified downloads belong to build-time tools only.
- **Source protection:** Never overwrite imported originals, including aliases/hardlinks; preserve validated atomic exports.
- **Untrusted projects:** Preserve exact ZIP member allowlists, format/pixel/size bounds, hashes, consistent history and atomic writes. Never extract archive paths, execute their contents, or persist source absolute paths. Reopened projects must not overwrite pre-existing exports when the original path is unknown.
- **Module boundaries:** `core/` has no Qt, model runtime or network dependency; `ui/` owns widgets, preview, translations and orchestration; `ai/` owns pinned model verification/inference. Keep inference in a separate process with bounded input, cancellation, job cleanup and stale-document guards. The worker is not a security sandbox.
- **Edit semantics:** Preserve preview/Apply/Cancel, bounded reversible history and full-resolution acceptance. Manual restore/erase mask strokes modify alpha only, not source RGB; maintain normalized coordinates and validated stroke/point limits.
- **Model security:** Load only checksum- and size-pinned local ONNX artifacts; no pickle loading, fetched executable code or `trust_remote_code=True`. Never silently introduce a GPU provider or larger model.
- **UX:** Keep DE/EN user-facing strings in existing UI translation modules, with novice-friendly names and accessible controls. Do not overstate what is AI versus deterministic image processing.
- **Repository hygiene:** Never commit personal photos, model binaries, build artifacts, keys, private configuration or account administration details. Check redistribution permissions for models and new dependencies.

## Implementation and evidence

- First explain the baseline and a small plan; change only what the task requires. Prefer focused tests to speculative refactors.
- After behavior changes run the installed environment's `python -m unittest discover -s tests -v` and `python -m compileall -q src tests tools`. CI uses Python 3.12 and Qt headless where appropriate. State any failures or skipped tests **explicitly**; no fabricated results.
- For inference, use the explicit `tools/prepare_model.py` step and real-model checks; for packaging changes, verify the actual Windows package and offline path. Mocked unit tests are not proof of model quality or installability.
- For documentation-only changes, validate internal links, examples and version/release claims; existing docs-only PRs may not trigger CI.
- Update user docs, roadmap and both languages when relevant. Do not equate a newer `main` feature with the already published `v0.1.0-alpha.1` ZIP.
- Work in a topic branch, present the diff and a PR. **Do not merge or publish a release without explicit authorization.**
