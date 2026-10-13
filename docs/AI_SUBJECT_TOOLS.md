# Local AI subject tools

Development feature after `v0.1.0-alpha.1`. The old published ZIP is unchanged. Use a development package built from a revision containing these tools, or the current source. Runtime processing stays local; this extension adds no dependencies, models, accounts, model servers or automatic downloads.

## What is actually AI here?

The existing checksum-pinned **U2NETP** model runs in a separate local CPU worker and predicts a foreground/saliency selection. The six tools use that selection for deterministic image operations. This is an expansion of what the existing model enables, **not a new or higher-quality segmentation model** and not generative editing.

The selection is computed once per workspace session. Changing effects, strengths or edge softness reuses it, without another model run. Reopening the workspace analyses the currently accepted image again. A saliency mask is neither an object identity nor a calibrated probability/confidence score or a depth map.

## Using the tools

Open a photo, then choose **AI subject tools → Soften background** or **Edit subject with AI**. The Edit menu and `Ctrl+Shift+E` open the same workspace. Finish any pending basic adjustment, free crop or mask correction first.

The workspace selects the subject automatically. It never commits the model result immediately. Enable **Show AI selection** to inspect the purple overlay, choose an effect and adjust its strength. **Show before** compares against the accepted image at workspace opening, not necessarily the original import. **Apply** calculates the latest settings at full resolution and adds one Undo/Redo step. **Cancel**, Escape or closing the dialog discards the entire pending edit.

| Task | Result | Preserved data |
| --- | --- | --- |
| Soften background | Blur the existing background behind the detected subject; no replacement photo needed. | Selected opaque subject colors and original alpha. |
| Color subject, black & white background | Keep subject colors while progressively desaturating the background. | Selected subject colors and original alpha. |
| Brighten subject | Increase brightness only within the selected subject, up to a factor of two at maximum strength. | Unselected background and original alpha; no new detail is synthesized. |
| Darken background | Reduce background brightness while retaining the subject. | Selected subject colors and original alpha. |
| Remove background | Turn the background transparent, with optional softened selection edges and explicit preview/accept. | Original RGB channels; source alpha is multiplied by the selection only once. |
| Crop to subject | Enclose all selected visible regions, with an adjustable 0–40% safety margin. | Retained image pixels, including their original alpha. |

The **Soften selection edge** control smooths the mask boundary. A high value can weaken fine foreground detail. It does not perform hair matting or reconstruct missing subject pixels. The purple inspection overlay is display-only and never enters exported pixels. Changing the task selects a suggested strength; Reset settings restores that task's starting settings.

To soften an existing background, start from a photo that still contains it. A photo already cut out does not contain visible background to reconstruct; undo the cutout first. After accepting a cutout, the existing manual mask tool can restore/remove alpha where necessary. The new workspace does not yet offer an in-place brush to repair the selection for all effects.

## Image quality and honest boundaries

- U2NETP can miss wanted pixels or select unwanted ones, especially with hair, glass, small subjects and similar foreground/background colors. Always inspect the proposed result. This change does not establish improved model accuracy.
- Background blur uses background-weighted, premultiplied filtering to reduce foreground-color halos. It does not recreate obscured background, remove contaminated edge colors or simulate a measured depth field/physical lens. Soft mask boundaries can still produce artifacts.
- Subject brightness and background effects operate on 8-bit sRGB pixels. They cannot recover clipped highlights, infer missing texture or replace a RAW/HDR workflow.
- Automatic cropping encloses all mask regions at the fixed selection threshold, ignoring fully transparent source pixels. It is not face-aware composition and may retain extra background or cut too tightly when the mask is wrong. Preview and the margin slider remain essential.
- Effects that only change colors preserve the source alpha exactly. Cutout intentionally changes alpha; crop intentionally changes dimensions. Applying a background-color effect does not silently flatten transparency.
- Reduced previews and final images use the same validated settings but different sampling resolutions. Filtering, mask resizing and crop rounding can differ at edges. Final rendering never exports the cached thumbnail or selection overlay.
- The current 40-million-pixel/8-bit image limits remain. There is no fixed total RAM guarantee. Input copies, temporary PNG encoding/decoding and thumbnail previews are currently synchronous. Full-resolution effects run in a separate thread, with cancellation checks between processing stages/tiles; a native filtering call may finish before cancellation takes effect.
- The inference process has a 180-second UI timeout. Cancelling stops it and cleanup waits for process exit. A forced application/system crash can leave temporary local job files. Cleanup failures are shown rather than silently treated as success.

