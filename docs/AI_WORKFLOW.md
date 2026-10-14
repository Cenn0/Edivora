# Develop LocalAiPhotoEditor with an AI coding agent

**Audience:** Contributors who want to ask ChatGPT, Codex, Copilot or another assistant to understand and change the project, including people who have never contributed to this codebase. You do not need to learn every module in advance; you do need to review the proposed work.

This document describes a **workflow**, not a claim that any particular assistant has write access. The GitHub repository is currently private.

## 1. Decide how the AI will access the code

| Your AI setup | What it can do | What you need to provide |
| --- | --- | --- |
| **Read-only chat with just a URL** | It may explain the public description but **cannot reliably inspect private source** | Paste/upload `AGENTS.md` and the relevant files, or use an authorized code connector |
| **AI with read access to the private repository** | Inspect code, suggest a plan, prepare patches | Ask it for the relevant files/diff; apply changes yourself if it lacks write permission |
| **Coding agent with authorized read/write access** | Create a branch, change files, run available checks, open a PR | Specify a focused task and review the PR before merging |

Grant the **least privilege needed**. A link, chat instruction, or model name alone never grants account permissions. Do not give the agent production credentials, private photos, API tokens, or model-license assumptions.

## 2. Give the agent only the needed context

A useful, low-noise reading order is:

1. `AGENTS.md` — short rules the agent must obey.
2. `CONTRIBUTING.md` and `docs/DEVELOPMENT.md` — how to install, run tests and report evidence.
3. `docs/ARCHITECTURE.md` — if the task changes behavior or module boundaries.
4. The **one feature document, source modules and neighboring tests** relevant to the task. Start from the [source map](DEVELOPMENT.md#where-should-i-make-my-change).

Avoid copying the entire repository into a prompt. Let the agent retrieve specific files as needed. Always refer to **current `main`** and check open PRs; the published `v0.1.0-alpha.1` ZIP and unmerged feature branches have different code.

## 3. Copy this prompt to start your task

Replace the bracketed placeholder. This works best as one task per PR.

```text
Repository: https://github.com/Cenn0/LocalAiPhotoEditor
Base: current main.

Goal: [one observable improvement, bug report or issue URL]

Read AGENTS.md, CONTRIBUTING.md and docs/DEVELOPMENT.md first,
then inspect only relevant code, tests and feature documentation.
Check whether the task is already implemented or covered by an open PR.

1. Briefly describe the current behavior, cause and acceptance criteria.
2. Propose the smallest maintainable change that preserves project invariants.
3. Implement it on a topic branch, with focused regression tests.
4. Update DE/EN strings and user documentation if behavior changes.
5. Run applicable local checks; report precise results, skipped tests,
   limitations and any unavailable real-model/package verification.
6. Review your own diff for accidental changes, leaks and unsafe input handling.
7. Open a PR with a summary, test evidence and remaining risks.
Do not merge the PR or publish a release unless I explicitly request it.

Do not introduce cloud inference, telemetry, runtime model downloads,
source-photo overwrites, unverified model binaries or new dependencies
without clear need and licensing assessment.
If the repository is inaccessible, say so and request only the relevant files.
Do not invent functionality, successful tests or CI status.
```

**Even simpler first task (example):** Replace the goal with: “Make the existing missing-local-model error easier for a beginner to understand, in both German and English; preserve the existing error handling and add an appropriate regression test.”

Do not assume an assistant can run graphical UI checks on a headless Linux environment. Ask it to report which environment it actually used.

## 4. Review the result before accepting it

| Review question | Expected evidence |
| --- | --- |
| Does the implementation solve the original problem? | Reproduction steps and a new or adapted regression test |
| Were only necessary files changed? | A small, readable diff without unrelated rewrites |
| Were tests really executed? | Exact commands, observed pass/fail/skip counts and relevant CI links |
| Are screenshots meaningful and safe? | Synthetic/authorized test images, DE/EN views where relevant |
| Are model or packaged claims justified? | Actual checksum-pinned inference and package smoke evidence if claimed |
| Is local privacy intact? | No network path in runtime, no photo/metadata uploads or implicit downloads |
| Is the imported photo still safe? | No overwriting of original/aliases; bounded, validated, atomic writes |
| Are formats and localization maintained? | `.laip` compatibility where applicable, two UI languages, updated docs |

Unit tests with mocked model outputs cannot demonstrate model segmentation quality. A compiled app running on a CI Windows Server runner is not the same as a clean Windows 11 acceptance. An untriggered documentation-only workflow is **not** a successful check.

## 5. A contribution path that stays manageable

A practical first session:

1. Use [DEVELOPMENT.md](DEVELOPMENT.md) to install and start the app and to run tests.
2. Ask your AI: “Show me where this behavior lives and which existing test covers it. Do not modify files yet.”
3. After reviewing the answer, provide the desired behavior and run the full implementation prompt above.
4. Examine the PR diff and actual test output. Make corrections in the same branch before requesting a merge.

**Small improvements** to errors, translations, UI hints and existing tests are ideal for learning. **Larger changes** such as a new model, generative editing, persisted adjustment layers or GPU support need explicit technical design, compatibility, privacy and distribution reviews. The [roadmap](ROADMAP.md) is planning context, **not** proof that a feature exists today.

## 6. If something goes wrong

- **AI says it changed GitHub, but nothing appears:** check that the tool was actually connected and that a real commit/PR URL was returned. Text describing changes is not a commit.
- **Tests reported “passed” but Qt cases were skipped:** install required Qt/native dependencies and rerun; record skips separately.
- **AI claims a newly coded feature is already in the download:** confirm against the specific [release](../README.en.md#try-the-windows-alpha), not `main`.
- **The real AI model is missing locally:** `tools/prepare_model.py` is an explicit development step that downloads and checks one pinned artifact.
- **Agent proposes disabling checksum/ZIP validation to fix a test:** reject that shortcut; find the actual cause or request review.
- **Agent returns a huge rewrite:** narrow the task and demand one minimal, testable change per PR.

For more detail on the module boundaries, read [ARCHITECTURE.md](ARCHITECTURE.md). For contribution expectations and security invariants, see [CONTRIBUTING.md](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md).
