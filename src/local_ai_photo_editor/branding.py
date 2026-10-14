"""Public Edivora identity while keeping the established Python module stable.

The existing 'local_ai_photo_editor' import path and '.laip' project identifier
are deliberately preserved so older projects and integrations remain readable.
"""
from __future__ import annotations

from pathlib import Path

APP_NAME = "Edivora"
PHOTO_EDITOR_TITLE = APP_NAME  # Initial title; localized by the UI on startup.
BRAND_TAGLINE_DE = "Einfach kreativ. Alles lokal."
BRAND_TAGLINE_EN = "Create simply. Stay local."


def mark_path() -> Path:
    """Return the bundled, self-contained SVG asset (no network or fonts)."""
    return Path(__file__).resolve().parent / "assets" / "edivora-mark.svg"


def app_icon():
    """Render the Edivora vector mark using Qt itself; no external SVG service.

    Must run after QApplication exists so QPixmap is available.
    """
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(mark_path().read_bytes()))
    if not renderer.isValid():
        raise RuntimeError("The bundled Edivora icon is not a valid SVG.")
    icon = QIcon()
    for size in (32, 64, 128, 256):
        image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        try:
            renderer.render(painter)
        finally:
            painter.end()
        icon.addPixmap(QPixmap.fromImage(image))
    return icon
