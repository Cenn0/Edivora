"""Real-frame comparison and explicit acceptance of local video improvements."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QScrollArea, QSlider, QSizePolicy, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from ..ai.restoration import model_available
from ..core.media_project import MediaClip
from ..core.video_adjustments import PRESETS, VideoAdjustments
from ..core.video_job import VideoJob, install_restored_clip, validate_destination
from .canvas import PhotoCanvas
from .icons import IconButton, icon
from .responsive import ElideLabel, VerticalScrollArea, WrappedCheckBox, fit_initial_window
from .theme import stylesheet
from .video_jobs import RestorationRunner
from .video_strings import text


class VideoEnhancementDialog(QDialog):
    def __init__(self, clip: MediaClip, at_ms: int, language: str,
                 protected: tuple[Path, ...], parent=None) -> None:
        super().__init__(parent)
        self.clip = clip.validated("video")
        self.at_ms = min(max(clip.start_ms, at_ms), clip.end_ms - 1)
        self.language, self.protected = language, protected
        self.result_clip: MediaClip | None = None
        self._before = self._after = None
        self._preview_key = None
        self._job_key = None
        self._mode = "preview"
        self._destination: Path | None = None
        self._closing = False
        self._loading_controls = True
        self.runner = RestorationRunner(self)
        self.runner.finished.connect(self._completed)
        self.runner.progress.connect(lambda value: self.progress.setValue(value))
        self.setWindowTitle(self._t("title"))
        self.setWindowIcon(icon("adjust"))
        self.setStyleSheet(stylesheet())
        self.setMinimumSize(640, 480)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(self._label("intro", True))
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)
        stage = QWidget()
        stage.setMinimumWidth(220)
        view = QVBoxLayout(stage)
        view.setContentsMargins(0, 0, 6, 0)
        self.canvas = PhotoCanvas()
        self.canvas.setMinimumSize(160, 110)
        self.canvas.set_language(language)
        view.addWidget(self.canvas, 1)
        self.compare = IconButton(self._t("before"), icon_name="compare")
        self.compare.setCheckable(True)
        self.compare.toggled.connect(self._show_comparison)
        self.compare.setEnabled(False)
        view.addWidget(self.compare)
        view.addWidget(self._label("preview_hint", True))
        split.addWidget(stage)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("inspectorTabs")
        self.tabs.setMinimumWidth(295)
        self.tabs.setMaximumWidth(450)
        split.addWidget(self.tabs)
        split.setStretchFactor(0, 1)
        split.setSizes([600, 330])
        corrections = self._page("corrections")
        corrections.addWidget(self._label("presets"))
        self.presets = QComboBox()
        self.presets.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.presets.setMinimumContentsLength(10)
        self.presets.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for key in PRESETS:
            self.presets.addItem(self._t(key), key)
        self.presets.setAccessibleName(self._t("presets"))
        self.presets.currentIndexChanged.connect(self._preset)
        corrections.addWidget(self.presets)
        self.sliders: dict[str, QSlider] = {}
        for name, initial in clip.video_adjustments.to_dict().items():
            row = QHBoxLayout()
            row.addWidget(self._label(name))
            value = QLabel(str(initial))
            row.addStretch()
            row.addWidget(value)
            corrections.addLayout(row)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0 if name in ("denoise", "sharpness") else -100, 100)
            slider.setValue(initial)
            slider.setAccessibleName(self._t(name))
            slider.valueChanged.connect(lambda number, label=value: label.setText(str(number)))
            slider.valueChanged.connect(self._changed)
            self.sliders[name] = slider
            corrections.addWidget(slider)
        self.reset = IconButton(self._t("reset"), icon_name="reset")
        self.reset.clicked.connect(lambda: self._set_adjustments(VideoAdjustments()))
        corrections.addWidget(self.reset)
        corrections.addWidget(self._label("limits", True))
        corrections.addStretch()
        neural = self._page("neural")
        self.ai = WrappedCheckBox(self._t("ai"))
        self.ai.setEnabled(model_available())
        self.ai.toggled.connect(self._changed)
        neural.addWidget(self.ai)
        neural.addWidget(self._label("ai_hint", True))
        neural.addWidget(self._label("strength"))
        self.strength = QSlider(Qt.Orientation.Horizontal)
        self.strength.setRange(1, 100)
        self.strength.setValue(60)
        self.strength.setAccessibleName(self._t("strength"))
        self.strength.valueChanged.connect(self._changed)
        neural.addWidget(self.strength)
        neural.addWidget(self._label("ai_limit", True))
        if not self.ai.isEnabled():
            neural.addWidget(self._label("ai_missing", True))
        neural.addStretch()
        footer = QHBoxLayout()
        self.preview_button = IconButton(self._t("preview"), icon_name="play")
        self.preview_button.clicked.connect(self.calculate_preview)
        self.apply_button = IconButton(self._t("apply"), icon_name="check")
        self.apply_button.setObjectName("primary")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply)
        self.cancel_button = IconButton(self._t("cancel"), icon_name="close")
        self.cancel_button.clicked.connect(self._cancel)
        for button in (self.preview_button, self.apply_button, self.cancel_button):
            button.setFitToWidth()
            footer.addWidget(button)
        self.compare.setFitToWidth()
        self.reset.setFitToWidth()
        root.addLayout(footer)
        self.status = ElideLabel()
        root.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.hide()
        root.addWidget(self.progress)
        self._loading_controls = False
        self._changed()
        fit_initial_window(self, (1080, 740))
        QTimer.singleShot(0, self.calculate_preview)

    def _t(self, key: str) -> str:
        return text(self.language, key)

    def _label(self, key: str, wrap: bool = True) -> QLabel:
        label = QLabel(self._t(key))
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(wrap)
        return label

    def _page(self, title: str) -> QVBoxLayout:
        scroll = VerticalScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        page.setObjectName("editingPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, self._t(title))
        return layout

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "preview_button"):
            # All three actions stay visible even at the smallest supported size.
            self.preview_button.setCompact(self.width() < 880)
            self.cancel_button.setCompact(self.width() < 740)

    def _adjustments(self) -> VideoAdjustments:
        return VideoAdjustments(**{name: slider.value() for name, slider in self.sliders.items()})

    def _key(self) -> tuple:
        return self._adjustments(), self.strength.value() if self.ai.isChecked() else 0

    def _changed(self, *_args) -> None:
        if self._loading_controls:
            return
        self._preview_key = None
        self.apply_button.setEnabled(False)
        self.apply_button.setText(self._t("create" if self.ai.isChecked() else "apply"))
        self.strength.setEnabled(self.ai.isChecked())
        self.status.setText(self._t("preview_dirty"))

    def _set_adjustments(self, value: VideoAdjustments) -> None:
        for name, number in value.to_dict().items():
            self.sliders[name].setValue(number)
        self._changed()

    def _preset(self) -> None:
        self._set_adjustments(PRESETS[self.presets.currentData()])

    def _request(self, mode: str) -> VideoJob:
        return VideoJob(self.clip.source, self.clip.start_ms, self.clip.end_ms,
                        self.at_ms, *self._key(), mode).validated()

    def _set_busy(self, busy: bool) -> None:
        self.tabs.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.apply_button.setEnabled(not busy and self._preview_key == self._key())
        self.progress.setVisible(busy)
        if busy:
            self.status.setText(self._t("working"))

    def calculate_preview(self) -> None:
        if self.runner.busy or self._closing:
            return
        try:
            self._mode, self._job_key = "preview", self._key()
            self.runner.start(self._request("preview"))
            self.progress.setRange(0, 0)
            self._set_busy(True)
        except (OSError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def _show_comparison(self) -> None:
        picture = self._before if self.compare.isChecked() else self._after
        if picture is not None:
            self.canvas.set_image(picture, picture.size)
        self.compare.setText(self._t("before"))

    def _completed(self, response: dict, folder: Path) -> None:
        try:
            if self._closing:
                return
            if response.get("cancelled"):
                self.status.setText(self._t("cancelled"))
                return
            if response.get("ok") is not True:
                raise ValueError(response.get("message") or self._t("error"))
            if self._mode == "preview":
                pictures = []
                for name in ("before.png", "after.png"):
                    path = folder / name
                    if path.is_symlink() or path.stat().st_size > 4_000_000:
                        raise ValueError("Invalid preview file.")
                    with Image.open(path) as image:
                        if image.format != "PNG" or not 1 <= image.width * image.height <= 640 * 360:
                            raise ValueError("Invalid preview dimensions.")
                        image.load()
                        pictures.append(image.convert("RGB"))
                self._before, self._after = pictures
                self.compare.setEnabled(True)
                self.compare.setChecked(False)
                self._show_comparison()
                self._preview_key = self._job_key
                self.status.setText(self._t("ready"))
            else:
                duration = response.get("duration_ms")
                if type(duration) is not int or not 100 <= duration <= 30_000:
                    raise ValueError("Invalid restored clip duration.")
                install_restored_clip(folder / "output.mp4", self._destination, self.protected)
                self.result_clip = replace(self.clip, source=self._destination,
                    duration_ms=duration, start_ms=0, end_ms=duration,
                    video_adjustments=VideoAdjustments())
                super().accept()
        except (OSError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))
        finally:
            self.runner.cleanup()
            self._set_busy(False)
            if self._closing:
                super().reject()

    def apply(self) -> None:
        if self.runner.busy or self._preview_key != self._key():
            return
        if not self.ai.isChecked():
            self.result_clip = replace(self.clip, video_adjustments=self._adjustments())
            self.runner.cleanup()
            super().accept()
            return
        try:
            request = self._request("render")
            selected, _ = QFileDialog.getSaveFileName(self, self._t("save"),
                str(self.clip.source.with_name(self.clip.source.stem + "-ki.mp4")), "MP4 (*.mp4)")
            if not selected:
                return
            candidate = Path(selected)
            if not candidate.suffix:
                candidate = candidate.with_suffix(".mp4")
            self._destination = validate_destination(candidate, self.protected)
            if self._destination.exists() and QMessageBox.question(self, self._t("save"),
                    self._t("overwrite"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
            self._mode, self._job_key = "render", self._key()
            self.runner.start(request, self._destination.parent)
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self._set_busy(True)
        except (OSError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def _show_error(self, message: str) -> None:
        self.status.setText(self._t("error"))
        QMessageBox.warning(self, self._t("error"), message)

    def _cancel(self) -> None:
        if self.runner.busy:
            self.runner.cancel()
        else:
            self.reject()

    def reject(self) -> None:
        self._closing = True
        if self.runner.busy:
            self._closing = True
            self.runner.cancel()
            return
        self.runner.cleanup()
        super().reject()

    def closeEvent(self, event) -> None:
        self._closing = True
        if self.runner.busy:
            event.ignore()
            self.reject()
        else:
            self.runner.cleanup()
            super().closeEvent(event)
