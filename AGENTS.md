# Edivora – contributor and AI-agent rules

Read **[README.md](README.md)**, **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)**, **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**, **[docs/MEDIA_PROJECTS_AI.md](docs/MEDIA_PROJECTS_AI.md)** and **[docs/ROADMAP.md](docs/ROADMAP.md)** before changing code. Edivora is a local-first Photo / Video / Audio suite, **not** only a photo editor.

## Non-negotiable constraints

- Keep runtime **offline and local**: do not upload photos, video, audio, prompts, filenames, metadata, or diagnostics; do not connect to remote inference/model hosts. Explicit build-time dependency/model preparation may use the network.
- **Never overwrite a source image or source media file.** Export separately, refuse same files including aliases/hardlinks, and install completed exports atomically. Unsafe failure paths must leave originals untouched.
- Treat `.laip` ZIP projects and `.edvp/.edap` JSON manifests as **untrusted input**. Preserve strict entry/key allowlists, size/pixel/time budgets, validated media paths and fingerprints, checksums, controlled history and atomic writes. No ZIP path extraction, executable data or `pickle`.
- Reopened photo projects do not know original image paths. Do not allow overwriting pre-existing exports after reopen. Media projects may contain external **absolute** local file references; retain safe relinking/validation behavior and disclose portability/privacy limits.
- Keep reusable image/media operations and validators in `core/` (without Qt or inference), GUI and DE/EN translations in `ui/`, verified model adapters in `ai/`. Child processes must support cancellation, bounding and cleanup. Do not block the Qt event loop with long inference or encoding.
- New models require pinned **exact files, sizes, SHA-256, license/redistribution review, build-time-only acquisition** and actual CPU inference verification. No arbitrary model loading, `trust_remote_code=True`, remote code downloads or automatic runtime model installs. GPU recognition alone proves no GPU support.
- FFmpeg encoding uses fixed validated argument lists, **never a shell**. Account for silent streams, protected export paths, file aliases, consistent sequence timestamps/streams and atomically committed results. Native decoders are **not** sandboxes.
- Foreground correction only changes **alpha**, not source RGB, unless a separately reviewed tool explicitly implements another safe operation. Keep previews reversible and accept/cancel explicit.
- Keep the launcher able to start any one, any two or all three workspaces independently. New controls use plain DE/EN labels, accessible names, keyboard alternatives and shared design tokens. Use the checked-in Edivora logo assets; do not embed external scripts/fonts/CDNs.
- Do **not** change original `v0.1.0-alpha.1` binary/tag/checksums or imply that a development feature is in the historic photo release. Distinguish *source implemented*, *tests verified*, *Windows package tested* and *official release*. Do not claim Windows 11, GPU, quality or license approval without evidence.
- No secrets, private source media, telemetry, sensitive admin instructions, generated binaries or model weights in commits.

## Required delivery discipline

1. Identify the current `main` baseline, existing PRs, release status and relevant module/test; select a narrow, reviewable change.
2. Add or update automated regression tests and DE/EN text. For visual changes, check that logo/SVG and supported displays work; update documentation and screenshots only when they represent the **actual** tested UI.
3. Run `PYTHONPATH=src python -m unittest discover -s tests -v` and `python -m compileall -q src tests tools`; on Windows also run native/media/model/package smoke tests as applicable. If execution was blocked, state this explicitly; don't represent static review or mocks as real success.
4. Document security, compat, media-format, model, redistribution and rollout implications in the PR. Keep license notices and release gates current.
