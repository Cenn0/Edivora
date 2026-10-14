"""Task-oriented previews with one explicit, reversible full-size commit."""
from __future__ import annotations

from dataclasses import replace

from PIL import Image
from PySide6.QtCore import QSignalBlocker, QThread, QTimer, Qt
from PySide6.QtGui import QColor, QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QScrollArea, QSlider, QTabWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from ..core.editing import load_image
from ..core.recipes import (ASPECTS, LOOKS, EditRecipe, RenderCancelled, auto_levels,
                            output_size, render_recipe)
from .theme import stylesheet
from .canvas import PhotoCanvas
from .editing_strings import text

_SECTIONS = ("light", "look", "shape", "background")


class _RenderThread(QThread):
    """Owns no widgets; input images are immutable for this job's lifetime."""
    def __init__(self, image: Image.Image, recipe: EditRecipe,
                 background: Image.Image | None, levels: tuple[int, int], parent: QWidget):
        super().__init__(parent)
        self.image, self.recipe, self.background, self.levels = image, recipe, background, levels
        self.result_image: Image.Image | None = None
        self.error: Exception | None = None

    def run(self) -> None:
        try:
            self.result_image = render_recipe(
                self.image, self.recipe, background_image=self.background,
                levels=self.levels, cancelled=self.isInterruptionRequested,
            )
        except RenderCancelled:
            pass
        except Exception as exc:
            self.error = exc


