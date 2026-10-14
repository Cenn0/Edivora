"""Render the branded icon from the committed SVG for Windows builds.

Requires the already-pinned PySide6 and Pillow dependencies, not a download or
an additional image conversion executable.
"""
from __future__ import annotations

from pathlib import Path


def build_windows_icon(source: Path, destination: Path) -> Path:
    from PIL import Image
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(source.read_bytes()))
    if not renderer.isValid():
        raise ValueError(f"Invalid Edivora logo: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    image = QImage(512, 512, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    png = destination / "Edivora-icon.png"
    if not image.save(str(png), "PNG"):
        raise OSError(f"Unable to write {png}")
    ico = destination / "Edivora.ico"
    with Image.open(png) as original:
        original.convert("RGBA").save(
            ico, format="ICO", sizes=[(16, 16), (24, 24), (32, 32),
                                      (48, 48), (64, 64), (128, 128), (256, 256)]
        )
    if not ico.is_file() or ico.stat().st_size == 0:
        raise OSError("Windows icon generation failed.")
    return ico
