"""Reusable visual in/out range selector for Video and Audio.

This widget owns presentation and pointer/keyboard interaction only. Export
ranges, validation and file operations remain in the controller/core.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..core.media import MIN_SELECTION_MS
from .theme import COLORS


def _time_label(ms: int) -> str:
    seconds = max(0, int(ms)) // 1000
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


class TrimTimeline(QWidget):
    """Single-range timeline with two draggable boundaries and a playhead.

    - Drag a handle to set an exact export boundary (100ms minimum range).
    - Click the bar away from the handles to seek, without changing a cut.
    - Focus a handle and use arrows for 100ms, Shift+arrows for 1s steps.
    - Spin boxes in the parent remain the accessible precise input alternative.
    """

    rangeChanged = Signal(int, int)
    seekRequested = Signal(int)

    TRACK_INSET = 22
    HANDLE_HIT = 16
    TRACK_TOP = 38
    TRACK_HEIGHT = 27

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.duration_ms = 0
        self.start_ms = 0
        self.end_ms = 0
        self.position_ms = 0
        self.active_handle = "start"
        self._dragging = False
        self.setMinimumHeight(94)
        self.setMaximumHeight(120)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEnabled(False)

    def _track_width(self) -> float:
        return float(max(1, self.width() - 2 * self.TRACK_INSET))

    def _x_at(self, milliseconds: int) -> float:
        if self.duration_ms <= 0:
            return float(self.TRACK_INSET)
        ratio = max(0.0, min(1.0, milliseconds / self.duration_ms))
        return self.TRACK_INSET + ratio * self._track_width()

    def _ms_at(self, x: float) -> int:
        if self.duration_ms <= 0:
            return 0
        ratio = max(0.0, min(1.0, (x - self.TRACK_INSET) / self._track_width()))
        return round(ratio * self.duration_ms)

    def set_duration(self, duration_ms: int) -> None:
        """A new file resets to the full range; callers own preservation."""
        self.duration_ms = max(0, int(duration_ms))
        self.start_ms = 0
        self.end_ms = self.duration_ms
        self.position_ms = 0
        self._dragging = False
        self.setEnabled(self.duration_ms >= MIN_SELECTION_MS)
        self.update()

    def set_range(self, start_ms: int, end_ms: int) -> None:
        """Sync accepted numeric control values without an emitted signal."""
        duration = self.duration_ms
        self.start_ms = max(0, min(duration, int(start_ms)))
        self.end_ms = max(0, min(duration, int(end_ms)))
        self.update()

    def set_position(self, position_ms: int) -> None:
        self.position_ms = max(0, min(self.duration_ms, int(position_ms)))
        self.update()

    def _edit_boundary(self, handle: str, proposed_ms: int) -> None:
        if not self.isEnabled() or self.duration_ms < MIN_SELECTION_MS:
            return
        value = max(0, min(self.duration_ms, int(proposed_ms)))
        if handle == "start":
            value = min(value, self.end_ms - MIN_SELECTION_MS)
            new_start, new_end = max(0, value), self.end_ms
        else:
            value = max(value, self.start_ms + MIN_SELECTION_MS)
            new_start, new_end = self.start_ms, min(self.duration_ms, value)
        if (new_start, new_end) != (self.start_ms, self.end_ms):
            self.start_ms, self.end_ms = new_start, new_end
            self.rangeChanged.emit(new_start, new_end)
            self.seekRequested.emit(new_start if handle == "start" else new_end)
            self.update()

    def _nearest_handle(self, x: float) -> str | None:
        distance_start = abs(x - self._x_at(self.start_ms))
        distance_end = abs(x - self._x_at(self.end_ms))
        distance = min(distance_start, distance_end)
        if distance > self.HANDLE_HIT:
            return None
        return "start" if distance_start <= distance_end else "end"

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (not self.isEnabled() or event.button() != Qt.MouseButton.LeftButton
                or not (self.TRACK_TOP - 12 <= event.position().y()
                        <= self.TRACK_TOP + self.TRACK_HEIGHT + 12)):
            event.ignore()
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        x = event.position().x()
        handle = self._nearest_handle(x)
        if handle is None:
            self.seekRequested.emit(self._ms_at(x))
        else:
            self.active_handle = handle
            self._dragging = True
            self._edit_boundary(handle, self._ms_at(x))
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            event.ignore()
            return
        if self._dragging:
            self._edit_boundary(self.active_handle, self._ms_at(event.position().x()))
        else:
            self.setCursor(
                Qt.CursorShape.SizeHorCursor
                if self._nearest_handle(event.position().x()) is not None
                else Qt.CursorShape.PointingHandCursor
            )
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            # Commit the release coordinate even if the platform skipped
            # the last move event during a fast drag.
            self._edit_boundary(self.active_handle, self._ms_at(event.position().x()))
            self._dragging = False
            self.update()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self.isEnabled():
            super().keyPressEvent(event)
            return
        key = event.key()
        if key not in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            super().keyPressEvent(event)
            return
        step = 1000 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 100
        change = step if key == Qt.Key.Key_Right else -step
        current = self.start_ms if self.active_handle == "start" else self.end_ms
        self._edit_boundary(self.active_handle, current + change)
        event.accept()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            bounds = QRectF(
                self.TRACK_INSET, self.TRACK_TOP,
                self._track_width(), self.TRACK_HEIGHT,
            )
            painter.setPen(QPen(QColor(COLORS["border"]), 1))
            painter.setBrush(QColor(COLORS["elevated"]))
            painter.drawRoundedRect(bounds, 9, 9)

            if self.duration_ms < MIN_SELECTION_MS:
                painter.setPen(QColor(COLORS["muted"]))
                painter.drawText(
                    QRect(0, 0, self.width(), 28),
                    Qt.AlignmentFlag.AlignCenter, "—",
                )
                return

            left = self._x_at(self.start_ms)
            right = self._x_at(self.end_ms)
            if right > left:
                region = QRectF(
                    left, self.TRACK_TOP + 2, right - left, self.TRACK_HEIGHT - 4,
                )
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(COLORS["primary"]).darker(155))
                painter.drawRect(region)

            # Dedicated playhead distinct from the cut markers.
            x = self._x_at(self.position_ms)
            painter.setPen(QPen(QColor(COLORS["selection"]), 2))
            painter.drawLine(
                QPoint(round(x), self.TRACK_TOP - 9),
                QPoint(round(x), self.TRACK_TOP + self.TRACK_HEIGHT + 9),
            )

            for handle, position in (("start", left), ("end", right)):
                painter.setPen(QPen(QColor(COLORS["app"]), 1))
                painter.setBrush(
                    QColor(COLORS["primary"] if handle == self.active_handle else COLORS["secondary"])
                )
                painter.drawRoundedRect(
                    QRectF(position - 5, self.TRACK_TOP - 5, 10, self.TRACK_HEIGHT + 10),
                    3, 3,
                )

            painter.setPen(QColor(COLORS["text"]))
            painter.drawText(
                QRect(self.TRACK_INSET, 1, max(1, self.width() // 2 - self.TRACK_INSET), 25),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                _time_label(self.start_ms),
            )
            painter.drawText(
                QRect(self.width() // 2, 1, max(1, self.width() // 2 - self.TRACK_INSET), 25),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                _time_label(self.end_ms),
            )
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(
                QRect(self.TRACK_INSET, self.TRACK_TOP + self.TRACK_HEIGHT + 11,
                      max(1, self.width() - 2 * self.TRACK_INSET), 18),
                Qt.AlignmentFlag.AlignCenter,
                _time_label(self.duration_ms),
            )
            if self.hasFocus():
                painter.setPen(QPen(QColor(COLORS["selection"]), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(
                    QRectF(2, 1, self.width() - 4, self.height() - 3), 5, 5,
                )
        finally:
            painter.end()
