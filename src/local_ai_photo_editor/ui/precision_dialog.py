"""Opt-in precision workspace built on the existing cancellable subject dialog."""
from __future__ import annotations

from PIL import Image
from PySide6.QtCore import QSignalBlocker, QThread
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from ..core.local_adjustments import DEFAULT_STRENGTH, LOCAL_MODES, LocalEdit, render_local
from ..core.mask import MaskStroke
from ..core.recipes import RenderCancelled
from ..core.selection import MAX_SELECTION_ACTIONS, SelectionHistory, render_selection
from ..core.subject import effective_subject_mask, selection_overlay, subject_bounds
from .detail_strings import STRINGS, text
from .navigation import NavigationCanvas, ViewControls
from .subject_dialog import SubjectDialog


class _SelectionRenderThread(QThread):
    def __init__(self, image, mask, actions, edit, parent):
        super().__init__(parent)
        self.image, self.mask, self.actions, self.edit = image, mask, actions, edit
        self.result_image = None
        self.failed = False

    def run(self) -> None:
        try:
            selection = render_selection(self.mask, self.actions, cancelled=self.isInterruptionRequested)
            self.result_image = render_local(self.image, selection, self.edit,
                                             cancelled=self.isInterruptionRequested)
        except RenderCancelled:
            pass
        except Exception:
            self.failed = True


