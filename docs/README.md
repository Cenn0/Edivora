# Edivora documentation

[← English README](../README.md) · [Deutsch](../README.de.md)

Edivora is an offline-first photo, video and audio editing suite. **Current source version: 0.4.0a1 (development).** The historical photo-only `v0.1.0-alpha.1` package does not include today's media editors. **No Windows package of the current suite is approved for public redistribution.** See [third-party licensing](../THIRD_PARTY_NOTICES.md) and [release checks](PUBLIC_RELEASE_CHECKLIST.md).

Some detailed guides are currently written primarily in German; the main README and this index are in English.

## Get started

| Goal | Guide |
| --- | --- |
| Set up the current development source and prepare local models | [Getting started](GETTING_STARTED.md) |
| Understand photo tools and foreground editing | [Photo adjustments](EDITING_TOOLS.md) · [Subject selection](AI_SUBJECT_TOOLS.md) · [Mask refinement](MASK_REFINEMENT.md) |
| Edit video and audio, and understand single-lane timelines | [Media workflows](MEDIA_MVP.md) · [Projects and local AI](MEDIA_PROJECTS_AI.md) |
| Learn file portability and original-file safeguards | [Photo project format](PROJECT_FORMAT.md) · [Media project format](MEDIA_PROJECTS_AI.md) · [Portable media CLI (source only)](PORTABLE_MEDIA.md) |
| Understand what DnCNN can and cannot restore | [Video restoration](VIDEO_RESTORATION.md) |

## Engineering and contributing

- [Architecture and process boundaries](ARCHITECTURE.md)
- [Model provenance and offline requirements](MODELS.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [Contributor guide](CONTRIBUTING.md) · [AI-assisted contributor rules](../AGENTS.md)
- [Design system](DESIGN_SYSTEM.md) · [UI implementation](UI_IMPLEMENTATION.md) · [Brand assets](BRAND.md)
- [Roadmap](ROADMAP.md) · [Security reporting](../SECURITY.md)

## Evidence, historical records and distribution

- [Historical photo-only alpha verification](VERIFICATION.md) · [historical release notes](RELEASE_NOTES_ALPHA.md)
- [Current 0.4 development changes](RELEASE_NOTES_RESPONSIVE_SUITE.md) · [responsive media UI and restoration](VIDEO_RESTORATION.md)
- [Windows binary release checklist](PUBLIC_RELEASE_CHECKLIST.md) · [Qt source obligations](QT_SOURCES.md)
- [Original design concept (historical)](CONCEPT.md)

**Evidence boundaries:** source-implemented ≠ CI-tested ≠ approved Windows distribution ≠ officially supported GPU inference. Local model preparation may download pinned assets; runtime processing uses local inference. Screenshots are test captures, not proof of end-user acceptance.
