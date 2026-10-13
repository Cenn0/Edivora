# Guided photo editing

Status: development source after the published `v0.1.0-alpha.1` portable Windows package. These tools do not require a new model, account, server or dependency. They are conventional local image operations, not generative AI.

## Starting an edit

1. Open a photo. In **More editing tools**, choose **Light & colors**, **Looks**, **Crop & mirror** or **Design background**. The same workspace is available from the Edit menu or `Ctrl+E`.
2. Change a control and inspect the preview. Tabs share one pending edit, so a crop, a look and a color correction can be combined.
3. **Show before** compares against the accepted image at the moment the workspace opened. It does not necessarily show the original imported photo; the main window's Original button does that.
4. Use the arrow beside a slider to reset just that value, **Reset section** for the current tab, or **Reset all** for the complete pending edit.
5. **Apply** calculates the latest settings at full resolution and adds one history step. **Cancel**, Escape or closing the workspace discards the pending edit. Undo/Redo in the main window can reverse/reapply an accepted result.

The editor disables opening these tools during an unfinished basic adjustment, crop, mask correction, original comparison or AI job. Finish or cancel that operation first. Export and project saving continue to use accepted images, never an unaccepted workspace preview.

## Available tools

| Area | Controls | What they do |
| --- | --- | --- |
| Light & color | Gently improve; darker/brighter; brighten dark areas; dim bright areas; cooler/warmer; color strength; contrast; sharpen details; automatic correction | Adjust the existing photo with visible values and explanations. Tonal corrections preserve the alpha channel. |
| Looks | Natural, Vivid, Soft, Warm, Black & white, Sepia; look strength; darken image edges | Blend a named look into the current edit. A strength of zero disables the look without resetting other controls. |
| Crop | Square 1:1, landscape 4:3, photo 3:2, widescreen 16:9, portrait 4:5, vertical 9:16; horizontal/vertical crop position; both mirror directions; 90-degree rotation | Keep exact integer crop ratios without stretching the photo. Position sliders shift the retained rectangle to keep the subject in view. The existing free-selection crop and resize tools remain available in the main window. |
| Background | Keep unchanged, solid color, own local photo; background blur | Fill transparent areas using real alpha compositing. Background photos are center-cropped to cover the result. Blur affects the chosen background photo, not the opaque foreground subject. |

**Gently improve** sets automatic correction to 60%, dark-area brightening to 15% and bright-area dimming to 10%. Other controls retain their values. It is a conservative starting suggestion, not an automatic claim that the photograph will look better. Automatic correction uses a bounded luminance histogram adjustment; fully transparent pixels do not affect the histogram, and near-flat histograms are left alone.

Every slider has a keyboard-accessible name, a visible numeric value and a short tooltip. The interface is available in German and English. Controls are grouped by task instead of model settings or technical color-space parameters.

## Replacing a background

First use the main window's local **Remove background** operation, then correct its mask where necessary. The background tab becomes usable when the accepted image actually contains transparent pixels, including partially transparent ones. An RGB image or a fully opaque RGBA image is not sufficient.

Choose a solid color or open your own JPEG, PNG or WebP background photo. The normal image loader handles orientation, supported color profiles and image limits. The application never uploads or downloads the photo. The selection stays in this editing session; its absolute source path is not added to the project.

The foreground is composited over the new background using its existing alpha. Partially transparent edges therefore blend with the backdrop. A completely opaque backdrop produces an opaque result; use Undo to recover the previous transparency. Existing mask mistakes, missing foreground pixels and background-colored edge contamination are not automatically repaired by replacement or blur.

This is **not** automatic portrait-background blur on an unsegmented photo. It softens a separate background image behind an existing cutout.

## History and project files

All settings in one workspace produce one reversible image snapshot. The existing `.laip` project format saves the accepted original/current/history pixels without a schema change. It does **not** save these slider settings as editable adjustment layers. Opening the workspace again starts with neutral settings applied to the currently accepted pixels. To revise a previously accepted operation without stacking adjustments, undo that operation first.

The original photo and background-photo files are not modified. Existing export destination protection, metadata removal and atomic file writes remain in effect. Background replacement may intentionally change transparency; light/color corrections and looks do not.

## Processing and limits

- The same validated recipe is used for preview and final rendering. Preview images are smaller; filtering, background fitting and integer crop rounding can produce small differences at full resolution. A thumbnail is not a pixel-exact promise for every edge of the exported result.
- The full-resolution render runs in a worker thread, away from widgets. Cancel requests are checked between stages and processing tiles. A native image-decoding or filtering call may need to finish before the next cancellation check. Cancellation never publishes a partial image.
- UI preview calculation, initial image copies/histogram analysis and background-file loading currently run synchronously. The implementation does not guarantee a completely stall-free interface for maximum-size photos or slow storage.
- Color operations use bounded float tiles. The normal 40-million-pixel input limit still applies. Pillow images, history and working copies also occupy memory; there is no fixed total RAM guarantee.
- This is an 8-bit, display-referred sRGB pipeline, not RAW processing, HDR editing, optical deblurring or reconstruction of clipped highlights. Excessive sharpening can create halos. No missing detail is generated.
- Very small images can be too small for a requested exact crop ratio. Extremely thin images can also exceed practical thumbnail-preview limits; the editor reports a failed preview rather than inventing pixels or accepting an empty image.
- No new packaging, GPU compatibility, Windows 11 clean-machine acceptance or AI segmentation-quality claim follows from these source changes.

## Implementation and verification

`core/recipes.py` contains immutable validated recipes, image geometry and local rendering. It has no Qt, inference-engine or network dependency. `ui/editing_dialog.py` owns the task tabs, pending previews and cancellable full-resolution render. `ui/guided_window.py` composes this workspace with the existing editor and checks document identity/revision before accepting a result. The public lazy `ui.EditorWindow` entry point includes these tools while headless core imports remain independent of Qt.

`tests/test_recipes.py` checks numerical directions, alpha/input preservation, exact geometry, compositing, tile boundaries, input limits and cancellation. `tests/test_editing_ui.py` checks translations, actual Qt controls, preview/accept/cancel behavior, full-resolution rendering, stale-result rejection, failures and Undo/Redo integration. Existing project, mask, export and AI-protocol tests also run in source CI.

`tools/capture_editing_ui.py` renders the actual main window and all four new tabs in both languages with a synthetic fixture. Fast Python checks run the source suite on Ubuntu 24.04 and Windows Server 2022 with Qt's offscreen platform, and retain test logs and captures as workflow artifacts. Successful source tests and captures do not constitute a new compiled portable release or an interactive usability study.