class PrecisionDialog(SubjectDialog):
    """Pending selection edits never alter the original mask or accepted photo."""
    def __init__(self, image: Image.Image, language: str = "de", mode: str = "light",
                 parent: QWidget | None = None, *, manual: bool = False,
                 start_immediately: bool = True) -> None:
        LocalEdit(mode=mode)
        self.selection_history = SelectionHistory()
        self._working_preview_mask: Image.Image | None = None
        self._manual = manual
        # The base validates its initial operation against the original modes.
        initial = mode if mode in LOCAL_MODES[:6] else "light"
        super().__init__(image, language, initial, parent, start_immediately=False)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(mode))
        if manual:
            self.start_manual_selection()
        elif start_immediately:
            self._start_timer.start(0)

    def _t(self, key: str, **values: object) -> str:
        if key == "intro" and self._manual:
            key = "manual_intro"
        if key in STRINGS[self.language]:
            return text(self.language, key, **values)
        return super()._t(key, **values)

    @property
    def edit(self) -> LocalEdit:
        return LocalEdit(str(self.mode_combo.currentData()), self.strength.value(),
                         self.feather.value(), self.padding.value())

    def _build(self, mode: str) -> None:
        super()._build(mode)
        old_canvas = self.canvas
        self.canvas = NavigationCanvas()
        self.canvas.set_language(self.language)
        self.canvas.setMinimumSize(340, 290)
        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(self.canvas, 1)
        self.navigation = ViewControls(self.canvas, self.language)
        preview_layout.addWidget(self.navigation)
        content = self.layout().itemAt(1).layout()
        content.replaceWidget(old_canvas, preview)
        old_canvas.setParent(None)
        old_canvas.deleteLater()
        for extra in LOCAL_MODES[6:]:
            self.mode_combo.addItem(self._t(extra), extra)

        panel = self.panel.layout()
        self.brush_button = self._button("brush_toggle", self._toggle_brush)
        self.brush_button.setCheckable(True)
        panel.insertWidget(3, self.brush_button)
        self.brush_settings = QWidget()
        settings = QVBoxLayout(self.brush_settings)
        settings.setContentsMargins(0, 0, 0, 0)
        settings.addWidget(self._label("brush_hint"))
        self.brush_mode = QComboBox()
        self.brush_mode.addItem(self._t("brush_add"), "restore")
        self.brush_mode.addItem(self._t("brush_remove"), "erase")
        self.brush_mode.setAccessibleName(self._t("brush_toggle"))
        self.brush_mode.currentIndexChanged.connect(self._brush_changed)
        settings.addWidget(self.brush_mode)
        _, self.brush_size, self.brush_size_value = self._slider(settings, "brush_size", 200, 40)
        self.brush_size.setMinimum(5)
        _, self.brush_softness, self.brush_softness_value = self._slider(settings, "brush_softness", 100, 35)
        self.brush_size.valueChanged.connect(self._brush_changed)
        self.brush_softness.valueChanged.connect(self._brush_changed)
        history_row = QHBoxLayout()
        self.selection_undo = self._button("selection_undo", self.undo_selection)
        self.selection_redo = self._button("selection_redo", self.redo_selection)
        history_row.addWidget(self.selection_undo)
        history_row.addWidget(self.selection_redo)
        settings.addLayout(history_row)
        self.invert_button = self._button("selection_invert", lambda: self.push_selection("invert"))
        self.invert_button.setToolTip(self._t("invert_hint"))
        self.clear_button = self._button("selection_clear", lambda: self.push_selection("clear"))
        self.restore_button = self._button("selection_reset", lambda: self.push_selection("reset"))
        for button in (self.invert_button, self.clear_button, self.restore_button):
            settings.addWidget(button)
        panel.insertWidget(4, self.brush_settings)
        self.brush_settings.hide()
        self.canvas.brush_stroke_finished.connect(self._stroke_finished)
        self.manual_button = self._button("manual_fallback", self.start_manual_selection)
        self.layout().itemAt(self.layout().count() - 1).layout().insertWidget(0, self.manual_button)
        self._undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self._redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self._undo_shortcut.activated.connect(self.undo_selection)
        self._redo_shortcut.activated.connect(self.redo_selection)
        self._brush_changed()

    def _update_controls(self) -> None:
        super()._update_controls()
        if not hasattr(self, "brush_button"):
            return
        ready = self._mask is not None and not self.is_busy and not self._closing
        painting = self.brush_button.isChecked()
        self.brush_button.setText(self._t("brush_done" if painting else "brush_toggle"))
        self.brush_settings.setVisible(painting)
        self.canvas.setEnabled(not self.is_busy and not self._closing)
        self.canvas.set_brush_enabled(ready and painting)
        self.navigation.setEnabled(ready)
        self.compare_button.setEnabled(ready and not painting)
        self.selection_check.setEnabled(ready and not painting)
        self.selection_undo.setEnabled(ready and self.selection_history.can_undo)
        self.selection_redo.setEnabled(ready and self.selection_history.can_redo)
        self._undo_shortcut.setEnabled(ready and self.selection_history.can_undo)
        self._redo_shortcut.setEnabled(ready and self.selection_history.can_redo)
        self.apply_button.setEnabled(ready and not painting and self._preview_valid and self.edit.has_effect)
        self.manual_button.setVisible(self._mask is None and not self.is_busy and not self._closing)
        self._brush_changed()

    def _brush_changed(self, *_args) -> None:
        if not hasattr(self, "brush_softness"):
            return
        self.canvas.set_brush(str(self.brush_mode.currentData()), self.brush_size.value() / 1000)
        self.brush_size_value.setText(f"{self.brush_size.value() / 10:g} %")
        self.brush_softness_value.setText(f"{self.brush_softness.value()} %")

    def _toggle_brush(self) -> None:
        if self.is_busy or self._mask is None or self._closing:
            self.brush_button.setChecked(False)
            return
        with QSignalBlocker(self.compare_button):
            self.compare_button.setChecked(False)
        with QSignalBlocker(self.selection_check):
            self.selection_check.setChecked(self.brush_button.isChecked())
        self.navigation.pan_button.setChecked(False)
        self._update_controls()
        self._show_preview()

    def _stroke_finished(self, points: object) -> None:
        if not self.brush_button.isChecked() or self.is_busy or self._closing:
            return
        stroke = MaskStroke(tuple(points), str(self.brush_mode.currentData()),
                            self.brush_size.value() / 1000, self.brush_softness.value() / 100)
        self.push_selection(stroke)

    def push_selection(self, action) -> None:
        if self._mask is None or self.is_busy or self._closing:
            return
        try:
            actions = (*self.selection_history.actions, action)
            # Validate and rasterize before mutating history or clearing redo.
            rendered = render_selection(self._preview_mask, actions)
            self.selection_history.push(action)
            self._working_preview_mask = rendered
            self._render_preview()
        except (ValueError, TypeError, OSError, MemoryError):
            self._preview_valid = False
            self.status.setText(self._t("selection_limit" if len(self.selection_history.actions) >= MAX_SELECTION_ACTIONS else "edit_error"))
            self._update_controls()

    def undo_selection(self) -> None:
        if self.is_busy or self._closing or not self.selection_history.can_undo:
            return
        try:
            rendered = render_selection(self._preview_mask, self.selection_history.actions[:-1])
            self.selection_history.undo()
            self._working_preview_mask = rendered
            self._render_preview()
        except (ValueError, OSError, MemoryError):
            self._preview_valid = False
            self.status.setText(self._t("edit_error"))
            self._update_controls()

    def redo_selection(self) -> None:
        if self.is_busy or self._closing or not self.selection_history.can_redo:
            return
        self.selection_history.redo()
        try:
            self._working_preview_mask = render_selection(self._preview_mask, self.selection_history.actions)
        except (ValueError, OSError, MemoryError):
            self.selection_history.undo()
            self._preview_valid = False
            self.status.setText(self._t("edit_error"))
            self._update_controls()
            return
        self._render_preview()

    def start_manual_selection(self) -> None:
        if self.is_busy or self._closing or self._mask is not None:
            return
        self._start_timer.stop()
        self._manual = True
        self.selection_history = SelectionHistory()
        self._mask = Image.new("L", self._image.size)
        self._preview_mask = Image.new("L", self._preview_source.size)
        self._working_preview_mask = self._preview_mask.copy()
        self._error_code = ""
        self.layout().itemAt(0).widget().setText(self._t("manual_intro"))
        self.brush_button.setChecked(True)
        self._toggle_brush()
        self._render_preview()

    def _install_selection(self, mask: Image.Image) -> None:
        # Do not relax the inference adapter's rejection of uniform masks.
        self.selection_history = SelectionHistory()
        self._working_preview_mask = None
        super()._install_selection(mask)

    def _mode_changed(self) -> None:
        with QSignalBlocker(self.strength):
            self.strength.setValue(DEFAULT_STRENGTH[self.edit.mode])
        self._changed()

    def reset_settings(self) -> None:
        for slider, value in ((self.strength, DEFAULT_STRENGTH[self.edit.mode]), (self.feather, 0), (self.padding, 12)):
            with QSignalBlocker(slider):
                slider.setValue(value)
        self._changed()

    def _render_preview(self) -> None:
        self._timer.stop()
        if self.is_busy or self._mask is None or self._closing:
            return
        if self.canvas._brush_points is not None:
            self._timer.start(100)
            return
        try:
            if self._working_preview_mask is None:
                self._working_preview_mask = render_selection(self._preview_mask, self.selection_history.actions)
            selection = self._working_preview_mask
            if selection.getextrema()[1] == 0:
                self._preview_result = self._preview_source
                self._preview_valid = False
                self._result_size = self._image.size
            else:
                self._preview_result = render_local(self._preview_source, selection, self.edit)
                self._result_size = self._image.size
                if self.edit.mode == "crop":
                    # The corrected thumbnail is not a pixel-exact full-size mask.
                    # Display an explicit crop-preview label, not exact dimensions.
                    sx, sy = self._image.width / self._preview_source.width, self._image.height / self._preview_source.height
                    self._result_size = (max(1, round(self._preview_result.width * sx)),
                                         max(1, round(self._preview_result.height * sy)))
                self._preview_valid = True
            self._show_preview()
        except (ValueError, OSError, MemoryError):
            self._preview_valid = False
            self.status.setText(self._t("edit_error"))
        self._update_controls()

    def _show_preview(self) -> None:
        if self._mask is None or self.is_busy or self._working_preview_mask is None:
            return
        painting = self.brush_button.isChecked()
        before = self.compare_button.isChecked() and not painting
        self.compare_button.setText(self._t("after" if before else "before"))
        if before:
            self.canvas.set_image(self._preview_source, self._image.size)
            self.status.setText(self._t("before_status"))
        elif painting or self.selection_check.isChecked():
            selection = self._working_preview_mask if painting else effective_subject_mask(self._working_preview_mask, self.edit.feather)
            self.canvas.set_image(selection_overlay(self._preview_source, selection), self._image.size)
            self.status.setText(self._t("brush_status" if painting else "selected_status"))
        elif self._preview_result is not None:
            self.canvas.set_image(self._preview_result, self._result_size)
            self.status.setText(self._t("crop_preview") if self.edit.mode == "crop" else
                                self._t("preview_status", width=self._result_size[0], height=self._result_size[1]))
        if self._working_preview_mask.getextrema()[1] == 0:
            self.status.setText(self._t("empty_selection"))

    def accept(self) -> None:
        if (self.is_busy or self._mask is None or self._closing or not self.edit.has_effect
                or self.brush_button.isChecked() or self.canvas._brush_points is not None):
            return
        self._render_preview()
        if not self._preview_valid:
            return
        self._timer.stop()
        self._worker = _SelectionRenderThread(self._image, self._mask, self.selection_history.actions, self.edit, self)
        self._worker.finished.connect(self._render_finished)
        self.status.setText(self._t("rendering"))
        self._update_controls()
        self._worker.start()
