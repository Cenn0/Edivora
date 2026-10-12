"""A fitted photo preview with transparency and pixel-aligned crop selection."""

from __future__ import annotations

import math

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from .strings import translate


class PhotoCanvas(QWidget):
    selection_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image = QImage()
        self._full_size = QSize()
        self._language = "de"
        self._crop_enabled = False
        self._anchor: QPointF | None = None
        self._selection: QRectF | None = None
        self._checker = QPixmap(24, 24)
        self._checker.fill(QColor("#343841"))
        painter = QPainter(self._checker)
        painter.fillRect(0, 0, 12, 12, QColor("#424752"))
        painter.fillRect(12, 12, 12, 12, QColor("#424752"))
        painter.end()
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.set_language("de")

    def set_language(self, language: str) -> None:
        self._language = language
        self.setAccessibleName(translate(language, "canvas_accessible"))
        self.update()

    def set_image(self, image: Image.Image, full_size: tuple[int, int]) -> None:
        rgba = image.convert("RGBA")
        # QImage must own its storage after this temporary bytes object leaves.
        self._image = QImage(
            rgba.tobytes(), rgba.width, rgba.height, rgba.width * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
        self._full_size = QSize(*full_size)
        self.clear_selection()
        self.update()

    @property
    def image_rect(self) -> QRectF:
        if self._image.isNull():
            return QRectF()
        available = self.rect().adjusted(28, 28, -28, -28)
        scale = min(
            max(1, available.width()) / self._image.width(),
            max(1, available.height()) / self._image.height(),
        )
        width, height = self._image.width() * scale, self._image.height() * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    @property
    def crop_box(self) -> tuple[int, int, int, int] | None:
        if self._selection is None:
            return None
        rect = self._selection.normalized()
        left = max(0, math.floor(rect.left() * self._full_size.width()))
        top = max(0, math.floor(rect.top() * self._full_size.height()))
        right = min(self._full_size.width(), math.ceil(rect.right() * self._full_size.width()))
        bottom = min(self._full_size.height(), math.ceil(rect.bottom() * self._full_size.height()))
        return (left, top, right, bottom) if left < right and top < bottom else None

    def set_crop_enabled(self, enabled: bool) -> None:
        self._crop_enabled = enabled
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)
        if not enabled:
            self.clear_selection()

    def clear_selection(self) -> None:
        self._anchor = None
        self._selection = None
        self.selection_changed.emit(None)
        self.update()

    def _normalized_point(self, point: QPointF) -> QPointF:
        rect = self.image_rect
        return QPointF(
            min(1.0, max(0.0, (point.x() - rect.left()) / rect.width())),
            min(1.0, max(0.0, (point.y() - rect.top()) / rect.height())),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._crop_enabled and event.button() == Qt.MouseButton.LeftButton and self.image_rect.contains(event.position()):
            self._anchor = self._normalized_point(event.position())
            self._selection = None
            self.selection_changed.emit(None)
            event.accept()
            self.update()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._selection = QRectF(self._anchor, self._normalized_point(event.position())).normalized()
            self.selection_changed.emit(self.crop_box)
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._anchor is not None and event.button() == Qt.MouseButton.LeftButton:
            self._selection = QRectF(self._anchor, self._normalized_point(event.position())).normalized()
            self._anchor = None
            if self._selection.width() * self.image_rect.width() < 3 or self._selection.height() * self.image_rect.height() < 3:
                self._selection = None
            self.selection_changed.emit(self.crop_box)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#15181e"))
        if self._image.isNull():
            self._paint_empty(painter)
            return
        rect = self.image_rect
        painter.drawTiledPixmap(rect, self._checker)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(rect, self._image)
        painter.setPen(QPen(QColor("#535966"), 1))
        painter.drawRect(rect)
        if self._selection is not None:
            selection = QRectF(
                rect.left() + self._selection.left() * rect.width(),
                rect.top() + self._selection.top() * rect.height(),
                self._selection.width() * rect.width(),
                self._selection.height() * rect.height(),
            )
            outside = QPainterPath()
            outside.setFillRule(Qt.FillRule.OddEvenFill)
            outside.addRect(rect)
            outside.addRect(selection)
            painter.fillPath(outside, QColor(0, 0, 0, 135))
            painter.setPen(QPen(QColor("#d8cdff"), 2))
            painter.drawRect(selection)
            painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
            for part in (1 / 3, 2 / 3):
                x = selection.left() + selection.width() * part
                y = selection.top() + selection.height() * part
                painter.drawLine(QPointF(x, selection.top()), QPointF(x, selection.bottom()))
                painter.drawLine(QPointF(selection.left(), y), QPointF(selection.right(), y))

    def _paint_empty(self, painter: QPainter) -> None:
        center = QPointF(self.width() / 2, self.height() / 2 - 70)
        icon = QRectF(center.x() - 42, center.y() - 32, 84, 64)
        painter.setPen(QPen(QColor("#858096"), 2))
        painter.drawRoundedRect(icon, 10, 10)
        painter.drawEllipse(QPointF(icon.left() + 22, icon.top() + 20), 5, 5)
        mountain = QPainterPath(QPointF(icon.left() + 10, icon.bottom() - 12))
        mountain.lineTo(icon.left() + 30, icon.top() + 33)
        mountain.lineTo(icon.left() + 43, icon.top() + 44)
        mountain.lineTo(icon.left() + 57, icon.top() + 27)
        mountain.lineTo(icon.right() - 10, icon.bottom() - 12)
        painter.drawPath(mountain)
        font = painter.font()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#e6e7ec"))
        painter.drawText(QRectF(16, center.y() + 52, self.width() - 32, 36), Qt.AlignmentFlag.AlignCenter, translate(self._language, "empty_title"))
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#a6a9b5"))
        painter.drawText(QRectF(16, center.y() + 92, self.width() - 32, 28), Qt.AlignmentFlag.AlignCenter, translate(self._language, "empty_hint"))
        painter.setPen(QColor("#777e90"))
        painter.drawText(QRectF(16, center.y() + 126, self.width() - 32, 28), Qt.AlignmentFlag.AlignCenter, translate(self._language, "empty_formats"))
