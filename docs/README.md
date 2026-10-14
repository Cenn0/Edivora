# Documentation — start here

[Main README (Deutsch)](../README.md) · [English README](../README.en.md) · [Contribution guide](../CONTRIBUTING.md)

This page is a **map**, not a prerequisite reading list. Pick the shortest path for your goal. Documents about individual features contain detailed behavior and technical limits; they should not be confused with a promise that those features are in the last published Windows ZIP.

## I am new to this project

1. **Just want to edit photos?** Start with the [German README](../README.md) or [English README](../README.en.md). Follow the download/extraction instructions. The published `v0.1.0-alpha.1` ZIP is an unsigned test build.
2. **Want to change a small piece of code?** Read [CONTRIBUTING.md](../CONTRIBUTING.md), then [DEVELOPMENT.md](DEVELOPMENT.md) and the relevant tests.
3. **Want an AI coding agent to help?** Read [AI_WORKFLOW.md](AI_WORKFLOW.md). Agents should follow the concise [AGENTS.md](../AGENTS.md) guardrails.

## Find the right technical document

| Question | Document |
| --- | --- |
| Which component owns this behavior? | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Why Python, Qt and a local model? | [CONCEPT.md](CONCEPT.md) |
| How do I install, run, test or debug source? | [DEVELOPMENT.md](DEVELOPMENT.md) |
| How does a new developer contribute? | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| How do I work safely and efficiently with an AI agent? | [AI_WORKFLOW.md](AI_WORKFLOW.md) |
| What do guided color and crop tools do? | [EDITING_TOOLS.md](EDITING_TOOLS.md) |
| How do AI subject effects work? | [AI_SUBJECT_TOOLS.md](AI_SUBJECT_TOOLS.md) |
| What does the mask brush really modify? | [MASK_REFINEMENT.md](MASK_REFINEMENT.md) |
| What is saved in a `.laip` project and how is it validated? | [PROJECT_FORMAT.md](PROJECT_FORMAT.md) |
| Where do model weights come from, and what is licensed? | [MODELS.md](MODELS.md) and [third-party notices](../THIRD_PARTY_NOTICES.md) |
| What did the published ZIP really pass? | [VERIFICATION.md](VERIFICATION.md) and [RELEASE_NOTES_ALPHA.md](RELEASE_NOTES_ALPHA.md) |
| What is implemented versus planned? | [ROADMAP.md](ROADMAP.md) |
| Which Qt source and distribution requirements are relevant? | [QT_SOURCES.md](QT_SOURCES.md) |

## Know which version you are reading about

- **Released package:** `v0.1.0-alpha.1`. Its verification evidence is tied to a specific older commit, platform and executable. Do not project those results onto new builds.
- **Default source:** current `main`. It includes further guided tools, subject effects, manual alpha correction and project files not present in the published ZIP.
- **Feature branches / open PRs:** proposals and experiments until merged into `main`; they may have separate entry points and independent test evidence.
- **Future ideas:** the roadmap describes proposed, not necessarily implemented, capabilities such as generative editing and optional GPU support.

For any issue or PR, link to the relevant code and tests, and record what was actually verified.
