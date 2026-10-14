"""Persistent Edivora hub: direct starts, no selection or bulk-start mode."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QVBoxLayout, QWidget,
)

from ..branding import app_icon
from .icons import IconButton, icon
from .media_strings import text
from .responsive import fit_initial_window
from .theme import COLORS, stylesheet

TOOLS = ("photo", "video", "audio")


class _ToolCard(QFrame):
    def __init__(self, tool: str, callback: Callable[[], None]):
        super().__init__()
        self.tool = tool
        self.setObjectName("startCard")
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(20, 18, 20, 18)
        self.grid.setSpacing(12)
        self.mark = QLabel()
        self.mark.setPixmap(icon(tool, COLORS["primary"]).pixmap(QSize(36, 36)))
        self.mark.setAccessibleName("")  # decorative; the adjacent title names the tool
        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        self.hint = QLabel()
        self.hint.setTextFormat(Qt.TextFormat.PlainText)
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        self.button = IconButton(key="open_tool")
        self.button.clicked.connect(callback)
        self._compact: bool | None = None
        self.set_compact(False)

    def set_compact(self, compact: bool) -> None:
        if self._compact == compact:
            return
        self._compact = compact
        for widget in (self.mark, self.title, self.hint, self.button):
            self.grid.removeWidget(widget)
        for i in range(4):
            self.grid.setRowStretch(i, 0)
            self.grid.setColumnStretch(i, 0)
        if compact:
            self.grid.setContentsMargins(14, 10, 14, 10)
            self.grid.addWidget(self.mark, 0, 0, 2, 1)
            self.grid.addWidget(self.title, 0, 1)
            self.grid.addWidget(self.hint, 1, 1)
            self.grid.addWidget(self.button, 0, 2, 2, 1)
            self.grid.setColumnStretch(1, 1)
        else:
            self.grid.setContentsMargins(20, 20, 20, 18)
            self.grid.addWidget(self.mark, 0, 0)
            self.grid.addWidget(self.title, 1, 0)
            self.grid.addWidget(self.hint, 2, 0, alignment=Qt.AlignmentFlag.AlignTop)
            self.grid.addWidget(self.button, 3, 0)
            self.grid.setRowStretch(2, 1)


class LauncherWindow(QMainWindow):
    def __init__(self, launch_tool: Callable[[str], bool]) -> None:
        super().__init__()
        self.language = "de"
        self._launch_tool = launch_tool
        self.quick_buttons: dict[str, IconButton] = {}
        self.cards: dict[str, _ToolCard] = {}
        self._compact: bool | None = None
        self.setWindowTitle("Edivora")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(640, 480)
        self.setStyleSheet(stylesheet())
        self._build()
        self._translate()
        fit_initial_window(self, (1060, 620))

    def _t(self, key: str, **values) -> str:
        return text(self.language, key, **values)

    def _build(self) -> None:
        center = QWidget(self)
        center.setObjectName("startPage")
        self.setCentralWidget(center)
        self.root = QVBoxLayout(center)
        self.root.setContentsMargins(24, 18, 24, 18)
        self.root.setSpacing(14)
        header = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(app_icon().pixmap(36, 36))
        mark.setAccessibleName("Edivora")
        mark.setObjectName("brandMark")
        header.addWidget(mark)
        brand = QLabel("Edivora")
        brand.setObjectName("appName")
        header.addWidget(brand)
        header.addStretch()
        self.local_badge = QLabel()
        self.local_badge.setObjectName("localBadge")
        header.addWidget(self.local_badge)
        self.language_combo = QComboBox()
        self.language_combo.addItem("Deutsch", "de")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self._switch_language)
        header.addWidget(self.language_combo)
        self.root.addLayout(header)
        self.heading = QLabel()
        self.heading.setObjectName("homeTitle")
        self.heading.setWordWrap(True)
        self.root.addWidget(self.heading)
        self.intro = QLabel()
        self.intro.setObjectName("startHint")
        self.intro.setWordWrap(True)
        self.root.addWidget(self.intro)
        self.card_grid = QGridLayout()
        self.card_grid.setSpacing(14)
        self.root.addLayout(self.card_grid, 1)
        for index, tool in enumerate(TOOLS):
            card = _ToolCard(tool, lambda _=False, t=tool: self._open(t))
            self.cards[tool] = card
            self.quick_buttons[tool] = card.button
            self.card_grid.addWidget(card, 0, index)
            QShortcut(QKeySequence(f"Alt+{index + 1}"), self,
                      activated=lambda t=tool: self._open(t))
        self.footer = QLabel()
        self.footer.setObjectName("muted")
        self.footer.setWordWrap(True)
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root.addWidget(self.footer)

    def _switch_language(self) -> None:
        self.language = str(self.language_combo.currentData() or "de")
        self._translate()

    def _translate(self) -> None:
        self.heading.setText(self._t("launcher_title"))
        self.intro.setText(self._t("launcher_intro"))
        self.local_badge.setText(self._t("local"))
        self.footer.setText(self._t("launcher_footer"))
        self.language_combo.setAccessibleName(self._t("language"))
        for index, (tool, card) in enumerate(self.cards.items()):
            card.title.setText(self._t(tool))
            card.hint.setText(self._t(f"{tool}_hint"))
            card.button.setText(self._t("open_tool"))
            label = f'{self._t(tool)} · {self._t("open_tool")} (Alt+{index + 1})'
            card.button.setAccessibleName(label)
            card.button.setToolTip(label)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "card_grid"):
            return
        compact = self.width() < 840
        if compact != self._compact:
            self._compact = compact
            for card in self.cards.values():
                self.card_grid.removeWidget(card)
            for i, card in enumerate(self.cards.values()):
                card.set_compact(compact)
                self.card_grid.addWidget(card, i if compact else 0, 0 if compact else i)
        short = self.height() < 560
        self.root.setSpacing(8 if short else 14)
        self.heading.setStyleSheet("font-size: 24px; font-weight: 700;" if short else "")

    def _open(self, tool: str) -> None:
        if tool not in TOOLS:
            raise ValueError("Unknown editor type.")
        if not self._launch_tool(tool):
            QMessageBox.warning(self, self._t("error"), self._t("launcher_failure"))
        # Deliberately never hide/close: editors are detached independent processes.
