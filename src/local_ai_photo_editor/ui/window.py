"""Beginner-oriented editor window and its cancellable local inference jobs."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import Callable

from PIL import Image
from PySide6.QtCore import QProcess, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from ..branding import APP_NAME, PHOTO_EDITOR_TITLE, app_icon
from ..core import (
    MAX_IMAGE_PIXELS, MAX_MASK_STROKES, ImageDocument, MaskStroke, adjust_image,
    crop_image, export_image, load_image, load_project, paint_alpha_strokes,
    resize_image, rotate_image, save_project as save_project_archive,
)
from .canvas import PhotoCanvas
from .strings import STRINGS, translate

_STYLE = """
QMainWindow, QDialog { background: #1d2028; color: #edeef4; }
QWidget { font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 13px; }
QLabel { color: #edeef4; background: transparent; }
QLabel#appName { font-size: 22px; font-weight: 700; letter-spacing: -0.4px; }
QLabel#muted, QLabel#status { color: #aeb4c4; }
QLabel#localBadge { color: #b8e2d0; background: #253a35; border-radius: 12px; padding: 6px 12px; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; color: #f1eefb; }
QLabel#fileName { font-size: 14px; font-weight: 600; }
QLabel#sliderValue { color: #c8b9f4; font-size: 12px; }
QLabel#cropHint { color: #d8c6ff; padding: 10px; background: #342e45; border-radius: 6px; }
QFrame#toolCard { background: #262a34; border: 1px solid #343946; border-radius: 12px; }
QFrame#previewFrame { background: #15181e; border: 1px solid #353a47; border-radius: 12px; }
QFrame#jobBar { background: #302940; border: 1px solid #65527f; border-radius: 8px; }
QWidget#toolsPanel, QWidget#toolsViewport { background: #1d2028; }
QPushButton { color: #ecebf5; background: #343949; border: 1px solid #4b5162; border-radius: 7px; padding: 9px 12px; min-height: 20px; }
QPushButton:hover { background: #40475a; border-color: #807493; }
QPushButton:pressed, QPushButton:checked { background: #544469; border-color: #b29ad7; }
QPushButton:focus { border: 2px solid #c4aff2; padding: 8px 11px; }
QPushButton:disabled { color: #808796; background: #2a2e38; border-color: #353b48; }
QPushButton#primary { background: #b4a0e5; color: #191421; border: 1px solid #c6b5ee; font-weight: 600; }
QPushButton#primary:hover { background: #c9b7f2; }
QPushButton#primary:disabled { background: #514861; color: #a69bb8; border-color: #645773; }
QPushButton#quiet { background: transparent; }
QComboBox, QSpinBox { color: #edeef4; background: #292e3b; border: 1px solid #4b5264; border-radius: 6px; padding: 6px 10px; min-height: 20px; }
QComboBox QAbstractItemView { color: #edeef4; background: #292e3b; selection-background-color: #645379; }
QSlider::groove:horizontal { height: 5px; background: #494e5e; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #ad95d7; border-radius: 2px; }
QSlider::handle:horizontal { background: #e5d7ff; width: 15px; margin: -5px 0; border-radius: 7px; }
QSlider:disabled::handle:horizontal { background: #858491; }
QProgressBar { border: 0; background: #51465e; border-radius: 3px; max-height: 7px; }
QProgressBar::chunk { background: #baa0ea; border-radius: 3px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #4a5060; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMenuBar { color: #c6cbd7; background: #1d2028; }
QMenuBar::item:selected { background: #373c4a; }
QMenu { background: #292e39; color: #edeef4; border: 1px solid #4b5264; }
QMenu::item { padding: 8px 24px; }
QMenu::item:selected { background: #55456e; }
QMenu::item:disabled { color: #777e8e; }
QCheckBox { color: #edeef4; spacing: 8px; }
QToolTip { background: #ece7f5; color: #211b2a; border: 1px solid #b5a0d8; padding: 6px; }
"""


class EditorWindow(QMainWindow):
    """Single-document window; ``set_document`` also supports packaged smoke tests."""

    def __init__(self) -> None:
        super().__init__()
        self.document: ImageDocument | None = None
        self.language = "de"
        self._revision = 0
        self._exported_revision = 0
        self._saved_revision = 0
        self._project_path: Path | None = None
        self._project_created_exports: set[Path] = set()
        self._current_size = (0, 0)
        self._original_size = (0, 0)
        self._preview_base: Image.Image | None = None
        self._original_preview: Image.Image | None = None
        self._mask_preview: Image.Image | None = None
        self._mask_strokes: list[MaskStroke] = []
        self._mask_redo: list[MaskStroke] = []
        self._translated_widgets: list[tuple[object, str]] = []
        self._status_key = "ready"
        self._status_values: dict[str, object] = {}
        self._worker: QProcess | None = None
        self._job_directory: Path | None = None
        self._job_document: ImageDocument | None = None
        self._job_revision = -1
        self._job_size = (0, 0)
        self._cancel_requested = False
        self._job_start_failed = False
        self._close_when_idle = False
        self._close_approved = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._show_preview)
        self.setWindowTitle(PHOTO_EDITOR_TITLE)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(900, 660)
        self.resize(1180, 820)
        self.setAcceptDrops(True)
        self.setStyleSheet(_STYLE)
        self._build_ui()
        self.set_language("de")

    @property
    def is_busy(self) -> bool:
        return self._worker is not None

    @property
    def has_pending_adjustments(self) -> bool:
        return any(slider.value() != 100 for slider in self.sliders.values())

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _label(self, key: str, style: str = "", wrap: bool = False) -> QLabel:
        label = QLabel(self._t(key))
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(wrap)
        if style:
            label.setObjectName(style)
        self._translated_widgets.append((label, key))
        return label

    def _button(self, key: str, callback: Callable, style: str = "") -> QPushButton:
        button = QPushButton(self._t(key))
        button.clicked.connect(callback)
        if style:
            button.setObjectName(style)
        self._translated_widgets.append((button, key))
        return button

    def _action(self, key: str, callback: Callable, shortcut: QKeySequence.StandardKey | None = None) -> QAction:
        action = QAction(self._t(key), self)
        action.triggered.connect(callback)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        self._translated_widgets.append((action, key))
        return action

    def _card(self, title: str, hint: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("toolCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(self._label(title, "sectionTitle"))
        if hint:
            layout.addWidget(self._label(hint, "muted", wrap=True))
        return card, layout

    def _build_ui(self) -> None:
        self.open_action = self._action("open", self.open_photo, QKeySequence.StandardKey.Open)
        self.open_project_action = self._action("open_project", self.open_project)
        self.save_project_action = self._action("save_project", self.save_project, QKeySequence.StandardKey.Save)
        self.save_project_as_action = self._action("save_project_as", self.save_project_as)
        self.export_action = self._action("export", self.export_copy, QKeySequence.StandardKey.SaveAs)
        self.undo_action = self._action("undo", self.undo, QKeySequence.StandardKey.Undo)
        self.redo_action = self._action("redo", self.redo, QKeySequence.StandardKey.Redo)
        self.reset_action = self._action("reset", self.reset_to_original)
        self.quit_action = self._action("quit", self.close, QKeySequence.StandardKey.Quit)
        self._file_menu = self.menuBar().addMenu(self._t("file_menu"))
        self._file_menu.addActions([self.open_action, self.open_project_action])
        self._file_menu.addSeparator()
        self._file_menu.addActions([self.save_project_action, self.save_project_as_action, self.export_action])
        self._file_menu.addSeparator()
        self._file_menu.addAction(self.quit_action)
        self._edit_menu = self.menuBar().addMenu(self._t("edit_menu"))
        self._edit_menu.addActions([self.undo_action, self.redo_action])
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self.reset_action)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(24, 18, 24, 16)
        outer.setSpacing(18)
        header = QHBoxLayout()
        header.setSpacing(12)
        brand_mark = QLabel()
        brand_mark.setObjectName("brandMark")
        brand_mark.setPixmap(app_icon().pixmap(54, 54))
        brand_mark.setFixedSize(54, 54)
        brand_mark.setAccessibleName(APP_NAME)
        header.addWidget(brand_mark)
        identity = QVBoxLayout()
        identity.setSpacing(4)
        name = QLabel(APP_NAME)
        name.setObjectName("appName")
        identity.addWidget(name)
        identity.addWidget(self._label("app_tagline", "muted"))
        header.addLayout(identity)
        header.addStretch()
        header.addWidget(self._label("local_badge", "localBadge"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Deutsch", "de")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(
            lambda: self.set_language(str(self.language_combo.currentData()))
        )
        header.addWidget(self.language_combo)
        outer.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.open_button = self._button("open", self.open_photo)
        self.save_project_button = self._button("save_project", self.save_project)
        self.undo_button = self._button("undo", self.undo, "quiet")
        self.redo_button = self._button("redo", self.redo, "quiet")
        self.original_button = self._button("original", self._toggle_original, "quiet")
        self.original_button.setCheckable(True)
        self.export_button = self._button("export", self.export_copy, "primary")
        for button in (self.open_button, self.save_project_button, self.undo_button, self.redo_button, self.original_button):
            toolbar.addWidget(button)
        toolbar.addStretch()
        toolbar.addWidget(self.export_button)
        outer.addLayout(toolbar)

        content = QHBoxLayout()
        content.setSpacing(18)
        photo_frame = QFrame()
        photo_frame.setObjectName("previewFrame")
        photo_layout = QVBoxLayout(photo_frame)
        photo_layout.setContentsMargins(12, 12, 12, 12)
        photo_info = QHBoxLayout()
        self.file_label = QLabel()
        self.file_label.setTextFormat(Qt.TextFormat.PlainText)
        self.file_label.setObjectName("fileName")
        self.file_label.setMinimumWidth(0)
        self.file_label.setWordWrap(True)
        photo_info.addWidget(self.file_label, 1)
        photo_layout.addLayout(photo_info)
        self.canvas = PhotoCanvas()
        self.canvas.selection_changed.connect(self._on_crop_selection)
        self.canvas.brush_stroke_finished.connect(self._mask_stroke_finished)
        photo_layout.addWidget(self.canvas, 1)
        self.crop_hint = QLabel()
        self.crop_hint.setTextFormat(Qt.TextFormat.PlainText)
        self.crop_hint.setObjectName("cropHint")
        self.crop_hint.setWordWrap(True)
        photo_layout.addWidget(self.crop_hint)
        self.dimensions_label = QLabel()
        self.dimensions_label.setObjectName("muted")
        photo_layout.addWidget(self.dimensions_label)
        content.addWidget(photo_frame, 1)

        panel = QWidget()
        panel.setObjectName("toolsPanel")
        panel.setMinimumWidth(286)
        panel.setMaximumWidth(330)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 6, 0)
        panel_layout.setSpacing(14)
        ai_card, ai_layout = self._card("ai_title", "ai_hint")
        self.ai_button = self._button("ai_action", self.start_background_removal, "primary")
        ai_layout.addWidget(self.ai_button)
        ai_layout.addWidget(self._label("ai_note", "muted", wrap=True))
        panel_layout.addWidget(ai_card)

        mask_card, mask_layout = self._card("mask_title", "mask_hint")
        self.mask_button = self._button("mask_open", self._toggle_mask)
        self.mask_button.setCheckable(True)
        mask_layout.addWidget(self.mask_button)
        self.mask_settings = QWidget()
        mask_settings_layout = QVBoxLayout(self.mask_settings)
        mask_settings_layout.setContentsMargins(0, 0, 0, 0)
        mask_settings_layout.setSpacing(10)
        mask_settings_layout.addWidget(self._label("mask_instruction", "muted", wrap=True))

        mode_row = QFormLayout()
        self.mask_mode_combo = QComboBox()
        self.mask_mode_combo.addItem(self._t("mask_restore"), "restore")
        self.mask_mode_combo.addItem(self._t("mask_erase"), "erase")
        self.mask_mode_combo.currentIndexChanged.connect(self._on_mask_settings_changed)
        mode_label = self._label("mask_mode")
        mode_label.setBuddy(self.mask_mode_combo)
        mode_row.addRow(mode_label, self.mask_mode_combo)
        mask_settings_layout.addLayout(mode_row)

        self.mask_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.mask_size_slider.setRange(1, 20)
        self.mask_size_slider.setValue(4)
        self.mask_size_slider.valueChanged.connect(self._on_mask_settings_changed)
        size_header = QHBoxLayout()
        size_label = self._label("mask_size")
        size_label.setBuddy(self.mask_size_slider)
        size_header.addWidget(size_label)
        size_header.addStretch()
        self.mask_size_value = QLabel("4 %")
        self.mask_size_value.setObjectName("sliderValue")
        size_header.addWidget(self.mask_size_value)
        mask_settings_layout.addLayout(size_header)
        mask_settings_layout.addWidget(self.mask_size_slider)

        self.mask_feather_slider = QSlider(Qt.Orientation.Horizontal)
        self.mask_feather_slider.setRange(0, 100)
        self.mask_feather_slider.setValue(30)
        self.mask_feather_slider.valueChanged.connect(self._on_mask_settings_changed)
        feather_header = QHBoxLayout()
        feather_label = self._label("mask_feather")
        feather_label.setBuddy(self.mask_feather_slider)
        feather_header.addWidget(feather_label)
        feather_header.addStretch()
        self.mask_feather_value = QLabel("30 %")
        self.mask_feather_value.setObjectName("sliderValue")
        feather_header.addWidget(self.mask_feather_value)
        mask_settings_layout.addLayout(feather_header)
        mask_settings_layout.addWidget(self.mask_feather_slider)

        mask_actions = QHBoxLayout()
        self.mask_apply_button = self._button("mask_apply", self.apply_mask_refinement, "primary")
        self.mask_cancel_button = self._button("mask_cancel_mode", self.discard_mask_refinement, "quiet")
        mask_actions.addWidget(self.mask_apply_button)
        mask_actions.addWidget(self.mask_cancel_button)
        mask_settings_layout.addLayout(mask_actions)
        mask_layout.addWidget(self.mask_settings)
        self.mask_settings.setVisible(False)
        panel_layout.addWidget(mask_card)

        adjust_card, adjustments = self._card("adjust_title", "adjust_hint")
        self.sliders: dict[str, QSlider] = {}
        self._slider_values: dict[str, QLabel] = {}
        for key in ("brightness", "contrast", "saturation"):
            row = QHBoxLayout()
            label = self._label(key)
            row.addWidget(label)
            row.addStretch()
            value = QLabel("0 %")
            value.setObjectName("sliderValue")
            row.addWidget(value)
            adjustments.addLayout(row)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 200)
            slider.setValue(100)
            slider.setSingleStep(1)
            slider.setPageStep(10)
            label.setBuddy(slider)
            slider.valueChanged.connect(self._on_adjustment_changed)
            self.sliders[key] = slider
            self._slider_values[key] = value
            adjustments.addWidget(slider)
        adjust_actions = QHBoxLayout()
        self.apply_button = self._button("apply", self.apply_adjustments, "primary")
        self.discard_button = self._button("discard", self.discard_adjustments, "quiet")
        adjust_actions.addWidget(self.apply_button)
        adjust_actions.addWidget(self.discard_button)
        adjustments.addLayout(adjust_actions)
        panel_layout.addWidget(adjust_card)

        shape_card, shape_layout = self._card("shape_title")
        shape_row = QHBoxLayout()
        self.rotate_button = self._button("rotate", self.rotate_clockwise)
        self.crop_button = self._button("crop", self._toggle_crop)
        self.crop_button.setCheckable(True)
        shape_row.addWidget(self.rotate_button)
        shape_row.addWidget(self.crop_button)
        shape_layout.addLayout(shape_row)
        self.crop_apply_button = self._button("crop_apply", self.apply_crop, "primary")
        shape_layout.addWidget(self.crop_apply_button)
        self.resize_button = self._button("resize", self.show_resize_dialog)
        shape_layout.addWidget(self.resize_button)
        panel_layout.addWidget(shape_card)

        panel_layout.addStretch()
        scroll = QScrollArea()
        scroll.viewport().setObjectName("toolsViewport")
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(300)
        scroll.setMaximumWidth(344)
        content.addWidget(scroll)
        outer.addLayout(content, 1)

        self.job_bar = QFrame()
        self.job_bar.setObjectName("jobBar")
        job_layout = QHBoxLayout(self.job_bar)
        job_layout.setContentsMargins(14, 10, 14, 10)
        self.job_label = self._label("ai_busy")
        job_layout.addWidget(self.job_label)
        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(False)
        job_layout.addWidget(progress, 1)
        self.cancel_button = self._button("cancel", self.cancel_background_removal)
        job_layout.addWidget(self.cancel_button)
        outer.addWidget(self.job_bar)
        self.status_label = QLabel()
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        outer.addWidget(self.status_label)

    def set_language(self, language: str) -> None:
        if language not in STRINGS:
            raise ValueError("Unsupported UI language.")
        self.language = language
        with QSignalBlocker(self.language_combo):
            self.language_combo.setCurrentIndex(self.language_combo.findData(language))
        for widget, key in self._translated_widgets:
            widget.setText(self._t(key))
        self._file_menu.setTitle(self._t("file_menu"))
        self._edit_menu.setTitle(self._t("edit_menu"))
        self.language_combo.setAccessibleName(self._t("language"))
        self.language_combo.setToolTip(self._t("language"))
        self.export_button.setToolTip(self._t("export_hint"))
        for control in (self.undo_button, self.redo_button):
            control.setToolTip(self._t("mask_instruction" if self.mask_button.isChecked() else "history_hint"))
        self.mask_mode_combo.setItemText(0, self._t("mask_restore"))
        self.mask_mode_combo.setItemText(1, self._t("mask_erase"))
        self.mask_mode_combo.setAccessibleName(self._t("mask_mode"))
        self.mask_size_slider.setAccessibleName(self._t("mask_size"))
        self.mask_feather_slider.setAccessibleName(self._t("mask_feather"))
        self.mask_button.setToolTip(self._t("mask_instruction" if self.mask_button.isChecked() else "mask_requires_alpha"))
        for key, slider in self.sliders.items():
            slider.setAccessibleName(self._t(key))
        self.canvas.set_language(language)
        self._update_state()

    def set_document(self, image: Image.Image, source_path: str | Path | None = None) -> None:
        self._install_document(ImageDocument(image, source_path))
        self._set_status("loaded")

    def _install_document(self, document: ImageDocument) -> None:
        if self.is_busy:
            raise RuntimeError("Cannot replace the document during an active job.")
        self.document = document
        self._revision += 1
        self._exported_revision = self._revision
        self._saved_revision = self._revision
        self._project_path = None
        self._project_created_exports.clear()
        self.original_button.setChecked(False)
        self.crop_button.setChecked(False)
        self.canvas.set_crop_enabled(False)
        self._leave_mask()
        self._reset_sliders()
        original = document.original
        self._original_size = original.size
        self._original_preview = self._thumbnail(original)
        self._refresh_document()

    @staticmethod
    def _thumbnail(image: Image.Image) -> Image.Image:
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        return image

    def _refresh_document(self) -> None:
        if self.document is None:
            return
        current = self.document.current
        self._current_size = current.size
        self._preview_base = self._thumbnail(current)
        self._show_preview()
        self._update_state()

    def _show_preview(self) -> None:
        if self._preview_base is None:
            return
        try:
            if self.original_button.isChecked():
                self.canvas.set_image(self._original_preview, self._original_size)
            else:
                preview = self._mask_preview if self.mask_button.isChecked() and self._mask_preview is not None else self._preview_base
                if self.has_pending_adjustments:
                    preview = adjust_image(preview, **self._adjustment_values())
                self.canvas.set_image(preview, self._current_size)
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)

    def _set_status(self, key: str, **values: object) -> None:
        self._status_key, self._status_values = key, values
        self._update_status()

    def _update_status(self) -> None:
        if self.original_button.isChecked():
            text = self._t("viewing_original")
        elif self.has_pending_adjustments:
            text = self._t("preview")
        elif self.mask_button.isChecked():
            text = self._t("mask_preview")
        else:
            text = self._t(self._status_key, **self._status_values)
        self.status_label.setText(text)

    def _update_state(self) -> None:
        has_document = self.document is not None
        idle = not self.is_busy
        pending = self.has_pending_adjustments
        original = self.original_button.isChecked()
        cropping = self.crop_button.isChecked()
        masking = self.mask_button.isChecked()
        editable = has_document and idle and not pending and not original and not masking
        self.open_button.setEnabled(idle)
        self.open_action.setEnabled(idle)
        self.open_project_action.setEnabled(idle)
        for control in (self.save_project_button, self.save_project_action, self.save_project_as_action):
            control.setEnabled(editable and not cropping)
        self.original_button.setEnabled(has_document and idle and not cropping and not masking)
        self.original_button.setText(self._t("original_active" if original else "original"))
        for control in (self.export_button, self.export_action):
            control.setEnabled(editable and not cropping)
        for control in (self.undo_button, self.undo_action):
            control.setEnabled(bool((masking and self._mask_strokes) or (editable and self.document.can_undo and not cropping)))
        for control in (self.redo_button, self.redo_action):
            control.setEnabled(bool((masking and self._mask_redo) or (editable and self.document.can_redo and not cropping)))
        self.reset_action.setEnabled(bool(editable and self.document.history and not cropping))
        for slider in self.sliders.values():
            slider.setEnabled(has_document and idle and not original and not cropping and not masking)
        self.apply_button.setEnabled(has_document and idle and pending and not original and not masking)
        self.discard_button.setEnabled(has_document and idle and pending and not masking)
        for control in (self.rotate_button, self.resize_button, self.ai_button):
            control.setEnabled(editable and not cropping)
        self.crop_button.setEnabled(editable)
        self.crop_button.setText(self._t("crop_cancel" if cropping else "crop"))
        can_mask = bool(has_document and idle and not pending and not original and not cropping and self._preview_base is not None and self._preview_base.mode == "RGBA")
        self.mask_button.setEnabled(can_mask)
        self.mask_button.setText(self._t("mask_cancel_mode" if masking else "mask_open"))
        self.mask_settings.setVisible(masking)
        self.mask_apply_button.setEnabled(bool(masking and self._mask_strokes))
        for control in (self.mask_mode_combo, self.mask_size_slider, self.mask_feather_slider, self.mask_cancel_button):
            control.setEnabled(masking)
        for control in (self.undo_button, self.redo_button):
            control.setToolTip(self._t("mask_instruction" if masking else "history_hint"))
        self.crop_apply_button.setVisible(cropping)
        self.crop_apply_button.setEnabled(editable and self.canvas.crop_box is not None)
        self.crop_hint.setVisible(cropping)
        self._update_crop_hint()
        self.canvas.setEnabled(idle)
        self.job_bar.setVisible(self.is_busy)
        self.cancel_button.setEnabled(self.is_busy and not self._cancel_requested)
        self.job_label.setText(self._t("cancelling" if self._cancel_requested else "ai_busy"))
        self.file_label.setText(
            self._project_path.name if has_document and self._project_path
            else self.document.source_path.name if has_document and self.document.source_path
            else self._t("untitled" if has_document else "no_photo")
        )
        self.dimensions_label.setText(
            self._t("dimensions", width=self._current_size[0], height=self._current_size[1], edits=len(self.document.history))
            if has_document else ""
        )
        self._update_status()

    def _editable(self) -> bool:
        return self.document is not None and not self.is_busy and not self.has_pending_adjustments and not self.original_button.isChecked() and not self.mask_button.isChecked()

    def _adjustment_values(self) -> dict[str, float]:
        return {key: slider.value() / 100 for key, slider in self.sliders.items()}

    def _on_adjustment_changed(self) -> None:
        for key, slider in self.sliders.items():
            difference = slider.value() - 100
            self._slider_values[key].setText(f"{difference:+d} %" if difference else "0 %")
        self._preview_timer.start(80)
        self._update_state()

    def _reset_sliders(self) -> None:
        self._preview_timer.stop()
        for key, slider in self.sliders.items():
            with QSignalBlocker(slider):
                slider.setValue(100)
            self._slider_values[key].setText("0 %")

    def discard_adjustments(self) -> None:
        if self.is_busy:
            return
        self._reset_sliders()
        self._show_preview()
        self._update_state()

    def _accept_result(self, result: Image.Image, label: str) -> None:
        if self.document is None:
            return
        self.document.apply(result, self._t(label))
        self._revision += 1
        self._reset_sliders()
        self._leave_crop()
        self._leave_mask()
        self._refresh_document()
        self._set_status("applied")

    def apply_adjustments(self) -> None:
        if self.document is None or self.is_busy or self.original_button.isChecked() or not self.has_pending_adjustments:
            return
        try:
            result = adjust_image(self.document.current, **self._adjustment_values())
            self._accept_result(result, "operation_adjust")
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)

    def _apply_operation(self, operation: Callable[[Image.Image], Image.Image], label: str) -> None:
        if not self._editable():
            return
        try:
            self._accept_result(operation(self.document.current), label)
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)

    def rotate_clockwise(self) -> None:
        self._apply_operation(rotate_image, "operation_rotate")

    def undo(self) -> None:
        if self.mask_button.isChecked():
            if self._mask_strokes:
                self._mask_redo.append(self._mask_strokes.pop())
                self._update_mask_preview()
            return
        if self._editable() and not self.crop_button.isChecked() and self.document.undo():
            self._revision += 1
            self._refresh_document()
            self._set_status("undo_done")

    def redo(self) -> None:
        if self.mask_button.isChecked():
            if self._mask_redo:
                self._mask_strokes.append(self._mask_redo.pop())
                self._update_mask_preview()
            return
        if self._editable() and not self.crop_button.isChecked() and self.document.redo():
            self._revision += 1
            self._refresh_document()
            self._set_status("redo_done")

    def reset_to_original(self) -> None:
        if self._editable() and not self.crop_button.isChecked():
            try:
                self.document.reset(self._t("reset"))
                self._revision += 1
                self._refresh_document()
                self._set_status("applied")
            except (ValueError, OSError, MemoryError) as exc:
                self._show_error("edit_error", exc)

    def _toggle_original(self) -> None:
        self._show_preview()
        self._update_state()

    def _toggle_mask(self) -> None:
        if self.mask_button.isChecked():
            if (
                self.document is None or self.is_busy or self.has_pending_adjustments
                or self.original_button.isChecked() or self.crop_button.isChecked()
                or self._preview_base is None or self._preview_base.mode != "RGBA"
            ):
                self.mask_button.setChecked(False)
                return
            self._mask_strokes.clear()
            self._mask_redo.clear()
            self._mask_preview = None
            self.canvas.set_brush_enabled(True)
            self._on_mask_settings_changed()
        else:
            self._leave_mask()
        self._show_preview()
        self._update_state()

    def _leave_mask(self) -> None:
        self.mask_button.setChecked(False)
        self._mask_strokes.clear()
        self._mask_redo.clear()
        self._mask_preview = None
        self.canvas.set_brush_enabled(False)

    def _on_mask_settings_changed(self) -> None:
        mode = str(self.mask_mode_combo.currentData())
        self.canvas.set_brush(mode, self.mask_size_slider.value() / 100)
        self.mask_size_value.setText(f"{self.mask_size_slider.value()} %")
        self.mask_feather_value.setText(f"{self.mask_feather_slider.value()} %")

    def _update_mask_preview(self) -> None:
        try:
            self._mask_preview = (
                paint_alpha_strokes(self._preview_base, self._mask_strokes)
                if self._mask_strokes else None
            )
            self._show_preview()
            self._update_state()
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)

    def _mask_stroke_finished(self, points: object) -> None:
        if not self.mask_button.isChecked() or self.document is None or self.is_busy:
            return
        if len(self._mask_strokes) >= MAX_MASK_STROKES:
            self._set_status("mask_limit")
            QMessageBox.warning(self, self._t("error_title"), self._t("mask_limit"))
            return
        stroke = MaskStroke(
            points=tuple(points),
            mode=str(self.mask_mode_combo.currentData()),
            diameter=self.mask_size_slider.value() / 100,
            feather=self.mask_feather_slider.value() / 100,
        )
        self._mask_strokes.append(stroke)
        self._mask_redo.clear()
        self._update_mask_preview()

    def apply_mask_refinement(self) -> None:
        if not self.mask_button.isChecked() or self.document is None or self.is_busy or not self._mask_strokes:
            return
        try:
            result = paint_alpha_strokes(self.document.current, self._mask_strokes)
            self._accept_result(result, "operation_mask")
            self._set_status("mask_applied")
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)

    def discard_mask_refinement(self) -> None:
        if not self.mask_button.isChecked() or self.is_busy:
            return
        self._leave_mask()
        self._show_preview()
        self._update_state()

    def _toggle_crop(self) -> None:
        self.canvas.set_crop_enabled(self.crop_button.isChecked())
        self._update_state()

    def _leave_crop(self) -> None:
        self.crop_button.setChecked(False)
        self.canvas.set_crop_enabled(False)

    def _update_crop_hint(self) -> None:
        box = self.canvas.crop_box
        text = self._t("crop_hint")
        if box is not None:
            text += "  " + self._t("crop_selected", width=box[2] - box[0], height=box[3] - box[1])
        self.crop_hint.setText(text)

    def _on_crop_selection(self, box: object) -> None:
        # Construction and preview changes can emit before every control exists.
        if hasattr(self, "crop_apply_button"):
            self.crop_apply_button.setEnabled(box is not None and self._editable())
            self._update_crop_hint()

    def apply_crop(self) -> None:
        box = self.canvas.crop_box
        if self.crop_button.isChecked() and box is not None:
            self._apply_operation(lambda picture: crop_image(picture, box), "operation_crop")

    def show_resize_dialog(self) -> None:
        if not self._editable():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("resize_title"))
        dialog.setMinimumWidth(330)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)
        hint = QLabel(self._t("resize_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        width, height = QSpinBox(), QSpinBox()
        for spin in (width, height):
            spin.setRange(1, MAX_IMAGE_PIXELS)
        width.setValue(self._current_size[0])
        height.setValue(self._current_size[1])
        form.addRow(self._t("width"), width)
        form.addRow(self._t("height"), height)
        layout.addLayout(form)
        keep_ratio = QCheckBox(self._t("keep_ratio"))
        keep_ratio.setChecked(True)
        layout.addWidget(keep_ratio)
        ratio = self._current_size[0] / self._current_size[1]

        def update_height(value: int) -> None:
            if keep_ratio.isChecked():
                with QSignalBlocker(height):
                    height.setValue(max(1, round(value / ratio)))

        def update_width(value: int) -> None:
            if keep_ratio.isChecked():
                with QSignalBlocker(width):
                    width.setValue(max(1, round(value * ratio)))

        width.valueChanged.connect(update_height)
        height.valueChanged.connect(update_width)
        keep_ratio.toggled.connect(lambda enabled: update_height(width.value()) if enabled else None)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self._t("apply"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._t("cancel"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._apply_operation(lambda picture: resize_image(picture, width.value(), height.value()), "operation_resize")

    def _has_unexported_changes(self) -> bool:
        if self.document is None:
            return False
        if self.has_pending_adjustments:
            return True
        # A saved editable project takes precedence over a flattened image
        # export, since exporting does not update that project's edit history.
        saved_revision = self._saved_revision if self._project_path else self._exported_revision
        return self._revision != saved_revision or bool(self.mask_button.isChecked() and self._mask_strokes)

    def _confirm(self, title: str, body: str) -> bool:
        message = QMessageBox(self)
        message.setWindowTitle(self._t(title))
        message.setTextFormat(Qt.TextFormat.PlainText)
        message.setText(self._t(body))
        message.setIcon(QMessageBox.Icon.Question)
        accept = message.addButton(self._t("yes"), QMessageBox.ButtonRole.AcceptRole)
        reject = message.addButton(self._t("no"), QMessageBox.ButtonRole.RejectRole)
        message.setDefaultButton(reject)
        message.exec()
        return message.clickedButton() is accept

    def _show_error(self, fallback: str, error: BaseException | None = None) -> None:
        key = fallback
        if isinstance(error, MemoryError):
            key = "memory_error"
        elif isinstance(error, (FileNotFoundError, PermissionError)) and fallback != "export_error":
            key = "file_access_error"
        elif isinstance(error, ValueError):
            detail = str(error).lower()
            if "limited to" in detail or "40,000,000" in detail:
                key = "image_too_large"
            elif "original image" in detail or "original photo" in detail:
                key = "source_protected"
            elif "icc" in detail or "profile" in detail:
                key = "invalid_profile"
            elif "animated" in detail or "multipage" in detail:
                key = "animated_image"
            elif "image mode" in detail or "8-bit" in detail:
                key = "unsupported_image"
        self._set_status(key)
        QMessageBox.warning(self, self._t("error_title"), self._t(key))

    def open_photo(self) -> None:
        if self.is_busy:
            return
        path, _ = QFileDialog.getOpenFileName(self, self._t("open"), "", self._t("open_filter"))
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        if self.is_busy:
            return
        if self._has_unexported_changes() and not self._confirm("replace_title", "replace_body"):
            return
        try:
            self.set_document(load_image(path), path)
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("open_error", exc)

    def open_project(self) -> None:
        if self.is_busy:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("open_project"), "", self._t("project_filter")
        )
        if path:
            self.open_project_path(path)

    def open_project_path(self, path: str | Path) -> None:
        if self.is_busy:
            return
        if self._has_unexported_changes() and not self._confirm("replace_title", "replace_body"):
            return
        try:
            restored = load_project(path)
            self._install_document(restored)
            self._project_path = Path(path).expanduser().absolute()
            self._saved_revision = self._revision
            self._update_state()
            self._set_status("project_loaded")
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("project_error", exc)

    def save_project(self) -> None:
        if not self._editable() or self.crop_button.isChecked():
            return
        if self._project_path is not None:
            self._write_project(self._project_path)
        else:
            self.save_project_as()

    def save_project_as(self) -> None:
        if not self._editable() or self.crop_button.isChecked():
            return
        source = self.document.source_path
        directory = self._project_path.parent if self._project_path else source.parent if source else Path.home()
        stem = self._project_path.stem if self._project_path else source.stem if source else "photo"
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("save_project_as"), str(directory / f"{stem}.laip"),
            self._t("project_filter"), options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".laip")
        if target.suffix.lower() != ".laip":
            self._show_error("project_error")
            return
        if target.exists() and not self._confirm("replace_export_title", "replace_export_body"):
            return
        self._write_project(target)

    def _write_project(self, path: Path) -> None:
        try:
            destination = save_project_archive(self.document, path)
            self._project_path = destination
            self._saved_revision = self._revision
            self._set_status("project_saved", name=destination.name)
            self._update_state()
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("project_error", exc)

    def export_copy(self) -> None:
        if not self._editable() or self.crop_button.isChecked():
            return
        source = self.document.source_path
        stem = self._project_path.stem if self._project_path else source.stem if source else self._t("untitled")
        directory = self._project_path.parent if self._project_path else source.parent if source else Path.home()
        default = directory / f"{stem}-{self._t('export_suffix')}.png"
        path, selected_filter = QFileDialog.getSaveFileName(
            self, self._t("export"), str(default), self._t("export_filter"),
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            suffix = ".jpg" if selected_filter.startswith("JPEG") else ".webp" if selected_filter.startswith("WebP") else ".png"
            target = target.with_suffix(suffix)
        try:
            if source is not None and (
                target.resolve() == source.resolve()
                or (target.exists() and source.exists() and target.samefile(source))
            ):
                self._show_error("source_protected")
                return
            # A reopened project intentionally omits the source filesystem
            # path. Never overwrite a pre-existing image in that case: it
            # could be the original photo. This session's own exports are safe.
            if (
                source is None and self._project_path is not None and target.exists()
                and target.absolute() not in self._project_created_exports
            ):
                self._show_error("project_export_existing")
                return
            if target.exists() and not self._confirm("replace_export_title", "replace_export_body"):
                return
            result = export_image(self.document.current, target, source_path=source)
            if self._project_path is not None:
                self._project_created_exports.add(result.absolute())
            self._exported_revision = self._revision
            self._set_status("export_done", name=result.name)
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("export_error", exc)

    @staticmethod
    def _drop_path(event: QDragEnterEvent | QDropEvent) -> Path | None:
        urls = event.mimeData().urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            return None
        path = Path(urls[0].toLocalFile())
        return path if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".laip"} and path.is_file() else None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self.is_busy and self._drop_path(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        path = self._drop_path(event)
        if not self.is_busy and path is not None:
            event.acceptProposedAction()
            if path.suffix.lower() == ".laip":
                self.open_project_path(path)
            else:
                self.open_path(path)
        else:
            event.ignore()

    def start_background_removal(self) -> None:
        if not self._editable() or self.crop_button.isChecked():
            return
        from ..__main__ import worker_command

        directory: Path | None = None
        try:
            directory = Path(tempfile.mkdtemp(prefix="localai-job-"))
            picture = self.document.current
            picture.save(directory / "input.png", format="PNG")
            (directory / "request.json").write_text(
                json.dumps({"version": 1, "operation": "remove_background"}), encoding="utf-8",
            )
            program, arguments = worker_command(directory)
            process = QProcess(self)
            self._worker = process
            self._job_directory = directory
            self._job_document = self.document
            self._job_revision = self._revision
            self._job_size = picture.size
            self._cancel_requested = False
            self._job_start_failed = False
            process.finished.connect(lambda code, status: self._finish_job(process, code))
            process.errorOccurred.connect(lambda error: self._worker_error(process, error))
            process.started.connect(lambda: process.kill() if self._cancel_requested else None)
            # No shell or TCP server; the command carries only a private job path.
            process.setProgram(program)
            process.setArguments(arguments)
            process.setStandardOutputFile(QProcess.nullDevice())
            process.setStandardErrorFile(QProcess.nullDevice())
            self._set_status("ai_busy")
            self._update_state()
            process.start()
        except (ValueError, OSError, MemoryError) as exc:
            if directory is not None:
                shutil.rmtree(directory, ignore_errors=True)
            self._worker = None
            self._job_directory = None
            self._job_document = None
            self._update_state()
            self._show_error("worker_start_error", exc)

    def _worker_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process is self._worker and error == QProcess.ProcessError.FailedToStart:
            self._job_start_failed = True
            self._finish_job(process, -1)

    def cancel_background_removal(self) -> None:
        if self._worker is None:
            return
        self._cancel_requested = True
        self._update_state()
        self._worker.kill()
        # finished/errorOccurred owns cleanup after the process has stopped.

    def _finish_job(self, process: QProcess, exit_code: int) -> None:
        if process is not self._worker or process.state() != QProcess.ProcessState.NotRunning:
            return
        directory = self._job_directory
        cancelled = self._cancel_requested
        close_after = self._close_when_idle
        error_key: str | None = "worker_start_error" if self._job_start_failed else None
        result: Image.Image | None = None
        if not cancelled and not close_after and error_key is None:
            try:
                status_path = directory / "result.json"
                output_path = directory / "output.png"
                if status_path.is_symlink() or status_path.stat().st_size > 4096:
                    raise ValueError("Invalid worker result.")
                status = json.loads(status_path.read_text(encoding="utf-8"))
                if not isinstance(status, dict):
                    raise ValueError("Invalid worker result.")
                if status.get("status") == "ok" and exit_code == 0:
                    if output_path.is_symlink():
                        raise ValueError("Invalid worker output.")
                    result = load_image(output_path)
                    if result.size != self._job_size:
                        raise ValueError("Unexpected worker output dimensions.")
                    if self.document is not self._job_document or self._revision != self._job_revision:
                        raise ValueError("The document changed during inference.")
                else:
                    error_key = {
                        "MODEL_MISSING": "model_missing",
                        "MODEL_INVALID": "model_invalid",
                    }.get(status.get("code"), "inference_error")
            except (OSError, ValueError, TypeError, MemoryError) as exc:
                error_key = "memory_error" if isinstance(exc, MemoryError) else "inference_error"
        self._worker = None
        self._job_directory = None
        self._job_document = None
        self._cancel_requested = False
        self._job_start_failed = False
        process.deleteLater()
        cleanup_failed = False
        if directory is not None:
            try:
                shutil.rmtree(directory)
            except OSError:
                cleanup_failed = True
        self._update_state()
        if close_after:
            self._close_approved = True
            QTimer.singleShot(0, self.close)
            return
        if cancelled:
            self._set_status("ai_cancelled")
        elif error_key is not None:
            self._show_error(error_key)
        elif result is not None:
            try:
                self._accept_result(result, "operation_ai")
                self._set_status("ai_done")
            except (ValueError, OSError, MemoryError) as exc:
                self._show_error("edit_error", exc)
        if cleanup_failed:
            self._set_status("cleanup_warning")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._close_approved:
            self._preview_timer.stop()
            event.accept()
            return
        if self.is_busy:
            event.ignore()
            if self._close_when_idle or self._confirm("busy_close_title", "busy_close_body"):
                self._close_when_idle = True
                self.cancel_background_removal()
            return
        if self._has_unexported_changes() and not self._confirm("close_title", "close_body"):
            event.ignore()
            return
        self._preview_timer.stop()
        event.accept()
