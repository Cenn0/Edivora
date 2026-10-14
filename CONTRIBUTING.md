# Contributing to LocalAiPhotoEditor

Contributions from first-time developers and AI-assisted workflows are welcome. You do **not** need to understand every module before fixing a small issue. Start with one observable problem, use the existing tests, and keep the scope narrow.

**Read first:** [README](README.en.md) (or [Deutsch](README.md)) → [development setup](docs/DEVELOPMENT.md) → the [AI-assisted workflow](docs/AI_WORKFLOW.md) if using a coding agent. Coding agents must also obey [AGENTS.md](AGENTS.md).

## Your first contribution in six steps

1. **Pick one task.** Use an existing GitHub issue when possible. Beginner-friendly examples include clearer errors, DE/EN text corrections, a small UI accessibility improvement, or a regression test for a reproducible bug. Check current `main` and open PRs so you do not duplicate existing work.
2. **Get source access.** The repository is currently private. Ask the maintainer for access. Create a topic branch (for example, `fix/better-model-error`) with write access, or use a fork where permissions allow it.
3. **Run the app and tests once.** Follow [DEVELOPMENT.md](docs/DEVELOPMENT.md). The normal editor can start without a prepared model; actual AI inference needs the explicit pinned-model preparation step. Initial `pip` and model preparation may use the network; app runtime must not.
4. **Make the smallest useful change.** Keep image operations in `core/`, UI and translations in `ui/`, and model adapters in `ai/`. Add a focused regression test for behavior changes. Use both German and English for user-facing strings.
5. **Verify, then inspect the diff.** Run the applicable unit tests and compile check. Use real-model and packaged checks if the change affects inference or distribution. Record exactly what passed, failed or was skipped. Review any AI-generated code before submitting it.
6. **Open a PR.** Describe the problem, behavioral difference, tests, limitations, and screenshots when relevant. Do not merge without maintainer approval; branch policies and CI remain authoritative.

### Minimal verification after installing the project

```text
python -m unittest discover -s tests -v
python -m compileall -q src tests tools
```

Use the selected venv's Python executable. On CI, headless Qt tests run with `QT_QPA_PLATFORM=offscreen` and dependencies installed. Your local run may skip Qt tests when Qt or its system libraries are missing; **skips are not passes**. OS-specific commands and additional smoke checks: [DEVELOPMENT.md](docs/DEVELOPMENT.md).

## What a good PR contains

- A concise **problem statement** and expected behavior, with steps to reproduce a bug if relevant.
- A small diff with tests covering the changed behavior. Update docs and the DE/EN dictionaries when required.
- A reproducible verification report: **commands, OS, results, number of skipped tests**, and any blocked checks. Do not claim a model-quality improvement from mocked masks or a release-ready package from unit tests.
- For visible changes, a UI screenshot or a clear note that one was not produced. Use synthetic or explicitly licensed fixtures; **never upload private photos**.
- Any **privacy, original-file, format-compatibility, model-license or distribution impact** and remaining risks.

A PR template is provided automatically in GitHub. Documentation-only PRs may not trigger the existing code/build workflows because of their path filters; verify links and code snippets manually and do not present non-running CI as green.

## Architectural and safety invariants

These requirements are more important than convenience or generated code speed.

| Area | Requirement |
| --- | --- |
| Offline by design | Application runtime must not send images, prompts, metadata or diagnostics over the network. No telemetry, cloud inference or implicit model downloads. |
| User data | Never overwrite the imported source file or its aliases. Exports are validated and written atomically. Do not add original absolute paths to `.laip` archives. |
| Untrusted projects | Preserve strict archive member allowlists, size/format/pixel limits, integrity checks and safe archive handling. Do not extract arbitrary paths or execute archive contents. |
| Modular design | Keep `core/` independent of Qt, networking and inference. Qt belongs in `ui/`; model verification/inference in `ai/`; inference runs in a separate process. |
| Edits and masks | Pending previews do not alter the accepted image; Apply/Cancel and Undo/Redo must remain meaningful. Manual alpha correction preserves original RGB pixels. |
| Model supply | Run only reviewed, size- and checksum-pinned local ONNX files. No `pickle` weights, arbitrary scripts, `trust_remote_code=True` or unnoticed runtime downloads. |
| Translation and UX | Provide German and English labels, accessible names and understandable guidance instead of exposing low-level model parameters to novices. |
| Release claims | Separate current `main`, feature branches, old released packages and verification evidence. Windows 11 clean-machine acceptance and GPU support must not be invented. |
| Legal and assets | Do not commit model binaries, private photos, secrets, generated packages or copied assets without verified rights. Respect Qt and ONNX artifact terms. |

## Branches, commits and review

Use a focused branch and descriptive commit message (for example, `fix: clarify missing-model feedback`). Submit source, tests and docs in the same PR whenever they change together. Prefer an existing small abstraction over introducing a framework or a new dependency. Large feature requests should be split into independently testable increments.

Keep a human in the loop when AI is used: read the diff, test the actual behavior, and check that the explanation matches the code. A connected AI agent can create a branch/PR only if the user grants suitable permissions; a chat model with just a URL cannot modify this private repository. [Use this step-by-step AI prompt](docs/AI_WORKFLOW.md).

## Help and project direction

Use [ROADMAP.md](docs/ROADMAP.md) for goals, but confirm implementation status against current `main`. New generative models, GPU providers, changes to the project format, packaging and licensing require a proposal with concrete requirements and verification plans, not an unreviewed dependency addition.

For quick navigation see the [documentation index](docs/README.md). For deeper rules agents should follow [AGENTS.md](AGENTS.md).
