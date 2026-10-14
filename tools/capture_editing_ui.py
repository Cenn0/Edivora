"""Capture actual Qt widgets with a synthetic fixture, never a private photo.

Run with PYTHONPATH=src. Linux CI uses QT_QPA_PLATFORM=offscreen; Windows
captures use the native windows platform because its offscreen plugin did not
provide usable fonts on the tested runner. Glyph availability is checked before
captures are accepted. This is a source-UI smoke check, not a packaged app or
segmentation-quality benchmark.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform

import numpy as np
from PIL import Image, ImageDraw
import PIL
import PySide6
from PySide6.QtCore import qVersion
from PySide6.QtGui import QFontInfo, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from local_ai_photo_editor.core.recipes import EditRecipe
from local_ai_photo_editor.ui import EditorWindow
from local_ai_photo_editor.ui.editing_dialog import EditingDialog


def check_text_font(widget: QWidget) -> str:
    """Do not silently report a screenshot full of missing-glyph boxes as valid."""
    metrics = QFontMetrics(widget.font())
    missing = [letter for letter in "AZaz09ÄÖÜäöüß" if not metrics.inFontUcs4(ord(letter))]
    if missing:
        raise RuntimeError(f"The capture font cannot render these letters: {missing}")
    return QFontInfo(widget.font()).family()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    width, height = 900, 650
    y, x = np.ogrid[:height, :width]
    pixels = np.empty((height, width, 3), dtype=np.uint8)
    pixels[..., 0] = 105 + x * 85 // width
    pixels[..., 1] = 145 + y * 65 // height
    pixels[..., 2] = 190 + x * 35 // width
    backdrop = Image.fromarray(pixels)
    subject = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(subject)
    draw.rounded_rectangle((260, 210, 640, 580), radius=55, fill=(180, 102, 68, 255))
    draw.ellipse((320, 80, 580, 340), fill=(62, 128, 78, 255))
    draw.ellipse((255, 135, 485, 365), fill=(79, 147, 85, 255))
    draw.ellipse((415, 135, 645, 365), fill=(86, 154, 98, 255))
    draw.rounded_rectangle((290, 400, 610, 480), radius=15, fill=(227, 200, 163, 255))
    scenes = {
        "light": EditRecipe(automatic=60, shadows=15, highlights=10),
        "look": EditRecipe(look="warm", look_strength=65, vignette=15),
        "shape": EditRecipe(aspect="4:5", focus_x=50),
        "background": EditRecipe(background="photo", background_blur=65),
    }
    files, fonts = [], set()
    window = EditorWindow()
    try:
        for language in ("de", "en"):
            window.set_language(language)
            window.set_document(subject)
            window.resize(1180, 820)
            window.show()
            QTest.qWait(60)
            fonts.add(check_text_font(window.open_button))
            main_path = args.output / f"editor-{language}.png"
            if not window.grab().save(str(main_path)):
                raise RuntimeError("Could not save the editor screenshot")
            files.append(main_path.name)
            # Capture the default calm layout and the optional advanced tools.
            window.more_tools_button.click()
            QTest.qWait(60)
            if window.more_tools_panel.isHidden():
                raise RuntimeError("Expanded precision controls are hidden")
            advanced_path = args.output / f"editor-advanced-{language}.png"
            if not window.grab().save(str(advanced_path)):
                raise RuntimeError("Could not save the expanded editor screenshot")
            files.append(advanced_path.name)
            window.more_tools_button.click()
            if not window.more_tools_panel.isHidden():
                raise RuntimeError("Advanced controls did not collapse")
            for section, recipe in scenes.items():
                dialog = EditingDialog(subject, language, section, window)
                try:
                    if section == "background":
                        dialog.set_background_image(backdrop)
                    dialog.set_recipe(recipe)
                    dialog._render_preview()
                    if not dialog._preview_valid:
                        raise RuntimeError(f"Preview failed: {language}/{section}")
                    dialog.show()
                    QTest.qWait(60)
                    fonts.add(check_text_font(dialog.apply_button))
                    path = args.output / f"editing-{section}-{language}.png"
                    if not dialog.grab().save(str(path)):
                        raise RuntimeError("Could not save an editing screenshot")
                    files.append(path.name)
                finally:
                    dialog.reject()
                    dialog.deleteLater()
                    app.processEvents()
    finally:
        window._close_approved = True
        window.close()
        window.deleteLater()
        app.processEvents()
    report = {
        "status": "passed", "scope": "source_ui_synthetic_fixture_only",
        "python": platform.python_version(), "os": platform.platform(),
        "pyside": PySide6.__version__, "qt": qVersion(), "pillow": PIL.__version__,
        "qt_platform": app.platformName(), "fonts": sorted(fonts),
        "glyph_check": "ASCII and German letters present", "screenshots": files,
    }
    (args.output / "capture-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
