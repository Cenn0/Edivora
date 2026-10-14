"""Shared layout helpers. Logical pixels are scaled by Qt, never by manual DPI math."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class ElideLabel(QLabel):
    """One-line filenames cannot force controls out of the window."""
    def __init__(self, *args, **kwargs):
        self._full_text = ""
        super().__init__(*args, **kwargs)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setTextFormat(Qt.TextFormat.PlainText)

    def setText(self, value: str) -> None:
        self._full_text = value
        self.setToolTip(value)
        self.setAccessibleName(value)
        self._update_text()

    def _update_text(self) -> None:
        super().setText(self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideMiddle, max(30, self.contentsRect().width())))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_text()


def fit_initial_window(window: QWidget, desired: tuple[int, int]) -> None:
    """Respect the available *logical* desktop, including the taskbar and DPI."""
    screen = window.screen()
    if screen is None:
        window.resize(*desired)
        return
    available = screen.availableGeometry()
    window.resize(min(desired[0], max(window.minimumWidth(), available.width() - 40)),
                  min(desired[1], max(window.minimumHeight(), available.height() - 60)))


def in_viewport(widget: QWidget, ancestor: QWidget) -> bool:
    """Used by runtime geometry tests, not a substitute for visual inspection."""
    origin = widget.mapTo(ancestor, QPoint(0, 0))
    from PySide6.QtCore import QRect
    return ancestor.rect().contains(QRect(origin, widget.size()))
