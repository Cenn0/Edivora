"""Verify actual local model inference with synthetic pixels, never private photos.

With --executable, test the new selection protocol inside the compiled worker;
image-effect assertions still run in this source harness. Without that option,
also exercise the real Qt process lifecycle and capture DE/EN source dialogs.
Neither mode is a segmentation-quality benchmark or clean-install acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time

import numpy as np
from PIL import Image

from local_ai_photo_editor.__main__ import _synthetic_photo, worker_command
from local_ai_photo_editor.ai.models import MODEL_SHA256
from local_ai_photo_editor.core import export_image
from local_ai_photo_editor.core.selection_io import read_subject_result
from local_ai_photo_editor.core.subject import SUBJECT_MODES, SubjectEdit, render_subject


def verify_worker(image: Image.Image, executable: Path | None) -> Image.Image:
    with tempfile.TemporaryDirectory(prefix="localai-subject-smoke-") as root:
        directory = Path(root)
        image.save(directory / "input.png", format="PNG")
        (directory / "request.json").write_text('{"version":1,"operation":"select_subject"}', encoding="utf-8")
        if executable is None:
            program, arguments = worker_command(directory)
        else:
            program, arguments = str(executable.resolve(strict=True)), ["--worker", str(directory)]
        env = dict(os.environ)
        if executable is not None:
            env.pop("PYTHONPATH", None)
        process = subprocess.run([program, *arguments], timeout=120, env=env,
                                 cwd=directory if executable is not None else None,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        mask = read_subject_result(directory, image.size, process.returncode)
        if mask.getextrema()[0] == mask.getextrema()[1]:
            raise RuntimeError("Real inference returned no usable selection")
        return mask


def verify_effects(image: Image.Image, mask: Image.Image, output: Path) -> list[dict[str, object]]:
    results = []
    source = image.tobytes()
    selected = np.asarray(mask) == 255
    for mode in SUBJECT_MODES:
        result = render_subject(image, mask, SubjectEdit(mode, strength=75))
        if mode == "cutout":
            if result.mode != "RGBA" or result.convert("RGB").tobytes() != source:
                raise RuntimeError("Cutout altered source color pixels")
        elif mode == "crop":
            if not (0 < result.width <= image.width and 0 < result.height <= image.height):
                raise RuntimeError("Invalid subject crop")
        else:
            if result.size != image.size:
                raise RuntimeError("A color effect changed image dimensions")
            if mode != "light":
                np.testing.assert_array_equal(np.asarray(result)[selected], np.asarray(image)[selected])
        if image.tobytes() != source:
            raise RuntimeError("A subject operation mutated its source")
        export_image(result, output / f"subject-{mode}.png")
        results.append({"mode": mode, "dimensions": list(result.size), "status": "passed"})
    return results


def capture_ui(image: Image.Image, output: Path) -> list[str]:
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from local_ai_photo_editor.ui import EditorWindow
    from local_ai_photo_editor.ui.subject_dialog import SubjectDialog

    app = QApplication.instance() or QApplication([])
    window = EditorWindow()
    captures = []

    def wait_for(predicate, seconds=120):
        deadline = time.monotonic() + seconds
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(20)
        if not predicate():
            raise RuntimeError("Subject GUI lifecycle timed out")

    def capture(widget, filename):
        metrics = QFontMetrics(widget.font())
        if any(not metrics.inFontUcs4(ord(c)) for c in "AZaz09ÄÖÜäöüß"):
            raise RuntimeError("Native UI capture font lacks required glyphs")
        if not widget.grab().save(str(output / filename)):
            raise RuntimeError("UI capture failed")
        captures.append(filename)

    try:
        for language in ("de", "en"):
            window.set_language(language)
            window.set_document(image)
            window.show()
            QTest.qWait(60)
            capture(window, f"ai-editor-{language}.png")
            dialog = SubjectDialog(image, language, "blur", window)
            try:
                dialog.show()
                wait_for(lambda: dialog._mask is not None or bool(dialog._error_code))
                if dialog._mask is None:
                    raise RuntimeError("Real GUI inference failed: " + dialog._error_code)
                for mode in SUBJECT_MODES:
                    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData(mode))
                    dialog._render_preview()
                    if not dialog._preview_valid:
                        raise RuntimeError("Invalid AI effect preview: " + mode)
                    QTest.qWait(40)
                    capture(dialog, f"ai-{mode}-{language}.png")
                dialog.selection_check.setChecked(True)
                QTest.qWait(40)
                capture(dialog, f"ai-selection-{language}.png")
                dialog.selection_check.setChecked(False)
                dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("light"))
                expected = render_subject(image, dialog._mask, dialog.edit)
                dialog.accept()
                wait_for(lambda: not dialog.is_busy)
                if dialog.result_image is None or dialog.result_image.tobytes() != expected.tobytes():
                    raise RuntimeError("Real full-resolution GUI render failed")
                if window.document.current.tobytes() != image.tobytes():
                    raise RuntimeError("Dialog changed document before window acceptance")
            finally:
                dialog.reject()
                wait_for(lambda: not dialog.is_busy, 15)
                dialog.deleteLater()
                app.processEvents()
    finally:
        window._close_approved = True
        window.close()
        window.deleteLater()
        app.processEvents()
    return captures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--executable", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"status": "error", "scope": "synthetic_runtime_not_quality",
              "worker": "packaged" if args.executable else "source",
              "python": platform.python_version(), "platform": platform.platform(),
              "model_sha256": MODEL_SHA256}
    try:
        image = _synthetic_photo().convert("RGB")
        image.save(args.output / "subject-input.png")
        mask = verify_worker(image, args.executable)
        mask.save(args.output / "subject-mask.png")
        report["effects"] = verify_effects(image, mask, args.output)
        if args.executable is None:
            report["source_ui_captures"] = capture_ui(image, args.output)
            report["real_gui_inference_and_apply"] = "passed"
        else:
            report["limits"] = "New compiled selection worker verified; effect and detailed dialog checks run against source."
        report["status"] = "passed"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
    (args.output / "subject-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