class EditingDialog(QDialog):
    """A dialog-local recipe; Cancel never alters the accepted document."""
    def __init__(self, image: Image.Image, language: str = "de",
                 section: str = "light", parent: QWidget | None = None):
        super().__init__(parent)
        if section not in _SECTIONS:
            raise ValueError("Unknown editing section.")
        self.language = language
        self._image = image.copy()
        self._preview_source = image.copy()
        self._preview_source.thumbnail((960, 960), Image.Resampling.LANCZOS)
        self._levels = auto_levels(image)
        self._background_image: Image.Image | None = None
        self._background_preview: Image.Image | None = None
        self._background_color = (255, 255, 255)
        self._quarter_turns = 0
        self._preview_result: Image.Image | None = None
        self._preview_valid = True
        self._rendered_recipe = EditRecipe()
        self._worker: _RenderThread | None = None
        self._closing = False
        self._updating = False
        self.result_image: Image.Image | None = None
        self.controls: dict[str, QSlider] = {}
        self.values: dict[str, QLabel] = {}
        self.combos: dict[str, QComboBox] = {}
        self.checks: dict[str, QCheckBox] = {}
        self._has_alpha = image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._render_preview)
        self.setWindowTitle(self._t("dialog_title"))
        self.setMinimumSize(800, 560)
        self.resize(1080, 720)
        self.setStyleSheet(stylesheet())
        self._build()
        self.tabs.setCurrentIndex(_SECTIONS.index(section))
        self._refresh_controls()
        self._render_preview()

    def _t(self, key: str, **values: object) -> str:
        return text(self.language, key, **values)

    @property
    def is_rendering(self) -> bool:
        return self._worker is not None

    @property
    def recipe(self) -> EditRecipe:
        values = {key: control.value() for key, control in self.controls.items()}
        values.update({key: str(control.currentData()) for key, control in self.combos.items()})
        values.update({key: control.isChecked() for key, control in self.checks.items()})
        return EditRecipe(**values, quarter_turns=self._quarter_turns,
                          background_color=self._background_color)

    def _label(self, key: str) -> QLabel:
        label = QLabel(self._t(key))
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        return label

    def _button(self, key: str, callback) -> QPushButton:
        button = QPushButton(self._t(key))
        button.clicked.connect(callback)
        return button

    def _page(self, key: str) -> QVBoxLayout:
        page = QWidget()
        page.setObjectName("editingPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self._label(f"{key}_hint"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, self._t(f"tab_{key}"))
        return layout

    def _slider(self, layout: QVBoxLayout, key: str, low: int = 0, high: int = 100,
                default: int = 0) -> None:
        header = QHBoxLayout()
        label = self._label(key)
        header.addWidget(label, 1)
        value = QLabel()
        value.setObjectName("sliderValue")
        header.addWidget(value)
        reset = QToolButton()
        reset.setText("↺")
        reset.setAccessibleName(self._t("reset_control", name=self._t(key)))
        reset.setToolTip(reset.accessibleName())
        header.addWidget(reset)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(default)
        slider.setPageStep(10)
        slider.setAccessibleName(self._t(key))
        slider.setToolTip(self._t(key + "_hint"))
        label.setBuddy(slider)
        label.setToolTip(slider.toolTip())
        self.controls[key], self.values[key] = slider, value
        slider.valueChanged.connect(self._changed)
        reset.clicked.connect(lambda checked=False, s=slider, v=default: s.setValue(v))
        layout.addLayout(header)
        layout.addWidget(slider)

    def _combo(self, layout: QVBoxLayout, key: str, choices) -> QComboBox:
        label = self._label(key + "_label")
        combo = QComboBox()
        combo.setAccessibleName(self._t(key + "_label"))
        for choice in choices:
            combo.addItem(self._t(f"{key}_{choice}"), choice)
        label.setBuddy(combo)
        self.combos[key] = combo
        combo.currentIndexChanged.connect(self._changed)
        layout.addWidget(label)
        layout.addWidget(combo)
        return combo

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.addWidget(self._label("safe_hint"))
        content = QHBoxLayout()
        preview = QVBoxLayout()
        self.canvas = PhotoCanvas()
        self.canvas.setMinimumSize(340, 280)
        self.canvas.set_language(self.language)
        preview.addWidget(self.canvas, 1)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        preview.addWidget(self.status)
        self.compare_button = self._button("before", self._show_preview)
        self.compare_button.setCheckable(True)
        self.compare_button.setToolTip(self._t("before_hint"))
        preview.addWidget(self.compare_button)
        content.addLayout(preview, 1)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(365)
        self.tabs.setMaximumWidth(420)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setAccessibleName(self._t("tools_title"))
        content.addWidget(self.tabs)
        outer.addLayout(content, 1)

        light = self._page("light")
        self.auto_button = self._button("auto_button", self.suggest_improvement)
        self.auto_button.setToolTip(self._t("auto_hint"))
        light.addWidget(self.auto_button)
        for key in ("exposure", "shadows", "highlights", "warmth", "saturation", "contrast", "sharpness", "automatic"):
            self._slider(light, key, -100 if key in {"exposure", "warmth", "saturation", "contrast"} else 0)
        light.addStretch()
        look = self._page("look")
        self._combo(look, "look", LOOKS)
        self._slider(look, "look_strength", default=100)
        self._slider(look, "vignette")
        look.addStretch()
        shape = self._page("shape")
        self._combo(shape, "aspect", ASPECTS)
        self._slider(shape, "focus_x", default=50)
        self._slider(shape, "focus_y", default=50)
        for key in ("mirror", "flip"):
            control = QCheckBox(self._t(key))
            control.toggled.connect(self._changed)
            shape.addWidget(control)
            self.checks[key] = control
        rotations = QHBoxLayout()
        rotations.addWidget(self._button("rotate_left", lambda: self.rotate(-1)))
        rotations.addWidget(self._button("rotate_right", lambda: self.rotate(1)))
        shape.addLayout(rotations)
        shape.addStretch()
        background = self._page("background")
        background.addWidget(self._label("background_ready" if self._has_alpha else "background_locked"))
        self._combo(background, "background", ("keep", "solid", "photo"))
        self.color_button = self._button("choose_color", self.choose_color)
        background.addWidget(self.color_button)
        self.photo_button = self._button("choose_photo", self.choose_background_photo)
        background.addWidget(self.photo_button)
        self.photo_label = self._label("photo_needed")
        background.addWidget(self.photo_label)
        self._slider(background, "background_blur")
        background.addWidget(self._label("background_note"))
        background.addStretch()

        footer = QHBoxLayout()
        self.reset_section_button = self._button("reset_section", self.reset_section)
        self.reset_all_button = self._button("reset_all", self.reset_all)
        footer.addWidget(self.reset_section_button)
        footer.addWidget(self.reset_all_button)
        footer.addStretch()
        self.cancel_button = self._button("cancel", self.reject)
        self.apply_button = self._button("apply", self.accept)
        self.apply_button.setObjectName("primary")
        self.apply_button.setDefault(True)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.apply_button)
        outer.addLayout(footer)

    def _refresh_controls(self) -> None:
        for key, control in self.controls.items():
            value = control.value()
            self.values[key].setText(f"{value:+d} %" if control.minimum() < 0 and value else f"{value} %")
        self.controls["look_strength"].setEnabled(self.combos["look"].currentData() != "none")
        cropped = self.combos["aspect"].currentData() != "original"
        for key in ("focus_x", "focus_y"):
            self.controls[key].setEnabled(cropped)
        self.combos["background"].setEnabled(self._has_alpha)
        mode = self.combos["background"].currentData()
        self.color_button.setEnabled(self._has_alpha and mode == "solid")
        self.photo_button.setEnabled(self._has_alpha and mode == "photo")
        self.photo_label.setVisible(mode == "photo")
        self.controls["background_blur"].setEnabled(self._has_alpha and mode == "photo")
        rgb = ", ".join(str(v) for v in self._background_color)
        self.color_button.setText(self._t("choose_color") + f" ({rgb})")
        ready = mode != "photo" or self._background_image is not None
        self.apply_button.setEnabled(not self.is_rendering and self.recipe.has_effect and ready and self._preview_valid)

    def _changed(self, *_args) -> None:
        if self._updating or self.is_rendering:
            return
        self._preview_valid = True
        self._refresh_controls()
        self._timer.start(100)

    def set_recipe(self, recipe: EditRecipe) -> None:
        if self.is_rendering:
            return
        self._updating = True
        try:
            for key, control in self.controls.items():
                with QSignalBlocker(control):
                    control.setValue(getattr(recipe, key))
            for key, control in self.combos.items():
                with QSignalBlocker(control):
                    control.setCurrentIndex(control.findData(getattr(recipe, key)))
            for key, control in self.checks.items():
                with QSignalBlocker(control):
                    control.setChecked(getattr(recipe, key))
            self._quarter_turns, self._background_color = recipe.quarter_turns, recipe.background_color
        finally:
            self._updating = False
        self._changed()

    def suggest_improvement(self) -> None:
        self.set_recipe(replace(self.recipe, automatic=60, shadows=15, highlights=10))

    def rotate(self, direction: int) -> None:
        self.set_recipe(replace(self.recipe, quarter_turns=(self._quarter_turns + direction) % 4))

    def reset_section(self) -> None:
        section = _SECTIONS[self.tabs.currentIndex()]
        self.set_recipe(self.recipe.reset_section(section))

    def reset_all(self) -> None:
        self.set_recipe(EditRecipe())

    def choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(*self._background_color), self, self._t("color_title"))
        if color.isValid():
            self._background_color = (color.red(), color.green(), color.blue())
            self._changed()

    def choose_background_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self._t("photo_title"), "", self._t("photo_filter"))
        if not path:
            return
        try:
            self.set_background_image(load_image(path))
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("image_error", exc)

    def set_background_image(self, image: Image.Image) -> None:
        if self.is_rendering:
            return
        from ..core.editing import _normalise_image
        background = _normalise_image(image)
        preview = background.copy()
        preview.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        self._background_image, self._background_preview = background, preview
        self.photo_label.setText(self._t("photo_loaded", width=background.width, height=background.height))
        self._changed()

    def _render_preview(self) -> None:
        if self.is_rendering:
            return
        self._timer.stop()
        try:
            output_size(self._image.size, self.recipe)
            if self.recipe.background == "photo" and self._background_preview is None:
                self.status.setText(self._t("photo_needed"))
                self._preview_valid = False
                self._refresh_controls()
                return
            self._preview_result = render_recipe(self._preview_source, self.recipe,
                                                 background_image=self._background_preview, levels=self._levels)
            self._preview_valid = True
            self._rendered_recipe = self.recipe
            self._show_preview()
        except (ValueError, OSError, MemoryError) as exc:
            self._preview_valid = False
            self.status.setText(self._t("error"))
            self.status.setToolTip(str(exc))
        self._refresh_controls()

    def _show_preview(self) -> None:
        before = self.compare_button.isChecked()
        self.compare_button.setText(self._t("after" if before else "before"))
        image = self._preview_source if before else self._preview_result
        if image is not None:
            size = self._image.size if before else output_size(self._image.size, self._rendered_recipe)
            self.canvas.set_image(image, size)
            self.status.setText(self._t("before_status") if before else
                                self._t("preview", width=size[0], height=size[1]) if self._rendered_recipe.has_effect
                                else self._t("no_changes"))

    def _show_error(self, key: str, exc: Exception) -> None:
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle(self._t("error_title"))
        message.setText(self._t(key))
        message.setDetailedText(str(exc))
        message.exec()

    def accept(self) -> None:
        if self.is_rendering or not self.recipe.has_effect:
            return
        recipe = self.recipe
        if recipe.background == "photo" and self._background_image is None:
            self.status.setText(self._t("photo_needed"))
            return
        self._timer.stop()
        self._worker = _RenderThread(self._image, recipe, self._background_image, self._levels, self)
        self._worker.finished.connect(self._render_finished)
        self.tabs.setEnabled(False)
        for control in (self.apply_button, self.compare_button, self.reset_all_button, self.reset_section_button):
            control.setEnabled(False)
        self.status.setText(self._t("rendering"))
        self._worker.start()

    def _render_finished(self) -> None:
        worker = self._worker
        if worker is None:
            return
        worker.wait()
        self._worker = None
        result, error = worker.result_image, worker.error
        worker.deleteLater()
        if self._closing:
            super().reject()
            return
        if error is None and result is not None:
            self.result_image = result
            super().accept()
            return
        self.tabs.setEnabled(True)
        for control in (self.compare_button, self.reset_all_button, self.reset_section_button):
            control.setEnabled(True)
        self._refresh_controls()
        self.status.setText(self._t("error"))
        if error is not None:
            self._show_error("error", error)

    def reject(self) -> None:
        self._timer.stop()
        if self._worker is not None:
            self._closing = True
            self._worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.status.setText(self._t("cancelling"))
            return
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_rendering:
            self.reject()
            event.ignore()
        else:
            self._timer.stop()
            super().closeEvent(event)
