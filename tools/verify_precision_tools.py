"""Exercise the opt-in source editor with the real bundled model and synthetic pixels.

Prepare the checksum-pinned model with tools/prepare_model.py before running.
No private photos or font files are read or uploaded by this verification tool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import time

from PIL import Image
import PIL
import PySide6
from PySide6.QtGui import QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from local_ai_photo_editor.__main__ import _synthetic_photo
from local_ai_photo_editor.ai.models import MODEL_SHA256
from local_ai_photo_editor.core.local_adjustments import LOCAL_MODES, render_local
from local_ai_photo_editor.core.mask import MaskStroke
from local_ai_photo_editor.core.selection import render_selection
from local_ai_photo_editor.ui.precision_dialog import PrecisionDialog
from local_ai_photo_editor.ui.precision_window import EditorWindow


def wait_for(predicate, timeout=190):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    if not predicate():
        raise RuntimeError("Precision source verification timed out")


def capture(widget, destination):
    metrics = QFontMetrics(widget.font())
    if not all(metrics.inFontUcs4(ord(letter)) for letter in "ABCabc09ÄÖÜäöüß"):
        raise RuntimeError("Native UI font cannot display required text")
    if not widget.grab().save(str(destination)):
        raise RuntimeError("Could not save verification screenshot")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    window = EditorWindow()
    image = _synthetic_photo()
    screenshots = []
    report = {"status": "error", "scope": "opt_in_source_runtime_not_quality"}
    try:
        for language in ("de", "en"):
            window.set_language(language)
            window.set_document(image)
            window.show()
            QTest.qWait(30)
            name = f"precision-editor-{language}.png"
            capture(window, args.output / name)
            screenshots.append(name)
            dialog = PrecisionDialog(image, language, "warm", window)
            try:
                dialog.show()
                wait_for(lambda: dialog._mask is not None or bool(dialog._error_code))
                if dialog._mask is None:
                    raise RuntimeError(f"Real subject selection failed: {dialog._error_code}")
                if dialog.job.is_running:
                    raise RuntimeError("Inference did not release its child process")
                mask_before = dialog._mask.tobytes()
                dialog.push_selection(MaskStroke(((.5, .5),), "erase", .06, .4))
                dialog.undo_selection()
                dialog.redo_selection()
                if dialog._mask.tobytes() != mask_before:
                    raise RuntimeError("Brush correction mutated the inferred mask")
                for mode in LOCAL_MODES:
                    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(mode))
                    dialog._render_preview()
                    if not dialog._preview_valid:
                        raise RuntimeError(f"Effect preview failed: {mode}")
                    QTest.qWait(10)
                    name = f"precision-{mode}-{language}.png"
                    capture(dialog, args.output / name)
                    screenshots.append(name)
                dialog.brush_button.click()
                dialog.canvas.set_zoom(2)
                QTest.qWait(20)
                name = f"precision-selection-{language}.png"
                capture(dialog, args.output / name)
                screenshots.append(name)
                dialog.brush_button.click()
                dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("warm"))
                expected = render_local(image, render_selection(dialog._mask, dialog.selection_history.actions), dialog.edit)
                dialog.accept()
                wait_for(lambda: not dialog.is_busy)
                if dialog.result_image is None or dialog.result_image.tobytes() != expected.tobytes():
                    raise RuntimeError("Full-size corrected selection was not applied")
                dialog.result_image.save(args.output / f"precision-output-{language}.png")
            finally:
                dialog.reject()
                wait_for(lambda: not dialog.is_busy)
                dialog.deleteLater()
                app.processEvents()
            manual = PrecisionDialog(image, language, "cool", window, manual=True)
            try:
                manual.show()
                QTest.qWait(20)
                if manual.job.is_running or manual._start_timer.isActive():
                    raise RuntimeError("Manual editing incorrectly started inference")
                manual.push_selection(MaskStroke(((.3, .4), (.5, .6)), "restore", .12, .35))
                name = f"precision-manual-{language}.png"
                capture(manual, args.output / name)
                screenshots.append(name)
                manual.brush_button.click()
                manual.accept()
                wait_for(lambda: not manual.is_busy)
                if manual.result_image is None:
                    raise RuntimeError("Manual selection could not be applied")
            finally:
                manual.reject()
                wait_for(lambda: not manual.is_busy)
                manual.deleteLater()
                app.processEvents()
        report.update(status="passed", python=platform.python_version(), platform=platform.platform(),
                      pyside=PySide6.__version__, pillow=PIL.__version__, qt_platform=app.platformName(),
                      model_sha256=MODEL_SHA256, modes=list(LOCAL_MODES),
                      real_inference_corrected_full_size_apply=True, manual_without_inference=True,
                      screenshots=screenshots,
                      limits="Source opt-in composition only; no new default integration, packaged precision UI, or quality benchmark.")
        code = 0
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
        code = 1
    finally:
        window._close_approved = True
        window.close()
        window.deleteLater()
        app.processEvents()
    (args.output / "precision-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
