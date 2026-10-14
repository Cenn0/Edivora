"""Preview navigation that preserves normalized crop and brush coordinates."""
from __future__ import annotations

import math
from numbers import Real

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .canvas import PhotoCanvas
from .detail_strings import text


class NavigationCanvas(PhotoCanvas):
    zoom_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        self._zoom = 1.0
        self._center = QPointF(.5, .5)
        self._space = False
        self._hand = False
        self._pan_position: QPointF | None = None
        super().__init__(parent)

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    @property
    def image_rect(self) -> QRectF:
        fitted = super().image_rect
        if fitted.isEmpty():
            return fitted
        width, height = fitted.width() * self._zoom, fitted.height() * self._zoom
        return QRectF(self.width() / 2 - self._center.x() * width,
                      self.height() / 2 - self._center.y() * height, width, height)

    def _bound_center(self) -> None:
        fitted = super().image_rect
        if fitted.isEmpty():
            return
        x = min(.5, max(1, self.width() - 56) / (2 * fitted.width() * self._zoom))
        y = min(.5, max(1, self.height() - 56) / (2 * fitted.height() * self._zoom))
        self._center = QPointF(min(1 - x, max(x, self._center.x())),
                              min(1 - y, max(y, self._center.y())))

    def set_language(self, language: str) -> None:
        super().set_language(language)
        self.setToolTip(text(language, "navigation_hint"))

    def set_image(self, image: Image.Image, full_size: tuple[int, int]) -> None:
        changed_size = (self._full_size.width(), self._full_size.height()) != full_size
        super().set_image(image, full_size)
        if changed_size:
            self._zoom, self._center = 1.0, QPointF(.5, .5)
            self.zoom_changed.emit(self._zoom)
        self._bound_center()

    def _drawing(self) -> bool:
        return self._brush_points is not None or self._anchor is not None

    def set_zoom(self, factor: float, anchor: QPointF | None = None) -> None:
        if isinstance(factor, bool) or not isinstance(factor, Real) or not math.isfinite(factor):
            raise ValueError("Zoom must be a finite number.")
        if self._image.isNull() or self._drawing() or self._pan_position is not None:
            return
        anchor = anchor or QPointF(self.width() / 2, self.height() / 2)
        point = self._normalized_point(anchor)
        self._zoom = min(8.0, max(1.0, float(factor)))
        fitted = super().image_rect
        self._center = QPointF(
            point.x() - (anchor.x() - self.width() / 2) / (fitted.width() * self._zoom),
            point.y() - (anchor.y() - self.height() / 2) / (fitted.height() * self._zoom),
        )
        self._bound_center()
        self.zoom_changed.emit(self._zoom)
        self.update()

    def fit_view(self) -> None:
        self.set_zoom(1.0)

    def pan_by(self, delta: QPointF) -> None:
        if self._image.isNull() or self._drawing():
            return
        rect = self.image_rect
        self._center -= QPointF(delta.x() / rect.width(), delta.y() / rect.height())
        self._bound_center()
        self.update()

    def set_hand_mode(self, enabled: bool) -> None:
        if not self._drawing():
            self._hand = enabled
            self._update_cursor()

    def _update_cursor(self) -> None:
        cursor = (Qt.CursorShape.ClosedHandCursor if self._pan_position is not None
                  else Qt.CursorShape.OpenHandCursor if self._space or self._hand
                  else Qt.CursorShape.CrossCursor if self._brush_enabled or self._crop_enabled
                  else Qt.CursorShape.ArrowCursor)
        self.setCursor(cursor)

    def set_brush_enabled(self, enabled: bool) -> None:
        if enabled != self._brush_enabled:
            super().set_brush_enabled(enabled)
        self._update_cursor()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._image.isNull():
            event.ignore()
            return
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta:
            steps = min(4, max(-4, delta / 120))
            self.set_zoom(self._zoom * 1.25 ** steps, event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        wants_pan = event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and (self._space or self._hand))
        if wants_pan and not self._drawing() and self.image_rect.contains(event.position()):
            self._pan_position = event.position()
            self._update_cursor()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_position is not None:
            self.pan_by(event.position() - self._pan_position)
            self._pan_position = event.position()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pan_position is not None and event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._pan_position = None
            self._update_cursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Space and not self._drawing():
            self._space = True
            self._update_cursor()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.set_zoom(self._zoom * 1.25)
        elif key == Qt.Key.Key_Minus:
            self.set_zoom(self._zoom / 1.25)
        elif key in (Qt.Key.Key_Home, Qt.Key.Key_0):
            self.fit_view()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            delta = {Qt.Key.Key_Left: QPointF(40, 0), Qt.Key.Key_Right: QPointF(-40, 0),
                     Qt.Key.Key_Up: QPointF(0, 40), Qt.Key.Key_Down: QPointF(0, -40)}[key]
            self.pan_by(delta)
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space = False
            self._update_cursor()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event) -> None:
        self._space = False
        self._pan_position = None
        self._brush_points = None
        self._anchor = None
        self._update_cursor()
        super().focusOutEvent(event)

    def resizeEvent(self, event) -> None:
        self._brush_points = None
        self._anchor = None
        self._pan_position = None
        self._bound_center()
        super().resizeEvent(event)


class ViewControls(QWidget):
    def __init__(self, canvas: NavigationCanvas, language: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas, self.language = canvas, language
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.out_button = QPushButton("−")
        self.in_button = QPushButton("+")
        self.fit_button = QPushButton(text(language, "zoom_fit"))
        self.pan_button = QPushButton(text(language, "pan"))
        self.pan_button.setCheckable(True)
        self.value = QLabel()
        for widget in (self.out_button, self.in_button, self.value, self.fit_button, self.pan_button):
            row.addWidget(widget)
        for button, key in ((self.out_button, "zoom_out"), (self.in_button, "zoom_in")):
            button.setAccessibleName(text(language, key))
            button.setToolTip(text(language, key))
            button.setMaximumWidth(44)
        self.setToolTip(text(language, "navigation_hint"))
        self.out_button.clicked.connect(lambda: canvas.set_zoom(canvas.zoom_factor / 1.25))
        self.in_button.clicked.connect(lambda: canvas.set_zoom(canvas.zoom_factor * 1.25))
        self.fit_button.clicked.connect(canvas.fit_view)
        self.pan_button.toggled.connect(canvas.set_hand_mode)
        canvas.zoom_changed.connect(self._update_value)
        self._update_value(canvas.zoom_factor)

    def _update_value(self, factor: float) -> None:
        self.value.setText(text(self.language, "zoom_value", factor=factor))
        self.out_button.setEnabled(factor > 1)
        self.in_button.setEnabled(factor < 8)
