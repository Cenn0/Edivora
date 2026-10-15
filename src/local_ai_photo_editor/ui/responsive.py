"""Shared layout helpers. Logical pixels are scaled by Qt, never by manual DPI math."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QScrollArea, QSizePolicy, QWidget


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


class WrappedCheckBox(QCheckBox):
    """Native, keyboard-accessible checkbox with an actually wrapping label."""
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._caption = QLabel(self)
        self._caption.setTextFormat(Qt.TextFormat.PlainText)
        self._caption.setWordWrap(True)
        self._caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setText(text)

    def setText(self, text: str) -> None:
        self._caption.setText(text)
        self.setAccessibleName(text)
        self.setToolTip(text)
        self.updateGeometry()

    def text(self) -> str:
        return self._caption.text()

    def heightForWidth(self, width: int) -> int:
        bounds = self._caption.fontMetrics().boundingRect(
            QRect(0, 0, max(1, width - 30), 10000), Qt.TextFlag.TextWordWrap, self.text())
        return max(24, bounds.height() + 6)

    def sizeHint(self) -> QSize:
        return QSize(260, self.heightForWidth(260))

    def minimumSizeHint(self) -> QSize:
        return QSize(60, 24)

    def hitButton(self, position: QPoint) -> bool:
        return self.rect().contains(position)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._caption.setGeometry(30, 0, max(0, self.width() - 30), self.height())


class VerticalScrollArea(QScrollArea):
    """Keep content in the actual viewport when a native scrollbar consumes width.

    Word-wrapping pages can acquire a wider minimum size before a vertical bar
    appears. A vertical-only inspector must reflow at the viewport's new width,
    not keep that stale size and hide its right edge behind a disabled bar.
    """
    def __init__(self, parent=None) -> None:
        self._fitting_width = False
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def setWidget(self, widget: QWidget) -> None:
        super().setWidget(widget)
        self._fit_content_width()

    def viewportEvent(self, event) -> bool:
        result = super().viewportEvent(event)
        if event.type() == QEvent.Type.Resize:
            self._fit_content_width()
        return result

    def _fit_content_width(self) -> None:
        widget = self.widget()
        width = self.viewport().width()
        if widget is None or self._fitting_width or width < 1:
            return
        self._fitting_width = True
        try:
            # This tracks the live viewport; it is not a hard-coded panel width.
            if widget.minimumWidth() != width or widget.maximumWidth() != width:
                widget.setFixedWidth(width)
        finally:
            self._fitting_width = False
