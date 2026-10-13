# Manual foreground mask correction (development source)

Status: implemented after the published v0.1.0-alpha.1 private test release. The released ZIP **does not** include this feature. A new distributable artifact must pass all build/runtime checks and the release gates before being described as tested for Windows 11 users.

## Workflow

1. Open an RGBA image, or open an ordinary photograph and select **Remove background** to get a foreground with transparency.
2. Choose **Refine edges → Refine with brush**. While this tool is open, normal crop, resize, AI and image export actions are disabled.
3. Select **Restore subject** to bring visible pixels back or **Remove background** to make selected areas transparent.
4. Adjust **Brush size** (1–20% of the shorter image dimension) and **Soft edge** (0–100%). Drag on the photo. Painted strokes update a local preview; the full-resolution image does not change yet.
5. **Undo/Redo** affect brush strokes while the tool is active. **Apply correction** commits all strokes as a single reversible document edit. **Discard correction** leaves the document unchanged.
6. Export PNG or lossless WebP to preserve transparency, or save the editable document in a .laip project. JPEG is composited onto white.

The tool is available for any current RGBA document, including an image that already had transparency; it does not require AI inference at edit time. Long drags are decimated to at most 2,048 points and editing sessions are limited to 128 strokes; apply the correction and start another if needed.

## Pixels, preview and quality

The brush adjusts **only 8-bit alpha**. Its restore operation reveals RGB pixels that are already present, instead of synthesizing or hallucinating subject detail. This works particularly well with the bundled U2NETP removal function, which preserves source RGB values even where it predicts transparency. However, images that were already fully transparent may contain arbitrary or premultiplied RGB data; the tool cannot reconstruct lost colors or previously removed visual details.

**Existing source transparency is not tracked separately**: restoring can increase alpha all the way to 255 even if the image had lower alpha before the AI ran. Use the tool deliberately with translucent objects and inspect results. Restoring RGB colors does not decontaminate hair edges whose color was mixed with the background. The feather slider blends alpha; it is not an automatic matting model, relighting tool or AI-based hair restoration.

Mouse strokes are saved as normalized coordinates. The preview applies the strokes to a thumbnail (maximum 1600×1600), while **Apply** rasterizes them on the original image at full resolution. Small differences at edges are possible because of rasterization and resampling. Preview/correction is intentionally not a pixel-perfect zoomed editor in this version. Brushes are rasterized with bounded local patches; acceptance can still take noticeable time and allocate substantial memory for 40-megapixel photographs. We make no minimum-RAM or latency guarantee from unit tests.

While corrections are pending, saving a project and exporting are disabled. The unsaved-change warning also considers pending brush strokes. The accepted result participates in the ordinary bounded Undo/Redo pixel-history and is stored in .laip snapshots. Stroke coordinates and brush settings are not stored separately after acceptance; reopening a project recovers the pixel-perfect accepted result rather than re-executing the brush input.

## Architectural and security boundaries

- Pure Pillow core under core/mask.py; no Qt, ONNX inference, image upload, file extraction, network or model loading.
- The canvas only records pointer strokes and displays a preview. The controller validates and applies accepted strokes at full resolution.
- Every stroke has a mode, diameter, feather fraction and bounded normalized points. Invalid, non-finite, negative or out-of-range values are rejected before processing.
- Source photos remain untouched, and every accepted mask change is reversible within the document history budget.
- This manual tool is **not** an isolation boundary or a substitute for validating potentially malicious image files.

## Verification

Tests should cover pixel and RGB integrity, hard and feathered paint, line interpolation and clipping, validation and bounds, UI undo/redo and cancellation, project reopen and saving, and the compiled Windows application's native GUI smoke check. These checks establish functional operation, not a measured foreground segmentation quality improvement or Windows 11 hardware compatibility.
