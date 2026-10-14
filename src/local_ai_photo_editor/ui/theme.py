"""One Edivora visual language for the photo editor and future workspaces.

Keep palette and component rules here, rather than adding independent
stylesheets to each dialog. Qt Style Sheets do not support CSS variables.
"""
from __future__ import annotations

from string import Template
from types import MappingProxyType

COLORS = MappingProxyType({
    "app": "#171B2D",
    "panel": "#202638",
    "elevated": "#2A3146",
    "border": "#3C465F",
    "text": "#F5F4FF",
    "secondary": "#B9C3D9",
    "muted": "#98A4BC",
    "primary": "#4FF3D3",
    "primary_hover": "#18B9C6",
    "selection": "#7792FF",
    "ai": "#C98CFF",
    "error": "#FF9EA8",
    "stage": "#101522",
})

_QSS = """
QMainWindow, QDialog { background: $app; color: $text; }
QWidget { font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 14px; }
QLabel { color: $text; background: transparent; }
QLabel#appName { font-size: 22px; font-weight: 700; color: $text; }
QLabel#brandMark { color: $primary; font-size: 24px; font-weight: 700; }
QLabel#workspaceName { font-size: 16px; font-weight: 600; color: $text; }
QLabel#muted, QLabel#status, QLabel#startHint, QLabel#homeDescription { color: $secondary; }
QLabel#localBadge {
    color: $primary; background: $elevated; border-radius: 10px; padding: 8px 12px;
}
QLabel#sectionTitle { font-size: 16px; font-weight: 600; }
QLabel#homeTitle { font-size: 24px; font-weight: 700; }
QLabel#fileName { font-size: 14px; font-weight: 600; }
QLabel#sliderValue { color: $selection; font-size: 13px; }
QLabel#saveState { color: $muted; font-size: 12px; }
QLabel#cropHint, QLabel#stepHint {
    color: $text; padding: 10px; background: $elevated;
    border: 1px solid $border; border-radius: 8px;
}
QLabel#aiAccent { color: $ai; font-weight: 600; }
QFrame#topBar {
    background: $panel; border-bottom: 1px solid $border;
}
QFrame#navRail {
    background: $panel; border-right: 1px solid $border;
}
QFrame#toolCard, QFrame#startCard {
    background: $elevated; border: 1px solid $border; border-radius: 12px;
}
QFrame#previewFrame {
    background: $stage; border: 1px solid $border; border-radius: 12px;
}
QFrame#jobBar {
    background: $elevated; border: 1px solid $ai; border-radius: 8px;
}
QFrame#bottomBar {
    background: $panel; border-top: 1px solid $border;
}
QWidget#toolsPanel, QWidget#toolsViewport, QScrollArea#inspectorScroll {
    background: $panel;
}
QWidget#startPage { background: $app; }
QStackedWidget#workspaceStack { background: $app; }
QPushButton {
    color: $text; background: $elevated; border: 1px solid $border;
    border-radius: 8px; padding: 5px 12px; min-height: 34px;
}
QPushButton:hover { background: $border; border-color: $selection; }
QPushButton:pressed, QPushButton:checked {
    background: $border; border-color: $selection;
}
QPushButton:focus { border: 2px solid $selection; padding: 4px 11px; }
QPushButton:disabled { color: $muted; background: $panel; border-color: $border; }
QPushButton#primary, QPushButton#homePrimary {
    background: $primary; color: $app; border: 1px solid $primary;
    font-weight: 700;
}
QPushButton#primary:hover, QPushButton#homePrimary:hover {
    background: $primary_hover; border-color: $primary_hover;
}
QPushButton#primary:disabled, QPushButton#homePrimary:disabled {
    background: $border; color: $muted; border-color: $border;
}
QPushButton#quiet { background: transparent; }
QPushButton#railButton {
    background: transparent; border: 1px solid transparent; border-radius: 10px;
    font-weight: 600; font-size: 12px; padding: 6px 2px; min-height: 58px;
}
QPushButton#railButton:hover { background: $elevated; }
QPushButton#railButton:checked {
    color: $primary; background: $elevated; border: 1px solid $selection;
}
QPushButton#railButton:disabled { color: $muted; }
QPushButton#quickAction, QPushButton#quickAiAction {
    text-align: left; padding: 10px 12px; font-size: 14px;
    font-weight: 600; min-height: 36px;
}
QPushButton#quickAiAction { border-left: 3px solid $ai; }
QPushButton#quickAction:disabled, QPushButton#quickAiAction:disabled {
    border-color: $border; color: $muted;
}
QPushButton#moreTools { background: transparent; text-align: left; }
QPushButton#homePlanned { color: $muted; background: $panel; }
QComboBox, QSpinBox {
    color: $text; background: $elevated; border: 1px solid $border;
    border-radius: 8px; padding: 5px 10px; min-height: 34px;
}
QComboBox:focus, QSpinBox:focus { border: 2px solid $selection; }
QComboBox QAbstractItemView {
    color: $text; background: $elevated;
    selection-background-color: $border;
}
QSlider::groove:horizontal { height: 6px; background: $border; border-radius: 3px; }
QSlider::sub-page:horizontal { background: $selection; border-radius: 3px; }
QSlider::handle:horizontal {
    background: $primary; width: 18px; margin: -6px 0; border-radius: 9px;
}
QSlider:disabled::handle:horizontal { background: $muted; }
QProgressBar { border: 0; background: $border; border-radius: 3px; max-height: 7px; }
QProgressBar::chunk { background: $ai; border-radius: 3px; }
QTabWidget::pane { border: 1px solid $border; background: $panel; }
QTabBar::tab {
    color: $secondary; background: $elevated;
    padding: 10px 14px; min-height: 26px;
}
QTabBar::tab:selected { color: $primary; background: $panel; }
QToolButton {
    color: $text; background: $elevated;
    border: 1px solid $border; border-radius: 6px; padding: 6px;
}
QWidget#editingPage { background: $panel; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 9px; background: transparent; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle:horizontal { background: $border; width: 4px; }
QMenuBar { color: $secondary; background: $panel; }
QMenuBar::item:selected { background: $elevated; }
QMenu { background: $panel; color: $text; border: 1px solid $border; }
QMenu::item { padding: 8px 24px; }
QMenu::item:selected { background: $border; }
QMenu::item:disabled { color: $muted; }
QCheckBox { color: $text; spacing: 8px; }
QToolTip { color: $text; background: $elevated; border: 1px solid $border; padding: 6px; }
"""


def stylesheet() -> str:
    """Qt-supported stylesheet built from a single immutable token palette."""
    return Template(_QSS).substitute(COLORS)
