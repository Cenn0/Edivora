# Edivora — unified UI/UX design system

**Status:** design specification from 14 October 2026. **Phase 1 is implemented in the source UI branch, with Qt/Windows verification still pending.** See [UI implementation status](UI_IMPLEMENTATION.md).  
**Scope:** the Photo editor and limited Video/Audio MVP workspaces.

**MVP implementation update (2026-10-14):** the application now has a
separate start launcher and independent Qt windows for Photo, Video and Audio,
all started by the **same executable**. This document also includes design
aspirations beyond the implemented MVP (e.g. multitrack timelines, detailed
timeline-based trim, Undo/Redo and video/audio AI); these should **not** be
presented as features that already exist. See
[MEDIA_MVP.md](MEDIA_MVP.md) for the concrete current capabilities and
[UI_IMPLEMENTATION.md](UI_IMPLEMENTATION.md) for implementation status.  
**Clickable preview:** [open the standalone layout prototype](prototypes/edivora-shell.html) in a local browser after saving it as an HTML file. It is an interactive design demonstration, not a functioning editor.  
**Related work:** [task-first Photo PR #10](https://github.com/Cenn0/LocalAiPhotoEditor/pull/10) and [Edivora branding PR #11](https://github.com/Cenn0/LocalAiPhotoEditor/pull/11) remain separately open. The implementation branch reuses the task-first Photo approach; the official SVG brand assets are not yet integrated. Do not confuse source UI changes with the published `v0.1.0-alpha.1` package.

## 1. Product experience

**One application. Three media workspaces. One interaction language.**

A first-time user should recognize the same steps in each editor:

1. Open a local file (or an existing project).
2. Pick the intended outcome using plain-language task cards.
3. Inspect a live, disposable preview.
4. Accept the change or cancel without modifying the project.
5. Export a new media file; optionally save a project for later editing.

The preview/accept/cancel model, status messaging, AI handling, history and export flow must behave consistently. **Media-specific editing surfaces must not be artificially identical.** Photo needs a large still canvas, Video needs playback plus a timeline, and Audio needs a waveform and transport controls.

### Non-goals

- No three unrelated executables or layouts: launch distinct processes of the same bundled application.
- No professional editing terminology on the initial screen unless essential.
- No default chat window dominating the editor.
- Do not infer a rich multitrack editor, speech model or GPU capability from the limited Video/Audio MVP.
- No forced cloud account, model server, telemetry, hidden network access or automatic model download.
- No immediate rewrite to QML, a web runtime or a new framework merely to achieve this layout.
- No assumption that a new suite name changes old `.laip` files or historical binaries.

## 2. Information architecture

Navigation rail (left, 68 px wide at normal sizes):

- **Start:** home screen with import affordance and three media cards.
- **Foto / Photo:** current workspace (functional scope according to README).
- **Video:** future workspace; clearly marked *Geplant / Planned* until implemented.
- **Audio:** future workspace; clearly marked *Geplant / Planned* until implemented.
- **Hilfe / Help** and **Einstellungen / Settings:** bottom of rail, accessible without clutter.

Do not make “AI” a fourth workspace: AI is a capability in relevant tasks. Use the suite mark and the word “Edivora” in the global identity, and the workspace label “Foto”, “Video” or “Audio” in the document header. Navigation items need both an icon and a visible or accessible text name, and the active one needs more than a color difference.

### Shared desktop composition (reference width 1280–1440 px)

| Region | Recommended dimensions | Purpose |
| --- | --- | --- |
| Global top bar | 56–64 px high | Suite identity, active project and saved status; Undo, Redo, Compare, export |
| Workspace rail | 68–76 px wide | Start / Photo / Video / Audio / Help / Settings |
| Main stage | Flexible, majority of width | Photo canvas, video monitor or audio waveform |
| Context inspector | 320–360 px wide, resizable | Task selection, active tool and controls, sticky Apply/Cancel |
| Lower editor dock | Media-dependent, resizable | Hidden for Photo; video timeline; audio tracks/time ruler when needed |
| Status region | 24–32 px high or inline | Zoom/time/dimensions, background task state, local-only message |

Proposed layout sketch:

~~~text
+------------------------------------------------------------------------+
| Edivora  / Photo - Portrait                         Undo Redo   Export  |
+-----+--------------------------------------+---------------------------+
|Start|                                      | What would you like to do?|
|Photo|           MEDIA CANVAS               | Improve photo             |
|Video|        fit / zoom / compare          | Crop & rotate             |
|Audio|                                      | Blur background (AI)      |
|     |                                      | Remove background (AI)    |
|     |                                      | More tools (collapsed)    |
|-----+--------------------------------------+---------------------------+
|Help |    status / zoom / relevant media metadata                   |
+-----+----------------------------------------------------------------+
~~~

For **Video**, split the stage vertically into monitor and lower timeline, while keeping the inspector in exactly the same place. For **Audio**, emphasize the waveform and transport (play/pause, time and selection), and display additional tracks only when the editing workflow needs them. Do not show a dead or empty timeline in Photo.

### Start screen

Lead with one sentence: “Was möchtest du bearbeiten?” / “What would you like to edit?” Show exactly three cards, each with a medium icon, an outcome phrase and a concise supported/planned status.

- **Foto bearbeiten / Edit a photo** — opens a photo or project.
- **Video bearbeiten / Edit a video** — *Geplant / Planned* while unimplemented.
- **Audio bearbeiten / Edit audio** — *Geplant / Planned* while unimplemented.

Offer a prominent drag-and-drop/import region and “Projekt öffnen / Open project”. An optional local recent-project list must avoid silently storing or exposing thumbnails from private files; allow users to clear it. The first launch must not require an account, wizard or model setup.

## 3. Same mental model across the workspaces

### Shared task inspector

At rest the inspector asks **“Was möchtest du tun?”**, not “Which parameters do you want to configure?” Show 3–5 typical tasks; disclose other capabilities behind “Weitere Werkzeuge / More tools”. Once a task is chosen, replace the card list with:

1. Back affordance + clear task title.
2. One-line explanation, optional example or hint.
3. At most the 2–4 most useful settings at first; reveal detailed options on demand.
4. **Sticky footer:** “Abbrechen / Cancel” and one primary “Übernehmen / Apply”.
5. Optional “Einstellungen zurücksetzen / Reset settings”.

The selected task remains visible when its preview is pending. A pending operation must **never be hidden** by collapsing a panel or changing language. Do not open separate full-screen/modal preview windows for everyday photo edits after the embedded inspector migration; preserve existing dialogs until equivalent undo, processing and cancellation behavior is verified.

### Photo (existing; expand incrementally)

First tasks: **Foto verbessern / Enhance**, **Zuschneiden & drehen / Crop & rotate**, **Hintergrund unscharf (KI) / Blur background (AI)** and **Hintergrund entfernen (KI) / Remove background (AI)**, matching proposed PR #10.

Advanced groups: **Licht & Farben / Light & color**, **Looks**, **Ausschnitt / Crop**, **Hintergrund / Background**, **Motivauswahl / Subject** and **Kanten korrigieren / Refine edges**, gated by actual functionality. Photo keeps a large central image and zoom/fit/comparison affordances. Only show transparency checkerboard when relevant.

### Video (future; no implemented claim)

Suggested initial tasks, subject to an actual supported media pipeline: **Anfang/Ende schneiden / Trim**, **Clips anordnen / Arrange**, **Licht/Farbe anpassen / Adjust**, **Ton bearbeiten / Edit sound**, **Exportieren / Export**. Playback stage on top; below it an easy-to-read timeline with a visible playhead, large clip handles, limited default track complexity and horizontal zoom. Additional tracks, keyframes and transitions are progressively disclosed.

Potential AI tasks such as captioning or subject tracking must remain unadvertised or marked planned until local models and end-to-end tests exist.

### Audio (future; no implemented claim)

Suggested tasks: **Zuschneiden / Trim**, **Lautstärke anpassen / Level**, **Stille entfernen / Remove silence**, and **Rauschen reduzieren / Reduce noise** (AI label only if inference is actually used). Primary surface is a waveform with a clear selection region, scrubbing and playback. Time controls belong in the same location and style as Video transport. A spectrogram or multitrack mixer is an advanced workspace, not the first-launch interface.

Do not specify supported output formats, latency, realtime effects or codec redistribution until the chosen processing pipeline is validated.

## 4. Interaction contract and states

Every workspace must implement the same user-observable states:

| State | User sees | Required behavior |
| --- | --- | --- |
| Empty | One large import/drop target and useful task suggestions | Editing controls disabled with explanation |
| Ready | Current accepted result, task shortcuts | Undo/Redo only when available |
| Preview pending | Pending result visibly marked as preview | Apply commits one history entry; Cancel restores accepted result |
| Processing | Plain-language job status, indeterminate progress unless measured, Cancel | No partial or stale result silently committed |
| Comparing | Before/after toggle, split view or hold-to-compare | Source of “before” must be explicit: original vs pre-tool snapshot |
| Exporting | Output destination, format, relevant quality options, progress | Validate and protect source, handle interruption safely |
| Error | Explanation and recoverable next action | Preserve accepted edits; no raw technical traceback |
| Unsaved changes | Visible project-dirty state and contextual confirmation | Switching files/workspaces or closing cannot lose edits silently |

Terminology is invariant: **“Projekt speichern / Save project”** saves an editable session; **“Exportieren / Export”** produces a new viewable/listenable media file. Use one primary CTA per region. Labels should always make clear which output is produced.

Keyboard conventions: `Ctrl+O` open, `Ctrl+S` save project, `Ctrl+Shift+S` (or the consistently documented Save As/export shortcut) export, `Ctrl+Z` Undo, `Ctrl+Y` / platform equivalent Redo. Reuse established shortcuts unless there is a documented migration. For Video/Audio, Space can toggle playback only when it does not interfere with focused form fields.

### AI UX is local-first and honest

- Put a small **KI / AI** label on tasks that really run a learned model, not on classic filters, auto contrast or signal-processing algorithms.
- Show a concise local-processing indication and the task's effect, e.g. “Motiv wird erkannt – lokal auf diesem Gerät”.
- Show transparent model availability: ready, not installed, unsupported on this machine or job failed. Never present an unavailable task as enabled.
- Expose cancellation, preview, before/after and Undo/Redo as for non-AI tools.
- No surprise download, account sign-in or external request. A build-time packaged model is distinct from runtime network access.
- Never show fictitious numerical progress when the inference backend exposes no reliable progress information.
- Bound input sizes and clean up temporary working files; worker isolation for cancellation is not a security sandbox.

## 5. Visual identity and concrete design tokens

Honor PR #11's proposed **Edivora** brand palette. Use one neutral dark foundation in every workspace and the same CTA colors, rather than theme-switching the entire app for Photo/Video/Audio.

| Token | Value | Intended use |
| --- | --- | --- |
| `background.app` | `#171B2D` | App shell / midnight |
| `background.panel` | `#202638` | Rail and inspector surfaces |
| `background.elevated` | `#2A3146` | Tool cards, controls |
| `border.default` | `#3C465F` | Dividers and surfaces |
| `text.primary` | `#F5F4FF` | Main labels |
| `text.secondary` | `#B9C3D9` | Explanations |
| `text.muted` | `#98A4BC` | Secondary metadata |
| `accent.primary` | `#4FF3D3` | Important actions with dark foreground |
| `accent.primary.hover` | `#18B9C6` | Hover/active variant (check its foreground contrast) |
| `accent.selection` | `#7792FF` | Focus, selection and time ranges |
| `accent.ai` | `#C98CFF` | Small AI glyphs/badges, not a global second primary |
| `accent.error` | `#FF9EA8` | Error copy/icon |

Dark palette contrast checks for the proposed pairs: primary text on app background approx. 15.7:1, secondary text on panel approx. 8.5:1, muted text on panel approx. 6.0:1, teal on app background approx. 12.3:1. These are computational checks for selected pairs, **not** a comprehensive accessibility audit or a claim for every state.

Typography: system **Segoe UI** on Windows, sans-serif fallback elsewhere; 14 px body, 16 px section title, 20–24 px page title, 12–13 px supplemental copy. No downloaded/bundled font. Use sentence case, avoid all caps for labels. Keep German translations short but never truncate essential actions.

Spacing: 4/8/12/16/24/32 px scale. Card radius 12 px; control radius 8 px. Standard interactive targets at least 44 px high. Icons 18–22 px with consistent stroke weight; text labels for core navigation and tools. Use limited motion (120–180 ms for small feedback; respect reduced-motion setting), no distracting gradients or default animations behind media.

### Component library (single ownership)

- `AppShell` — title bar, rail, top actions, tool panels and status region
- `StartCard` — media mode, short description and honest availability
- `TaskCard` — verb-led action with icon, one-line hint and optional AI label
- `ToolInspector` — one focused task + detailed settings disclosure
- `PropertySlider` — label, value, reset, keyboard actions and accessible range
- `PreviewSurface` — fit/zoom, pan, transparent background and comparison
- `TransportBar` — for Video/Audio only; same play/pause/time vocabulary
- `TimelineView` / `WaveformView` — media-specific, not global widgets
- `JobIndicator` — progress, cancellation and local-state wording
- `ExportDialog` — consistent flow, workspace-specific formats and validation
- `Toast/InlineError` — non-blocking feedback, explanation and recovery

Use icons that convey actual tasks, never an icon-only navigation system, and do not color-code safety or functionality without explanatory words.

## 6. Responsive desktop and accessibility

Reference layout at 1280×800; validate 900×660 (current Photo window minimum), 1024×768, 1366×768, 1920×1080, 125/150/200% scaling and Windows text scaling. **These are test targets, not verified support claims.**

At tight widths: collapse the global rail to icons with persistent accessible names; permit collapsing the inspector into a labeled drawer, but automatically keep any pending Apply/Cancel accessible. Video timeline stays resizable rather than disappearing mid-edit. Preserve keyboard access to the import, preview, inspector and export path.

Provide visible 2 px keyboard focus, supported tab order, labels/accessible names for each slider and mode, helpful tooltip + persistent wording where possible, correct screen-reader announcements for task progress, reasonable contrast in hover/selected/disabled states and a way to reduce animation. Validate with keyboard-only navigation and a screen reader rather than declaring WCAG compliance based on palette alone.

Keep matching German/English strings and test both in the smallest window, including long errors and dynamic status text.

## 7. Integration with the existing Qt architecture

**Technical feasibility:** Qt Widgets supports resizable splitter layouts (`QSplitter`), switched editor views (`QStackedWidget`) and stylesheet-based theming. Official references: [QSplitter](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSplitter.html), [QStackedWidget](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QStackedWidget.html), [Qt style sheets](https://doc.qt.io/qt-6/stylesheet-syntax.html).

**Recommended implementation:** incremental refactoring of the existing Qt Widgets app; do not rewrite the processing core. Factor the existing `ui/window.py` and `ui/guided_window.py` layout into reusable shell elements without duplicating editing logic.

**Actual Phase 1 module ownership:** `ui/window.py` provides the shell and Photo stage; `ui/guided_window.py` provides beginner tasks, advanced disclosure and safe dialog lifecycles; `ui/theme.py` owns color tokens and the Qt stylesheet. Existing `ui/canvas.py`, `ui/editing_dialog.py` and `ui/subject_dialog.py` reuse the theme. The broader split below is a **future refactoring direction**, not an already-created directory tree.

Proposed module ownership, to be adjusted before implementation:

~~~text
ui/
  app_shell.py                # shared main window, navigation, common actions
  theme/
    tokens.py                 # one Python token registry
    stylesheet.py             # Qt stylesheet assembled from tokens
  widgets/
    task_card.py
    tool_inspector.py
    preview_controls.py
    job_indicator.py
    export_flow.py
  workspaces/
    photo.py                  # adapter to existing Photo canvas/controllers
    video.py                  # only when actual playback/editing is built
    audio.py                  # only when actual waveform/editing is built
  strings.py                  # common localization; media strings grouped
~~~

Do not implement CSS custom properties as a browser-like styling system in Qt Style Sheets; build the theme using Python token values and Qt-supported selectors/properties. Retain `core/` as Qt-independent and preserve existing `ai/` process/input safety contracts. A new Video/Audio media core should be independently testable; share only genuine abstractions, such as history, project lifecycle, task state and UI components. Reuse versioned project contracts but **do not repurpose the existing `.laip` file format for video/audio**.

**Supported vs recommended:** This layout is technically achievable in Qt Widgets and the needed widget classes are officially documented; it does not mean that the complete multi-media application is officially certified, implemented or tested. Incremental migration is the project best-practice recommendation. Local-only inference, bounded untrusted input and source-protecting exports are the security requirements.

## 8. Migration roadmap and acceptance criteria

| Phase | Change | Acceptance gate |
| --- | --- | --- |
| 0 — Align | Review/merge PR #10 (task-first Photo) and PR #11 (branding) after their own checks; reconcile any overlapping UI changes | Product labels, assets and the four Photo tasks match this specification; no premature Video/Audio claims |
| 1 — Foundation | **Implemented in the source UI branch:** theme tokens, shared shell, workspace rail, start view and beginner inspector | Automated Qt/DE/EN and Windows packaging verification are still required before release |
| 2 — Photo UX | Move frequent dialog workflows inline into the context inspector one at a time, preserving explicit commit/cancel | Preview and Undo/Redo behave exactly; no operation is lost when panel is collapsed |
| 3 — Media capability | Implement Video and Audio processing, media views and export *separately*; activate their cards only when feature-complete | Verified decoding, playback/edit, codecs/licensing, cancellation, project format and package tests |
| 4 — Usability & release | Keyboard/screen-reader tests, small-window and DPI testing, 5 novice-user tasks, packaged offline acceptance | No task dead-ends; source is protected; install/runtime claims backed by measurements |

Photo-specific regression criteria: opening a file by click/drop, task choice, explicit preview/Apply/Cancel, before/after semantics, Undo/Redo, mask editing, DE/EN labels, project saving and source-safe export all work with actual image processing.

Suite criteria: identical location and meaning of project, Undo/Redo, processing indicator, Compare and Export; a workspace switch with unsaved edits gives an explicit decision; unavailable modules are visible as planned but not interactive fake tools. Existing packaging and CI must continue to work while the app is migrated.

**Decision summary:** Build *one shared, approachable editor shell* with a stable task inspector and three media-specific working surfaces. Preserve the current Qt/Python core and existing safety contracts. A dedicated timeline/waveform only appears where it makes sense. Ship the redesigned Photo experience first; Video and Audio remain clearly planned until usable.
