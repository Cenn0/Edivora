# Selection and detail tools — opt-in development extension

## Availability

This branch adds a separately launchable source-code extension. **The normal launcher, `main` and previous Windows ZIPs are not switched to these tools by this work.** Attempts to update existing source files were blocked by the connector; the blocked changes are not part of this branch. The extension is isolated in new modules and kept in a draft pull request for review.

With the existing development dependencies installed, run from this branch:

```text
python -m local_ai_photo_editor.detail_editor
```

The standard `python -m local_ai_photo_editor` command still starts the previous composition. The precision entry point is for source development, not a new compiled application or released installer. Model preparation remains the existing explicit build/development step; the application never downloads a model.

## Features

| Tool | Behavior |
| --- | --- |
| Correct AI selection | Add missed regions or remove incorrectly selected regions using a brush. Changes affect an independent selection, not the accepted photo or its alpha. |
| Manual selection | Start from an empty selection and paint a region without loading or running an AI model. This is also available after model/inference failure. |
| Selection history | Undo/redo individual strokes and invert, clear or restore the starting selection. The latter commands are reversible too. |
| Preview navigation | Mouse-wheel zoom anchored to the pointer, 1x–8x the fitted preview. Pan with the middle mouse button, Space+drag or the Pan tool. Plus/minus zoom, arrows pan and Home fits the image. |
| Local temperature | Warm or cool only the selected colors. |
| Local saturation | Boost or reduce colors only in the selected area. Full desaturation makes it grayscale. |
| Existing subject effects | Reuse the corrected selection for background blur, color pop, subject brightening, background dimming, cutout and crop. |

The precision window retains the existing import/export, project snapshots, source protection and accepted-image Undo/Redo workflow. Its AI menu and buttons open the precision workspace; the extra manual action uses `Ctrl+Shift+M`.

## Beginner workflow

1. Open a photo in the precision editor. Choose **Edit AI selection** or **Select an area with a brush**.
2. In **Correct selection**, choose **Add** or **Remove**. Adjust brush size and soft edge only when needed. Purple shows the selected region. A stroke changes the selection after releasing the mouse.
3. Use the wheel or navigation buttons to inspect edges. Panning does not paint. Undo/Redo in this workspace refers to selection actions, not the document's accepted history.
4. Choose **Show result** to leave brush mode. The original-sized selection coordinates are retained even when the preview is zoomed or cropped.
5. Choose an effect, set its strength and compare before/result. Only **Apply** renders the full-resolution result and adds one document history step. **Cancel**, Escape or closing the dialog discards pending changes.

While correction mode is open, Apply is disabled: leave correction mode to inspect the actual effect first. An empty manual selection cannot be applied. **Reset settings** resets the effect controls without deleting the selection journal. **Restore starting selection** restores the initial inferred mask (or the empty manual baseline) and is itself undoable.

**Invert selection** swaps selected and unselected regions. Existing background effects always edit the unselected remainder; local warmth/saturation edits always affect the selected region. Inverting a selection therefore also swaps the meaning of subject and background for these effects.

## Architecture

- `core/selection.py`: validated normalized selection journal and grayscale brush rasterization. The journal stores commands and coordinates, not full-resolution mask snapshots per stroke. A parity test compares its brush output to the established alpha-repair rasterizer.
- `core/local_adjustments.py`: validated local edits. Existing effects delegate to the existing subject adapter; new temperature/color controls reuse the existing recipe renderer and composite into the selection. Alpha and fully hidden RGB are preserved by color edits.
- `ui/navigation.py`: zoom/pan view transform. Pointer input is converted back to normalized image coordinates. View changes are ignored during active drawing to prevent coordinate jumps.
- `ui/precision_dialog.py`: optional composition of the existing subject dialog, independent pending selections, correction controls and full-resolution rendering. The existing child-process inference job remains unchanged.
- `ui/precision_window.py` and `detail_editor.py`: opt-in window/entry point. They deliberately do not modify the standard application launcher.

Selection commands are limited to 128 per workspace. Each brush stroke retains the existing maximum of 2048 normalized points. Every action is validated before rendering begins. A full-size selection is reconstructed only for final application; preview selection processing uses the smaller image. Full-size rendering is cancellable between stages/strokes/tiles. Individual native library calls may finish before cancellation is observed.

## Limits and verification scope

Zoom enlarges the **existing reduced-size preview**, not additional full-resolution source detail. It is not a 100%-pixel or super-resolution view. Preview rasterization and final full-resolution edges/crop rounding can differ. Exact corrected crop dimensions are calculated during final application; the UI labels the reduced crop as a preview.

The extension does not add model quality, generative object removal, content reconstruction or editable layers. Corrections can fix the selected area but cannot reconstruct missing RGB detail or automatically clean color contamination. Selections and journals exist only within a workspace session. `.laip` files continue to save accepted pixels/history, not reusable selections or adjustment parameters.

The 40 MP image limit remains. A bounded journal does not imply a fixed total RAM ceiling: the image, baseline mask, working masks, previews and render copies still consume memory. Preview updates and initial image copies are synchronous; there is no claim of stall-free interaction for every supported image size.

New tests cover brush parity, malformed inputs, cancellation, bounded history, precise input mapping, local-color/alpha invariants, failure recovery, full-size application and document Undo/Redo. Synthetic widget captures are diagnostics, not a usability or segmentation-quality benchmark. `tools/verify_precision_tools.py` additionally exercises real model inference, corrected full-size application and the no-inference manual path in the **source** precision composition. The separate precision workflow uses native Qt on Windows and offscreen Qt on Linux, with a glyph-availability check before accepting captures.

The existing Windows package workflow still builds the standard entry point. A successful result from that workflow must not be presented as a packaged precision-editor acceptance test. Default integration, a compiled precision-editor build, fresh Windows 11 offline acceptance and an interactive usability study remain separate work.

API references used during implementation: [Qt wheel events](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QWheelEvent.html) and [Pillow ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html). These document library operations, not end-user platform acceptance.
