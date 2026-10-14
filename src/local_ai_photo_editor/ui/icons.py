"""Small original vector icons, rendered at the requested DPI without icon fonts."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton

from .theme import COLORS

# Original 24-unit line drawings. No external assets, icon font, network or theme dependency.
_PATHS = {
    "photo": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m4 17 5-5 4 4 3-3 4 4"/>',
    "video": '<rect x="2" y="5" width="14" height="14" rx="3"/><path d="m16 10 6-4v12l-6-4z"/>',
    "audio": '<path d="M10 17V5l10-2v12M10 9l10-2"/><ellipse cx="7" cy="18" rx="3" ry="3"/><ellipse cx="17" cy="16" rx="3" ry="3"/>',
    "open": '<path d="M3 19V6h7l2 3h9v3M3 19l3-7h16l-3 7z"/>',
    "save": '<path d="M4 3h13l4 4v14H3V3zM7 3v6h9V3M7 21v-8h10v8"/>',
    "export": '<path d="M5 14v7h14v-7M12 16V3m-5 5 5-5 5 5"/>',
    "play": '<path d="m7 3 14 9-14 9z"/>',
    "pause": '<path d="M8 4v16M16 4v16"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "add": '<path d="M12 4v16M4 12h16"/>',
    "remove": '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
    "left": '<path d="m13 5-7 7 7 7M6 12h15"/>',
    "right": '<path d="m11 5 7 7-7 7M3 12h15"/>',
    "duplicate": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 5V3H3v13h2"/>',
    "split": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="m8 8 13 13M8 16 21 3"/>',
    "undo": '<path d="m8 3-5 5 5 5M3 8h10a7 7 0 0 1 0 14"/>',
    "redo": '<path d="m16 3 5 5-5 5M21 8h-10a7 7 0 0 0 0 14"/>',
    "compare": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 2v20M5 15l3-4 4 5M15 8h3"/>',
    "reset": '<path d="M4 5v6h6M4 11a8 8 0 1 1 0 5"/>',
    "crop": '<path d="M7 2v15h15M2 7h15v15M4 4l16 16"/>',
    "resize": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M6 13v5h5m7-7V6h-5M6 18 18 6"/>',
    "adjust": '<path d="M4 6h7m6 0h3M4 12h2m6 0h8M4 18h11m5 0h0"/><circle cx="14" cy="6" r="3"/><circle cx="9" cy="12" r="3"/><circle cx="18" cy="18" r="3"/>',
    "spark": '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/>',
    "check": '<path d="m4 12 5 5L20 6"/>',
    "close": '<path d="m5 5 14 14M5 19 19 5"/>',
    "home": '<path d="m2 11 10-9 10 9M5 9v12h14V9M10 21v-7h4v7"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9 8a3 3 0 1 1 4 3c-1 1-1 1-1 3M12 17v1"/>',
    "settings": '<path d="M3 5h18M3 12h18M3 19h18M8 2v6M16 9v6M9 16v6"/>',
    "start": '<path d="M5 3v18m14-16L9 12l10 7z"/>',
    "end": '<path d="M19 3v18M5 5l10 7-10 7z"/>',
    "volume": '<path d="M3 9h4l5-5v16l-5-5H3zM16 8a6 6 0 0 1 0 8M19 5a10 10 0 0 1 0 14"/>',
}

KEY_ICONS = {
    "open": "open", "open_tool": "open", "open_project": "open",
    "save_project": "save", "save_project_as": "save", "export": "export",
    "undo": "undo", "redo": "redo", "original": "compare", "before": "compare",
    "reset": "reset", "reset_all": "reset", "reset_section": "reset",
    "reset_range": "reset", "apply": "check", "cancel": "close", "retry": "reset",
    "rotate_left": "undo", "rotate_right": "redo", "crop": "crop", "resize": "resize",
    "mark_start": "start", "mark_end": "end", "play": "play", "pause": "pause", "stop": "stop",
    "clip_add": "add", "clip_remove": "remove", "clip_up": "left", "clip_down": "right",
    "clip_duplicate": "duplicate", "clip_split": "split",
    "media_project_open": "open", "media_project_save": "save", "media_project_save_as": "save",
    "ai_voice": "spark", "ai_video_frame": "spark", "ai_action": "spark",
    "auto_button": "spark", "nav_start": "home", "nav_photo": "photo", "nav_video": "video",
    "nav_audio": "audio", "nav_help": "help", "nav_settings": "settings",
    "quick_improve": "adjust", "quick_crop": "crop", "quick_blur": "spark", "quick_cutout": "spark",
    "video_improve": "adjust", "restore_video": "spark", "preview_result": "compare",
    "mask_open": "photo", "mask_apply": "check", "mask_cancel_mode": "close",
    "adjust_apply": "check", "adjust_discard": "close", "choose_photo": "photo",
    "choose_color": "adjust", "more_tools": "settings", "less_tools": "settings",
    "quick_more_show": "settings", "quick_more_hide": "settings",
    "subject_blur_open": "spark", "subject_open": "spark",
    "home_open_photo": "photo", "home_open_tool": "open", "home_continue": "right",
}


class _VectorEngine(QIconEngine):
    def __init__(self, name: str, color: str):
        super().__init__()
        self.name, self.color = name, color

    def clone(self):
        return _VectorEngine(self.name, self.color)

    def paint(self, painter: QPainter, rect, mode, state) -> None:
        color = COLORS["muted"] if mode == QIcon.Mode.Disabled else self.color
        data = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
                f'stroke-linejoin="round">{_PATHS[self.name]}</svg>')
        renderer = QSvgRenderer(QByteArray(data.encode("ascii")))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(rect.width(), rect.height())
        renderer.render(painter, QRectF(rect.x() + (rect.width()-side)/2,
                                       rect.y() + (rect.height()-side)/2, side, side))
        painter.restore()

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        pixmap = QPixmap(size)
        from PySide6.QtCore import Qt
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, pixmap.rect(), mode, state)
        painter.end()
        return pixmap


@lru_cache(maxsize=128)
def icon(name: str, color: str | None = None) -> QIcon:
    if name not in _PATHS:
        raise ValueError(f"Unknown built-in icon: {name}")
    return QIcon(_VectorEngine(name, color or COLORS["text"]))


class IconButton(QPushButton):
    """Keep a full accessible label even when a toolbar switches to icon-only."""
    def __init__(self, label: str = "", *, key: str = "", icon_name: str | None = None, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._compact = False
        self._icon_name = icon_name or KEY_ICONS.get(key)
        if self._icon_name:
            self.setIcon(icon(self._icon_name))
        self.setIconSize(QSize(20, 20))
        self.setText(label)

    def setObjectName(self, name: str) -> None:
        super().setObjectName(name)
        if self._icon_name:
            color = COLORS["app"] if name in ("primary", "homePrimary") else COLORS["text"]
            self.setIcon(icon(self._icon_name, color))

    def setText(self, label: str) -> None:
        self._full_text = label
        self.setAccessibleName(label.replace("&", ""))
        self.setToolTip(label.replace("&", ""))
        super().setText("" if self._compact and not self.icon().isNull() else label)

    def setCompact(self, compact: bool) -> None:
        self._compact = compact
        super().setText("" if compact and not self.icon().isNull() else self._full_text)

    @property
    def full_text(self) -> str:
        return self._full_text