There is still no instruction-based generation, generative object removal, neural super-resolution or stronger optional model in this extension.

## Architecture and protocol

`ai/background.py::predict_subject` separates raw saliency inference from alpha compositing. Existing `remove_background` still calls the same model and `apply_mask`, preserving its public behavior. ONNX Runtime is imported inside inference only, after pinned model-byte verification. It is not initialized by core or GUI imports.

The existing `--worker <private-job-directory>` entry point accepts an additional exact request: `{"version":1,"operation":"select_subject"}`. Version booleans, unknown fields and unknown operations are rejected. The worker writes a metadata-free grayscale `mask.png` and an atomic result manifest containing version, operation, dimensions and SHA-256. The original image is not replaced.

`core/selection_io.py` verifies the exit code, bounded JSON/file sizes, exact success fields, SHA-256, PNG/L mode, single-frame content and matching dimensions. It rejects symlinks and masks carrying metadata. Checksums detect mismatches/corruption; they are not authentication against another process running as the same OS user.

`core/subject.py` owns immutable settings, validated mask geometry and image effects, independently of Qt and inference. Tiled blur includes a filtering halo so tile boundaries do not introduce artificial seams. Hidden RGB pixels stay unchanged for color-only effects. The UI adapter suppresses subprocess diagnostic streams and surfaces only known public error categories.

`ui/subject_job.py` owns QProcess startup, timeout, cancellation and post-exit cleanup. `ui/subject_dialog.py` owns the cached mask, preview-only overlay, task controls and a cancellable full-resolution rendering thread. `ui/guided_window.py` checks document identity and revision before accepting a result, so an obsolete dialog cannot overwrite a replacement document. Parent windows are not destroyed while a child process/thread is active.

The existing `.laip` snapshot format stores the accepted result and Undo/Redo images without a schema change. This does **not** persist editable effect settings or raw AI selections for future re-editing. Undo before revising a previously accepted operation to avoid stacking corrections.

## Verification

The normal source suite includes deterministic tests for every effect, alpha/source preservation, crop bounds, foreground-color leakage, tile boundaries, cancellation, checksum/format validation, worker request rejection and error categories. Qt tests exercise preview/apply/cancel, stale-document guards, history, mask reuse, full-resolution rendering, process startup failure, timeout and cleanup. Fixture/mock tests are explicitly not model-quality evidence.

`tools/verify_subject_tools.py` uses synthetic pixels and the actual bundled model. On native Windows it exercises real source GUI inference, captures every effect and selection overlay in DE/EN, and verifies an accepted full-size dialog render. The Windows build workflow additionally runs the new selection operation inside the compiled executable from a temporary working directory with `PYTHONPATH` removed. The surrounding image-effect assertions still execute in the source harness; this is not exhaustive interaction coverage of every new control inside the compiled GUI.

Commands, with the existing project dependencies and prepared model:

```text
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests tools
PYTHONPATH=src python tools/verify_subject_tools.py test-results/subject-source
PYTHONPATH=src python tools/verify_subject_tools.py test-results/subject-packaged --executable <application-path>
```

Use the native `windows` Qt platform for Windows captures and `offscreen` for headless Linux checks. Existing source/packaged background-removal, GUI, export and project smoke tests remain in the build workflow. Exact completed run IDs/results belong to the implementation PR; no success is assumed merely because tests or workflows exist. A clean Windows 11 offline acceptance test and broad image-quality/usability evaluation remain separate gates.

## Primary references

- [U-2-Net paper: salient object detection](https://arxiv.org/abs/2005.09007)
- [Qt QProcess lifecycle and process termination](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html)
- [Pillow premultiplied alpha modes](https://pillow.readthedocs.io/en/stable/handbook/concepts.html)
- [Pillow GaussianBlur semantics](https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html)
