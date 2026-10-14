# Edivora: Qt UI implementation status

This document describes the **development-source UI**, not the already released
`v0.1.0-alpha.1` portable Windows package.

**Update 2026-10-14 — three-tool MVP:** The default application entrypoint
now opens a separate `ui/launcher.py` start screen. It can spawn any subset of
Photo, Video and Audio as independent instances of the same application
executable using `--tool photo|video|audio`; the Photo shell can also start
Video or Audio directly. The Video and Audio MVPs are implemented in
`ui/media_window.py` with `QMediaPlayer` playback, region selection,
volume/fade controls where applicable, and safe local FFmpeg exports in
`core/media.py`. They are not full multitrack/project editors.
See [MEDIA_MVP.md](MEDIA_MVP.md). The older descriptive bullets below
document the preceding Photo-only UI milestone; phrases such as "planned" or
"disabled" in those historical milestones no longer describe the new
development branch.

## Delivered UI scope

- **One desktop shell:** Edivora identity and consistent top actions; labelled
  Start, Photo, Video (planned), Audio (planned), Help and Settings navigation.
- **Start:** photo picker, .laip project picker, local-file drag and drop through
  the existing window handler, three media cards, and a Continue editing path
  when a photo is already open. Video and Audio remain disabled; there are no
  placeholder timelines, decoders, network services or pretend export paths.
- **Photo:** existing protected source and pixel processing, canvas, original
  comparison, crop and alpha-only mask brush, history, project and file export.
  Canvas and inspector are separated by a resizable splitter.
- **Task-first inspector:** enhance, crop/rotate, blur background (local AI) and
  remove background (local AI). More tools expands existing widgets without
  recreating their history logic. Pending adjustments, crop and mask corrections
  force the precision panel open; navigation back to Start is blocked until
  the active transaction is completed or discarded.
- **Consistent colors:** `ui/theme.py` is the single token map and Qt stylesheet.
  Photo canvas, editing dialog and subject/AI dialog use the same palette.
  Core navigation/action controls have textual accessible names and focus styles.
- **German and English:** common text remains in `ui/strings.py`; specific
  editing and subject dialog dictionaries remain separate and localized.

## Current component boundaries

| Module | Responsibility |
| --- | --- |
| `ui/window.py` | Shared shell, photo stage, importer/exporter, history and preview gating |
| `ui/guided_window.py` | Simple tasks, advanced disclosure, existing dialog lifecycle |
| `ui/theme.py` | One palette and stylesheet for shell, canvas, controls and dialogs |
| `ui/canvas.py` | Fitted still-image preview and brush/crop interaction |
| `ui/editing_dialog.py` | Separate reversible full-size preview for standard effects |
| `ui/subject_dialog.py` | Separate cancellable local subject inference and preview |

The old `local_ai_photo_editor` Python module and `.laip` project format are
preserved. Edivora's full icon/window/package identity belongs to the separate
branding work; this UI currently uses an in-app wordmark and temporary glyph.

## Important limitations

- **Photo workflows are not all inline.** Quick tasks for complex editing and
  local AI still open their verified preview dialogs. Migrating each workflow
  into a persistent inspector requires independent tests for asynchronous
  cancellation, before/after, Apply/Cancel and Undo/Redo.
- The small-width toolbar uses compact comparison/history controls; it still
  needs real Windows text-scaling and screen-reader acceptance at 125%, 150%
  and 200%. Color tokens are not proof of WCAG compliance.
- A hidden/resized editor stage does not discard the image, history or project.
  Start is a navigation view, not a project-close action.
- Video/Audio playback, simple trimming and new-file export are implemented in
  the later media-MVP branch. **No** multitrack timeline, reusable project format,
  per-operation history, audio/video AI model or cross-codec guarantee exists.
  No cloud model hosting or runtime download is introduced.
- This does not change the contents of the published `alpha.1` Windows ZIP.

## Verification

From a checkout of this branch with dependencies installed:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests tools
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python tools/capture_editing_ui.py /tmp/edivora-captures
```

For a Windows acceptance pass, additionally exercise import/drop, language
switching, Ctrl+Z/Y, comparison, pending crop and brush corrections, AI job
cancel, project save/open and source-safe PNG/JPEG/WebP export with real Qt
windows. Check the smallest supported window and display scaling, then verify
the actual packaged executable independently. CI failure before job startup
must not be reported as a failed or successful application test.

## Follow-up

1. Integrate the final branding assets with the in-app wordmark.
2. Migrate simple Photo preview tools into an inspector with sticky
   Apply/Cancel **only after** parity tests pass.
3. Build tested, separately scoped Video and Audio media pipelines before
   enabling their navigation and start cards.
