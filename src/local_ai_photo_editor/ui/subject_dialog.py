"""Beginner subject effects: infer once, inspect, preview, explicitly apply."""
from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QSignalBlocker, QThread, QTimer, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from ..core.recipes import RenderCancelled
from ..core.subject import (
    SUBJECT_MODES, SubjectEdit, effective_subject_mask, render_subject,
    selection_overlay, subject_bounds, validate_subject_mask,
)
from .canvas import PhotoCanvas
from .subject_job import SubjectSelectionJob
from .subject_strings import text

_DEFAULT_STRENGTH = {"blur": 60, "color_pop": 100, "light": 35, "dim": 45, "cutout": 100, "crop": 100}


class _SubjectRenderThread(QThread):
    def __init__(self, image: Image.Image, mask: Image.Image, edit: SubjectEdit, parent: QWidget) -> None:
        super().__init__(parent)
        self.image, self.mask, self.edit = image, mask, edit
        self.result_image: Image.Image | None = None
        self.failed = False

    def run(self) -> None:
        try:
            self.result_image = render_subject(self.image, self.mask, self.edit,
                                               cancelled=self.isInterruptionRequested)
        except RenderCancelled:
            pass
        except Exception:
            self.failed = True


class SubjectDialog(QDialog):
    """No accepted image is mutated, even when inference or rendering fails."""
    def __init__(self, image: Image.Image, language: str = "de", mode: str = "blur",
                 parent: QWidget | None = None, *, start_immediately: bool = True) -> None:
        super().__init__(parent)
        SubjectEdit(mode=mode)
        self.language = language
        self._image = image.copy()
        self._preview_source = image.copy()
        self._preview_source.thumbnail((960, 960), Image.Resampling.LANCZOS)
        self._mask: Image.Image | None = None
        self._preview_mask: Image.Image | None = None
        self._preview_result: Image.Image | None = None
        self._preview_valid = False
        self._result_size = image.size
        self._closing = False
        self._error_code = ""
        self._worker: _SubjectRenderThread | None = None
        self.result_image: Image.Image | None = None
        self.job = SubjectSelectionJob(self)
        self.job.finished.connect(self._selection_finished)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._render_preview)
        self._start_timer = QTimer(self)
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self.start_selection)
        self.setWindowTitle(self._t("title"))
        self.setMinimumSize(820, 580)
        self.resize(1080, 740)
        self._build(mode)
        self.canvas.set_image(self._preview_source, self._image.size)
        self._update_controls()
        if start_immediately:
            self._start_timer.start(0)

    def _t(self, key: str, **values: object) -> str:
        return text(self.language, key, **values)

    @property
    def is_busy(self) -> bool:
        return self.job.is_running or self._worker is not None

    @property
    def edit(self) -> SubjectEdit:
        return SubjectEdit(mode=str(self.mode_combo.currentData()), strength=self.strength.value(),
                           feather=self.feather.value(), padding=self.padding.value())

    def _label(self, key: str) -> QLabel:
        label = QLabel(self._t(key))
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        return label

    def _button(self, key: str, callback) -> QPushButton:
        button = QPushButton(self._t(key))
        button.clicked.connect(callback)
        return button

    def _slider(self, layout: QVBoxLayout, key: str, maximum: int, value: int) -> tuple[QWidget, QSlider, QLabel]:
        container = QWidget()
        rows = QVBoxLayout(container)
        rows.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        label = self._label(key)
        header.addWidget(label, 1)
        number = QLabel()
        number.setObjectName("sliderValue")
        header.addWidget(number)
        rows.addLayout(header)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, maximum)
        slider.setValue(value)
        slider.setPageStep(10)
        slider.setAccessibleName(self._t(key))
        label.setBuddy(slider)
        if key in {"feather", "padding"}:
            slider.setToolTip(self._t(key + "_hint"))
        slider.valueChanged.connect(self._changed)
        rows.addWidget(slider)
        layout.addWidget(container)
        return container, slider, number

    def _build(self, mode: str) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)
        outer.addWidget(self._label("intro"))
        content = QHBoxLayout()
        self.canvas = PhotoCanvas()
        self.canvas.set_language(self.language)
        self.canvas.setMinimumSize(340, 290)
        content.addWidget(self.canvas, 1)
        self.panel = QWidget()
        self.panel.setObjectName("toolsPanel")
        panel = QVBoxLayout(self.panel)
        panel.setContentsMargins(16, 12, 16, 12)
        panel.setSpacing(14)
        mode_label = self._label("mode")
        panel.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.setAccessibleName(self._t("mode"))
        for value in SUBJECT_MODES:
            self.mode_combo.addItem(self._t(value), value)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(mode))
        self.mode_combo.setMinimumContentsLength(20)
        self.mode_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        mode_label.setBuddy(self.mode_combo)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        panel.addWidget(self.mode_combo)
        self.mode_hint = self._label(mode + "_hint")
        panel.addWidget(self.mode_hint)
        self.strength_row, self.strength, self.strength_value = self._slider(panel, "strength", 100, _DEFAULT_STRENGTH[mode])
        self.feather_row, self.feather, self.feather_value = self._slider(panel, "feather", 100, 0)
        self.padding_row, self.padding, self.padding_value = self._slider(panel, "padding", 40, 12)
        self.selection_check = QCheckBox(self._t("selection"))
        self.selection_check.setToolTip(self._t("selection_hint"))
        self.selection_check.toggled.connect(self._show_preview)
        panel.addWidget(self.selection_check)
        self.compare_button = self._button("before", self._show_preview)
        self.compare_button.setCheckable(True)
        panel.addWidget(self.compare_button)
        self.reset_button = self._button("reset", self.reset_settings)
        panel.addWidget(self.reset_button)
        panel.addWidget(self._label("limits"))
        panel.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.panel)
        scroll.setMinimumWidth(320)
        scroll.setMaximumWidth(380)
        content.addWidget(scroll)
        outer.addLayout(content, 1)
        self.status = self._label("detecting")
        outer.addWidget(self.status)
        self.cleanup_label = self._label("cleanup_warning")
        self.cleanup_label.hide()
        outer.addWidget(self.cleanup_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        outer.addWidget(self.progress)
        footer = QHBoxLayout()
        self.retry_button = self._button("retry", self.start_selection)
        footer.addWidget(self.retry_button)
        footer.addStretch()
        self.cancel_button = self._button("cancel", self.reject)
        self.apply_button = self._button("apply", self.accept)
        self.apply_button.setObjectName("primary")
        self.apply_button.setDefault(True)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.apply_button)
        outer.addLayout(footer)

    def _update_controls(self) -> None:
        ready = self._mask is not None and not self.is_busy and not self._closing
        self.panel.setEnabled(ready)
        mode = self.edit.mode
        self.strength_row.setVisible(mode not in {"cutout", "crop"})
        self.padding_row.setVisible(mode == "crop")
        self.mode_hint.setText(self._t(mode + "_hint"))
        for slider, label in ((self.strength, self.strength_value), (self.feather, self.feather_value), (self.padding, self.padding_value)):
            label.setText(f"{slider.value()} %")
        self.apply_button.setEnabled(ready and self._preview_valid and self.edit.has_effect)
        self.progress.setVisible(self.is_busy)
        self.retry_button.setVisible(bool(self._error_code) and self._mask is None and not self.is_busy)
        self.cancel_button.setEnabled(not self._closing)

    def start_selection(self) -> None:
        if self.is_busy or self._closing:
            return
        self._start_timer.stop()
        self._timer.stop()
        self._mask = self._preview_mask = self._preview_result = None
        self._preview_valid = False
        self._error_code = ""
        self.status.setText(self._t("detecting"))
        self.job.start(self._image)
        self._update_controls()

    def _selection_finished(self, mask: object, error: str, cleanup_failed: bool) -> None:
        self.cleanup_label.setVisible(cleanup_failed)
        if self._closing:
            super().reject()
            return
        if not error:
            try:
                self._install_selection(mask)
                return
            except (ValueError, TypeError, OSError, MemoryError):
                error = "NO_SUBJECT"
        self._error_code = error
        self.status.setText(self._t(error))
        self._update_controls()

    def _install_selection(self, mask: Image.Image) -> None:
        self._start_timer.stop()
        validate_subject_mask(mask, self._image.size)
        if mask.getextrema()[0] == mask.getextrema()[1]:
            raise ValueError("A uniform mask is not a usable subject selection.")
        self._mask = mask.copy()
        self._preview_mask = mask.resize(self._preview_source.size, Image.Resampling.LANCZOS)
        self._error_code = ""
        self._render_preview()

    def _mode_changed(self) -> None:
        with QSignalBlocker(self.strength):
            self.strength.setValue(_DEFAULT_STRENGTH[self.edit.mode])
        self._changed()

    def reset_settings(self) -> None:
        for slider, value in ((self.strength, _DEFAULT_STRENGTH[self.edit.mode]), (self.feather, 0), (self.padding, 12)):
            with QSignalBlocker(slider):
                slider.setValue(value)
        self._changed()

    def _changed(self, *_args) -> None:
        if self.is_busy or self._mask is None or self._closing:
            return
        self._preview_valid = False
        self._timer.start(100)
        self._update_controls()

    def _render_preview(self) -> None:
        self._timer.stop()
        if self.is_busy or self._mask is None or self._closing:
            return
        try:
            edit = self.edit
            self._preview_result = render_subject(self._preview_source, self._preview_mask, edit)
            self._result_size = self._image.size
            if edit.mode == "crop":
                mask = effective_subject_mask(self._mask, edit.feather)
                alpha = self._image.getchannel("A") if self._image.mode == "RGBA" else None
                left, top, right, bottom = subject_bounds(mask, edit.padding, alpha)
                self._result_size = (right - left, bottom - top)
            self._preview_valid = True
            self._show_preview()
        except (ValueError, OSError, MemoryError):
            self._preview_valid = False
            self.status.setText(self._t("edit_error"))
        self._update_controls()

    def _show_preview(self) -> None:
        if self._mask is None or self.is_busy:
            return
        before = self.compare_button.isChecked()
        self.compare_button.setText(self._t("after" if before else "before"))
        if before:
            self.canvas.set_image(self._preview_source, self._image.size)
            self.status.setText(self._t("before_status"))
        elif self.selection_check.isChecked():
            mask = effective_subject_mask(self._preview_mask, self.edit.feather)
            self.canvas.set_image(selection_overlay(self._preview_source, mask), self._image.size)
            self.status.setText(self._t("selected_status"))
        elif self._preview_result is not None:
            self.canvas.set_image(self._preview_result, self._result_size)
            self.status.setText(self._t("preview_status", width=self._result_size[0], height=self._result_size[1])
                                if self.edit.has_effect else self._t("no_effect"))

    def accept(self) -> None:
        if self.is_busy or self._mask is None or self._closing or not self.edit.has_effect:
            return
        self._timer.stop()
        self._worker = _SubjectRenderThread(self._image, self._mask, self.edit, self)
        self._worker.finished.connect(self._render_finished)
        self.status.setText(self._t("rendering"))
        self._update_controls()
        self._worker.start()

    def _render_finished(self) -> None:
        worker = self._worker
        if worker is None:
            return
        worker.wait()
        self._worker = None
        result, failed = worker.result_image, worker.failed
        worker.deleteLater()
        if self._closing:
            super().reject()
            return
        if result is not None and not failed:
            self.result_image = result
            super().accept()
            return
        self.status.setText(self._t("edit_error"))
        self._update_controls()

    def reject(self) -> None:
        self._start_timer.stop()
        self._timer.stop()
        self._closing = True
        if self.job.is_running:
            self.job.cancel()
        elif self._worker is not None:
            self._worker.requestInterruption()
        else:
            super().reject()
            return
        self.status.setText(self._t("cancelling"))
        self._update_controls()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.reject()
        if self.is_busy:
            event.ignore()
        else:
            event.accept()
