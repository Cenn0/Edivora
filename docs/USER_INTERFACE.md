# Task-first user interface (development source)

The desktop editor is designed for someone who opens it occasionally, rather than
a trained photo editor. This page describes the **source UI**, not the already
published `v0.1.0-alpha.1` Windows ZIP.

## First edit: three steps

1. Open a local JPG, PNG or WebP photo (or drop it into the editor).
2. Pick a clearly named task in **What would you like to do?**:
   **Enhance photo**, **Crop & rotate**, **Blur background (AI)** or
   **Remove background (AI)**.
3. Inspect the preview and choose **Apply**. Then select **Save a photo copy**.
   The imported original file is never overwritten. Undo/Redo and **View
   original** remain at the top.

The two AI shortcuts open the **subject preview workspace**. That workspace
detects a foreground selection locally, shows the result, and applies it
only after confirmation. The original direct background removal command
still exists under **Show more options** for compatibility; unlike the
quick shortcut, it commits on completion without a separate preview.

**Show more options** is collapsed at first launch. It reveals the existing
guided Light/Looks/Crop/Background editor, detailed subject effects,
direct background removal, foreground brush, exact sliders and
rotation/crop/resize controls. Power users can still use `Ctrl+E`
for guided editing, `Ctrl+Shift+E` for subject editing and the
`File`/`Edit` menus. Saving a reusable `.laip` editing project
is under `File > Save project` (`Ctrl+S`); this is distinct from exporting
an image.

## Progressive-disclosure rules

| Situation | Behaviour |
| --- | --- |
| No image | Quick actions disabled; open-photo guidance shown |
| Image ready | All four quick actions enabled; advanced options stay collapsed until requested |
| In a pending slider preview, manual crop or mask brush | Quick actions are disabled. The advanced panel automatically opens and cannot close until **Apply** or **Discard/Cancel** completes the edit |
| Original comparison | Changes disabled until returning to edited view |
| Local AI job | Changes disabled; cancel control and explanatory status remain available |
| Modal editing/subject workspace | Parent editing controls disabled; **Apply** or **Cancel** governs acceptance |

This avoids a common dead end: collapsing the only visible Apply/Discard
buttons while a preview is unfinished. The disclosure state is preserved when
switching between German and English. Open menus and keyboard shortcuts remain
available without duplicating image-processing implementations.

## Translation and implementation

The shared main-window translations and contextual instructions live in
`src/local_ai_photo_editor/ui/strings.py`, and the task-first layout in
`ui/guided_window.py`. The original specialized widgets and their signal
connections are **moved into** the optional panel, not replaced. Processing
remains in `core/` or in the existing isolated AI job, and the privacy /
export constraints in `AGENTS.md` remain unchanged.

Maintain both German and English labels (matching keys/placeholders); avoid
introducing parameters such as model size, masks or inference backends into
the four initial quick tasks. Preserve explicit preview/accept/discard
behaviour and keep disabled states explainable.

## Verification and limits

- `PYTHONPATH=src python -m unittest discover -s tests -v` covers UI
  composition, languages, enabled states, task routing and panel disclosure,
  in addition to the existing editor checks.
- `python -m compileall -q src tests tools` catches syntax errors.
- `PYTHONPATH=src python tools/capture_editing_ui.py <output-dir>`
  captures default/expanded main views (DE/EN) and the four editing tabs
  from synthetic photos; CI retains artifacts from Linux and Windows.
- A screenshot capture is **not** an interactive usability study.
  Screen-reader navigation, Windows 11 high-DPI behavior, small displays
  and the clean-machine packaged release need manual acceptance before
  calling this version end-user validated.
