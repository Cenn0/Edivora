# Edivora visual identity and naming

**Public product:** Edivora · **Tagline (DE):** Einfach kreativ. Alles lokal. · **Tagline (EN):** Create simply. Stay local.

## Product architecture and labels

- **Edivora Photo** — current editing workspace; photo formats, local segmentation and standard corrections are supported to the extent documented in the README. This is not a claim of a stable release.
- **Edivora Video** — future module; neither a timeline editor nor a video AI model is currently implemented.
- **Edivora Audio** — future module; neither a waveform editor nor an audio AI model is currently implemented.
- **Edivora AI** is a capability used by relevant tools, **not** a fourth application or a promise that classic filters are AI-generated.

The public brand does not alter the local-first design: no accounts or runtime cloud inference are required. Avoid labeling traditional image filters as AI.

## Identity assets

All primary identity artwork is authored as small, readable, self-contained SVG files in `src/local_ai_photo_editor/assets/`.

| Asset | Usage |
| --- | --- |
| `edivora-mark.svg` | Main UI icon, app/taskbar icon source and repository identity |
| `edivora-mark-mono.svg` | Single-color icon for restricted contexts |
| `edivora-wordmark.svg` | README, welcome or help screens |
| `edivora-banner.svg` | Media-workspace overview; explicitly labels future modules |

**Palette:** Midnight `#171B2D`; teal `#4FF3D3` / `#18B9C6`; blue `#7792FF` / `#4E56E9`; violet `#C98CFF` / `#8759E9`; ivory `#F5F4FF`. In-app body text must remain legible and controls must not rely on color alone. Prefer the icon alongside the full name, not as the only label.

The Windows build derives its ICO at build time from `edivora-mark.svg` through `tools/brand_assets.py`. Source builds render the same embedded SVG through QtSvg. No font is bundled or downloaded. Do not replace these deterministic build assets with externally hosted images or runtime requests.

## Identity and compatibility decisions

- `local_ai_photo_editor` remains the Python import package and `python -m local_ai_photo_editor` remains a supported developer entry point. Renaming every import immediately would create needless compatibility and deployment risk.
- Existing `.laip` projects and their `local-ai-photo-editor-project` format identifier stay unchanged: renaming the format would break old archives. Future media project formats require separately designed, versioned schemas.
- Historical `v0.1.0-alpha.1` downloads, file names and their checksums continue to use `LocalAiPhotoEditor`. They are historical *binaries*, not Edivora-branded builds.
- New Windows development packages use `Edivora.exe` and the `Edivora/` folder. The release publisher for the immutable historical alpha remains intentionally unchanged.
- The GitHub repository URL can remain the historical `Cenn0/LocalAiPhotoEditor` until its owner explicitly renames it; GitHub rename, release tags and package identity are distinct operations. Review existing links, CI checks and integrations before renaming the repository.

## Trademark and domain diligence

A web search on 14 October 2026 did not surface an obvious same-name image/video/audio editor for “Edivora”, but **this is not a legal clearance, official database search, or guarantee of domain availability**. Search DPMAregister, EUIPO/TMview and relevant jurisdictions, related classes and phonetic variants before public launch. Do not add `®` or claim a registered mark. Ensure design assets and brand identifiers remain generic enough to change if conflicts emerge.
