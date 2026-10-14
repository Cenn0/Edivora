"""Edivora's single-entry selection screen for 1–3 independent editor processes."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from ..branding import app_icon
from .media_strings import text
from .theme import stylesheet


TOOLS = ("photo", "video", "audio")
SYMBOLS = {"photo": "▣", "video": "▶", "audio": "♫"}


class LauncherWindow(QMainWindow):
    def __init__(self, launch_tool: Callable[[str], bool]) -> None:
        super().__init__()
        self.language = "de"
        self._launch_tool = launch_tool
        self._translated: list[tuple[object, str]] = []
        self.choices: dict[str, QCheckBox] = {}
        self.quick_buttons: dict[str, QPushButton] = {}
        self.setWindowTitle("Edivora")
        self.setMinimumSize(780, 510)
        self.resize(1020, 690)
        self.setStyleSheet(stylesheet())
        self._build()
        self._translate()

    def _t(self, key: str) -> str:
        return text(self.language, key)

    def _label(self, key: str, style: str = "", wrap: bool = False) -> QLabel:
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(wrap)
        if style:
            label.setObjectName(style)
        self._translated.append((label, key))
        return label

    def _button(self, key: str, callback: Callable, style: str = "") -> QPushButton:
        button = QPushButton()
        if style:
            button.setObjectName(style)
        button.clicked.connect(callback)
        self._translated.append((button, key))
        return button

    def _build(self) -> None:
        center = QWidget(self)
        center.setObjectName("startPage")
        self.setCentralWidget(center)
        root = QVBoxLayout(center)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(22)

        header = QHBoxLayout()
        brand_symbol = QLabel()
        brand_symbol.setPixmap(app_icon().pixmap(40, 40))
        brand_symbol.setAccessibleName("Edivora")
        brand_symbol.setObjectName("brandMark")
        header.addWidget(brand_symbol)
        header.addWidget(self._label("suite", "appName"))
        header.addStretch()
        header.addWidget(self._label("local", "localBadge"))
        language = QComboBox()
        language.addItem("Deutsch", "de")
        language.addItem("English", "en")
        language.currentIndexChanged.connect(self._switch_language)
        header.addWidget(language)
        self.language_combo = language
        root.addLayout(header)

        root.addSpacing(14)
        root.addWidget(self._label("launcher_title", "homeTitle"))
        root.addWidget(self._label("launcher_intro", "startHint", wrap=True))

        cards = QHBoxLayout()
        cards.setSpacing(14)
        for tool in TOOLS:
            panel = QFrame()
            panel.setObjectName("startCard")
            panel.setMinimumWidth(195)
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(17, 20, 17, 18)
            layout.setSpacing(15)
            icon = QLabel(SYMBOLS[tool])
            icon.setObjectName("brandMark")
            icon.setAccessibleName(tool)
            layout.addWidget(icon)
            layout.addWidget(self._label(tool, "sectionTitle"))
            hint = self._label(f"{tool}_hint", "muted", wrap=True)
            hint.setAlignment(Qt.AlignmentFlag.AlignTop)
            layout.addWidget(hint, 1)

            choose = QCheckBox()
            choose.setAccessibleName(tool)
            choose.toggled.connect(self._update_start_button)
            self.choices[tool] = choose
            self._translated.append((choose, "select_tool"))
            layout.addWidget(choose)

            quick = self._button("open_tool", lambda _=False, t=tool: self._open(t))
            self.quick_buttons[tool] = quick
            layout.addWidget(quick)
            cards.addWidget(panel, 1)
        root.addLayout(cards, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.open_selected = self._button("start_selected", self._open_selected, "primary")
        self.open_selected.setMinimumWidth(280)
        self.open_selected.setEnabled(False)
        buttons.addWidget(self.open_selected)
        root.addLayout(buttons)
        foot = self._label("launcher_footer", "muted")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(foot)

    def _switch_language(self) -> None:
        self.language = str(self.language_combo.currentData() or "de")
        self._translate()

    def _translate(self) -> None:
        for widget, key in self._translated:
            widget.setText(self._t(key))

    def _update_start_button(self, *_args: object) -> None:
        if hasattr(self, "open_selected"):
            self.open_selected.setEnabled(any(box.isChecked() for box in self.choices.values()))

    def _open(self, tool: str) -> None:
        if not self._launch_tool(tool):
            QMessageBox.warning(self, self._t("error"), self._t("launcher_failure"))

    def _open_selected(self) -> None:
        selected = [tool for tool in TOOLS if self.choices[tool].isChecked()]
        if not selected:
            QMessageBox.information(self, self._t("suite"), self._t("launcher_empty"))
            return
        failed = [tool for tool in selected if not self._launch_tool(tool)]
        if failed:
            QMessageBox.warning(
                self, self._t("error"),
                self._t("launcher_failure") + " " + ", ".join(self._t(t) for t in failed),
            )
