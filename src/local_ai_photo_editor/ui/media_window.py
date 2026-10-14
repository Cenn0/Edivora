"""Two independent, task-first offline Qt media workspaces.

The player is for disposable previews only. FFmpeg performs exports into
temporary files; a successful job atomically installs a new destination.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QProcess, QSignalBlocker, Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSlider, QSplitter, QVBoxLayout, QWidget,
)

from ..branding import app_icon
from ..core.media import (
    MIN_SELECTION_MS, MediaExport, commit_export, ffmpeg_executable, validate_source,
)
from .media_strings import text
from .theme import stylesheet
from .icons import IconButton, icon
from .responsive import fit_initial_window
from .media_shell import build_media_shell, resize_media_shell
from .trim_timeline import TrimTimeline


def clock(milliseconds: int) -> str:
    seconds = max(0, milliseconds) // 1000
    return f"{seconds // 3600:02d}:{(seconds // 60) % 60:02d}:{seconds % 60:02d}"


class MediaWindow(QMainWindow):
    """Video and Audio: separate windows, one straightforward editing contract."""

    def __init__(self, kind: str, compiled_executable: str | None = None) -> None:
        if kind not in ("video", "audio"):
            raise ValueError("Editor must be video or audio.")
        super().__init__()
        self.kind = kind
        self.language = "de"
        self._compiled_executable = compiled_executable
        self.source: Path | None = None
        self.duration_ms = 0
        self._labels: list[tuple[object, str]] = []
        self._export_process: QProcess | None = None
        self._active_export: MediaExport | None = None
        self._temporary_export: Path | None = None
        self._export_error = bytearray()
        self._cancel_requested = False
        self._wave_process: QProcess | None = None
        self._wave_data = bytearray()
        self._wave_pixmap: QPixmap | None = None
        self._status_key = "ready"
        self._status_values: dict[str, object] = {}
        self.setMinimumSize(640, 480)
        self.resize(1270, 800)
        self.setAcceptDrops(True)
        self.setStyleSheet(stylesheet())

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self._build_ui()
        self.player.durationChanged.connect(self._duration_changed)
        self.player.positionChanged.connect(self._position_changed)
        self.player.playbackStateChanged.connect(self._playback_changed)
        self.player.errorOccurred.connect(self._playback_error)
        self._translate()
        self._update_enabled()
        fit_initial_window(self, (1270, 800))

    def _t(self, key: str, **kwargs: object) -> str:
        return text(self.language, key, **kwargs)

    def _label(self, key: str, style: str = "", wrap: bool = False) -> QLabel:
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(wrap)
        if style:
            label.setObjectName(style)
        self._labels.append((label, key))
        return label

    def _button(self, key: str, callback: Callable, style: str = "") -> QPushButton:
        button = IconButton(key=key)
        if style:
            button.setObjectName(style)
        button.clicked.connect(callback)
        self._labels.append((button, key))
        return button

    def _check(self, key: str, callback: Callable) -> QCheckBox:
        check = QCheckBox()
        check.toggled.connect(callback)
        self._labels.append((check, key))
        return check

    def _build_ui(self) -> None:
        build_media_shell(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        resize_media_shell(self)

    def _switch_language(self) -> None:
        self.language = str(self.language_combo.currentData() or "de")
        self._translate()

    def _translate(self) -> None:
        self.setWindowTitle(f"Edivora · {self._t(self.kind)}")
        for widget, key in self._labels:
            # A language switch must not erase a decoded waveform pixmap.
            if widget is self.wave_label and self._wave_pixmap is not None:
                continue
            widget.setText(self._t(key))
            if isinstance(widget, QCheckBox):
                widget.setAccessibleName(self._t(key))
                widget.setToolTip(self._t(key))
        if self.wave_label is not None and self._wave_pixmap is not None:
            self.wave_label.setToolTip(
                self._t("waveform_partial") if self.duration_ms > 900_000 else ""
            )
        if self.source is not None:
            self.file_label.setText(self.source.name)
        self._set_status(self._status_key, **self._status_values)
        self.timeline.setToolTip(self._t("timeline_hint"))
        self.timeline.setAccessibleName(self._t("timeline_title"))
        self.timeline.setAccessibleDescription(self._t("timeline_accessible"))
        self._playback_changed(self.player.playbackState())
        self.language_combo.setAccessibleName(self._t("language"))
        self.volume.setAccessibleName(self._t("volume"))
        for control, key in ((self.start_spin, "start_time"), (self.end_spin, "end_time")):
            control.setAccessibleName(self._t(key))
        for index, key in self._inspector_tab_keys:
            self.inspector_tabs.setTabText(index, self._t(key))
        resize_media_shell(self)

    def _set_status(self, key: str, **values: object) -> None:
        self._status_key = key
        self._status_values = values
        self.status.setText(self._t(key, **values))

    def _is_busy(self) -> bool:
        return self._export_process is not None

    def _valid_selection(self) -> bool:
        if self.source is None or self.duration_ms <= 0:
            return False
        start = round(self.start_spin.value() * 1000)
        end = round(self.end_spin.value() * 1000)
        if start < 0 or end > self.duration_ms + 1 or end - start < MIN_SELECTION_MS:
            return False
        if self.kind == "audio":
            fades = round((self.fade_in.value() + self.fade_out.value()) * 1000)
            if fades > end - start:
                return False
        return True

    def _update_enabled(self) -> None:
        enabled = self.source is not None and self.duration_ms > 0 and not self._is_busy()
        can_export = enabled and self._valid_selection()
        for button in (self.export_button, self.export_second):
            button.setEnabled(can_export)
        self.open_button.setEnabled(not self._is_busy())
        for control in (self.play_button, self.stop_button, self.start_spin,
                        self.end_spin, self.volume, self.timeline, self.mark_start_button,
                        self.mark_end_button, self.reset_range_button):
            control.setEnabled(enabled)
        for control in (self.mute, self.normalize, self.fade_in, self.fade_out):
            if control is not None:
                control.setEnabled(enabled)

    def _selection_changed(self, *_args: object) -> None:
        self.timeline.set_range(
            round(self.start_spin.value() * 1000),
            round(self.end_spin.value() * 1000),
        )
        self._update_enabled()
        if self.source is not None and self.duration_ms > 0:
            if not self._valid_selection() and not self._is_busy():
                self._set_status("invalid_selection")
            elif self._status_key == "invalid_selection":
                self._set_status("loaded")

    def _timeline_changed(self, start_ms: int, end_ms: int) -> None:
        # Prevent a signal cycle from numeric field updates. The spin boxes
        # remain the exact source for the existing validated FFmpeg export.
        if self._is_busy() or self.duration_ms <= 0:
            return
        with QSignalBlocker(self.start_spin), QSignalBlocker(self.end_spin):
            self.start_spin.setValue(start_ms / 1000)
            self.end_spin.setValue(end_ms / 1000)
        self._selection_changed()

    def _seek_from_timeline(self, position_ms: int) -> None:
        if self.source is None or self.duration_ms <= 0 or self._is_busy():
            return
        if self.timeline._dragging:
            self.player.pause()
        self.timeline.set_position(position_ms)
        self.player.setPosition(position_ms)

    def _mark_start_at_playhead(self) -> None:
        if self.source is None or self.duration_ms < MIN_SELECTION_MS or self._is_busy():
            return
        position = min(self.player.position(), round(self.end_spin.value() * 1000) - MIN_SELECTION_MS)
        self.start_spin.setValue(max(0, position) / 1000)

    def _mark_end_at_playhead(self) -> None:
        if self.source is None or self.duration_ms < MIN_SELECTION_MS or self._is_busy():
            return
        position = max(self.player.position(), round(self.start_spin.value() * 1000) + MIN_SELECTION_MS)
        self.end_spin.setValue(min(self.duration_ms, position) / 1000)

    def _reset_range(self) -> None:
        if self.source is None or self.duration_ms < MIN_SELECTION_MS or self._is_busy():
            return
        with QSignalBlocker(self.start_spin), QSignalBlocker(self.end_spin):
            self.start_spin.setValue(0)
            self.end_spin.setValue(self.duration_ms / 1000)
        self._selection_changed()

    def _volume_changed(self, value: int) -> None:
        self.volume_label.setText(f"{value} %")
        self.audio_output.setVolume(min(value / 100, 1.0))

    def _mute_changed(self, muted: bool) -> None:
        self.audio_output.setMuted(muted)

    def open_file(self) -> None:
        if self._is_busy():
            return
        if self.kind == "video":
            filter_spec = "Video (*.mp4 *.mov *.mkv *.webm *.avi *.m4v)"
        else:
            filter_spec = "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus)"
        path, _ = QFileDialog.getOpenFileName(self, self._t("open"), "", filter_spec)
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        if self._is_busy():
            return
        try:
            file = validate_source(path, self.kind)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, self._t("error"), f"{self._t('file_error')}\n{exc}")
            return
        self._cancel_waveform()
        self.player.stop()
        self.source = file
        self.duration_ms = 0
        self.file_label.setText(file.name)
        self.file_label.setToolTip(str(file))
        self.timeline.set_duration(0)
        for spin in (self.start_spin, self.end_spin):
            spin.blockSignals(True)
            spin.setRange(0, 0)
            spin.setValue(0)
            spin.blockSignals(False)
        self._set_status("duration_wait")
        url = QUrl.fromLocalFile(str(file))
        # Qt ignores setSource with the same URL. Clear it first so duplicate
        # clips, undo/redo, and reopening a file receive fresh metadata.
        if self.player.source() == url:
            self.player.setSource(QUrl())
        self.player.setSource(url)
        if self.kind == "audio":
            self._render_waveform(file)
        self._update_enabled()

    def _duration_changed(self, duration: int) -> None:
        if self.source is None:
            return
        self.duration_ms = max(0, int(duration))
        self.timeline.set_duration(self.duration_ms)
        seconds = self.duration_ms / 1000
        for spin in (self.start_spin, self.end_spin):
            spin.blockSignals(True)
            spin.setRange(0.0, seconds)
            spin.blockSignals(False)
        self.start_spin.setValue(0)
        self.end_spin.setValue(seconds)
        self._set_status("loaded" if duration > 0 else "no_duration")
        self._update_enabled()
        self._position_changed(self.player.position())

    def _position_changed(self, position: int) -> None:
        self.timeline.set_position(position)
        self.time_label.setText(self._t("time_label", position=clock(position), duration=clock(self.duration_ms)))
        if self._valid_selection() and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            if position >= round(self.end_spin.value() * 1000):
                self.player.pause()

    def _playback_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.play_button.setIcon(icon("pause" if state == QMediaPlayer.PlaybackState.PlayingState else "play"))
        self.play_button.setText(self._t(
            "pause" if state == QMediaPlayer.PlaybackState.PlayingState else "play"
        ))

    def _playback_error(self, error: QMediaPlayer.Error, _message: str) -> None:
        if error != QMediaPlayer.Error.NoError and self.source is not None:
            self._set_status("preview_error")

    def toggle_play(self) -> None:
        if not self._valid_selection():
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            start, end = round(self.start_spin.value() * 1000), round(self.end_spin.value() * 1000)
            if self.player.position() < start or self.player.position() >= end:
                self.player.setPosition(start)
            self.player.play()

    def stop_playback(self) -> None:
        self.player.pause()
        if self._valid_selection():
            self.player.setPosition(round(self.start_spin.value() * 1000))

    def _build_export(self, destination: Path) -> MediaExport:
        return MediaExport(
            kind=self.kind, source=self.source, destination=destination,
            duration_ms=self.duration_ms,
            start_ms=round(self.start_spin.value() * 1000),
            end_ms=round(self.end_spin.value() * 1000),
            volume_percent=self.volume.value(),
            mute=self.mute.isChecked() if self.mute is not None else False,
            normalize=self.normalize.isChecked() if self.normalize is not None else False,
            fade_in_ms=round(self.fade_in.value() * 1000) if self.fade_in is not None else 0,
            fade_out_ms=round(self.fade_out.value() * 1000) if self.fade_out is not None else 0,
        ).validated()

    def export_file(self) -> None:
        if not self._valid_selection() or self._is_busy() or self.source is None:
            return
        default_extension = ".mp4" if self.kind == "video" else ".wav"
        proposed = self.source.with_name(self.source.stem + "-edivora" + default_extension)
        filter_spec = "MP4 (*.mp4)" if self.kind == "video" else "WAV (*.wav);;MP3 (*.mp3)"
        chosen, filter_name = QFileDialog.getSaveFileName(
            self, self._t("export_title"), str(proposed), filter_spec
        )
        if not chosen:
            return
        target = Path(chosen)
        if not target.suffix:
            target = target.with_suffix(".mp3" if "MP3" in filter_name else default_extension)
        try:
            export = self._build_export(target)
            engine = ffmpeg_executable(self._compiled_executable)
            if target.exists() and QMessageBox.question(
                self, self._t("export_title"), self._t("overwrite"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
            temporary = export.temp_output()
            args = export.ffmpeg_arguments(temporary)
        except (ValueError, OSError, RuntimeError) as exc:
            QMessageBox.warning(self, self._t("error"), str(exc))
            return
        self.stop_playback()
        self._active_export = export
        self._temporary_export = temporary
        self._export_error.clear()
        self._cancel_requested = False
        process = QProcess(self)
        self._export_process = process
        process.readyReadStandardError.connect(self._collect_error)
        process.finished.connect(self._export_finished)
        process.errorOccurred.connect(self._export_start_error)
        process.setProgram(engine)
        process.setArguments(args)
        self.progress.show()
        self.cancel_button.show()
        self._set_status("processing")
        self._update_enabled()
        process.start()

    def _collect_error(self) -> None:
        if self._export_process is not None:
            data = bytes(self._export_process.readAllStandardError())
            self._export_error.extend(data)
            if len(self._export_error) > 8192:
                del self._export_error[:-8192]

    def _export_start_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._export_finished(-1, QProcess.ExitStatus.CrashExit)

    def _export_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        process = self._export_process
        if process is None:
            return
        self._collect_error()
        export, temporary = self._active_export, self._temporary_export
        self._export_process = None
        self._active_export = None
        self._temporary_export = None
        process.deleteLater()
        self.progress.hide()
        self.cancel_button.hide()
        try:
            if self._cancel_requested:
                self._set_status("cancelled")
                return
            if exit_code != 0 or export is None or temporary is None:
                error = self._export_error.decode("utf-8", "replace").strip()[-500:]
                raise RuntimeError(error or self._t("failed"))
            commit_export(export, temporary)
            self._set_status("done", name=export.destination.name)
        except (ValueError, OSError, RuntimeError) as exc:
            self._set_status("failed")
            QMessageBox.warning(self, self._t("error"), f"{self._t('failed')}\n{exc}")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self._update_enabled()

    def cancel_export(self) -> None:
        process = self._export_process
        if process is None:
            return
        # Detached from playback; killing the encoder cannot change source.
        self._cancel_requested = True
        process.kill()
        process.waitForFinished(2000)
        # finished() normally invokes cleanup; cover a failed signal delivery.
        if self._export_process is process:
            self._export_finished(-1, QProcess.ExitStatus.CrashExit)


    def _cancel_waveform(self) -> None:
        process = self._wave_process
        if process is not None:
            self._wave_process = None
            process.kill()
            process.waitForFinished(1000)
            process.deleteLater()
        self._wave_data.clear()
        self._wave_pixmap = None

    def _render_waveform(self, source: Path) -> None:
        if self.wave_label is None:
            return
        self.wave_label.setText(self._t("waveform"))
        self.wave_label.setToolTip("")
        self._wave_pixmap = None
        try:
            engine = ffmpeg_executable(self._compiled_executable)
        except (OSError, RuntimeError):
            self.wave_label.setText(self._t("waveform_unavailable"))
            return
        process = QProcess(self)
        self._wave_process = process
        self._wave_data = bytearray()
        process.setProgram(engine)
        process.setArguments([
            "-nostdin", "-hide_banner", "-loglevel", "error",
            "-protocol_whitelist", "file,pipe,data",
            "-t", "900", "-i", str(source),
            "-filter_complex", "aformat=channel_layouts=mono,showwavespic=s=1000x180:colors=0x4FF3D3",
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
        ])
        process.readyReadStandardOutput.connect(self._collect_waveform)
        process.finished.connect(
            lambda code, status, p=process: self._waveform_finished(p, code, status)
        )
        process.errorOccurred.connect(
            lambda error, p=process: self._waveform_error(p, error)
        )
        QTimer.singleShot(30000, lambda p=process: self._waveform_timeout(p))
        process.start()

    def _collect_waveform(self) -> None:
        if self._wave_process is None:
            return
        self._wave_data.extend(bytes(self._wave_process.readAllStandardOutput()))
        if len(self._wave_data) > 5 * 1024 * 1024:
            self._wave_process.kill()

    def _waveform_finished(
        self, process: QProcess, code: int, _status: QProcess.ExitStatus
    ) -> None:
        # Ignore completion of a canceled job after another file was opened.
        if self._wave_process is not process:
            return
        self._collect_waveform()
        self._wave_process = None
        process.deleteLater()
        if self.wave_label is None:
            return
        picture = QPixmap()
        if code == 0 and picture.loadFromData(bytes(self._wave_data), "PNG"):
            self._wave_pixmap = picture
            self.wave_label.setPixmap(picture)
            self.wave_label.setScaledContents(True)
            if self.duration_ms > 900000:
                self.wave_label.setToolTip(self._t("waveform_partial"))
        else:
            self.wave_label.setText(self._t("waveform_unavailable"))
        self._wave_data.clear()

    def _waveform_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process is self._wave_process and error == QProcess.ProcessError.FailedToStart:
            self._waveform_finished(process, -1, QProcess.ExitStatus.CrashExit)

    def _waveform_timeout(self, process: QProcess) -> None:
        if self._wave_process is process and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and not self._is_busy():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and not self._is_busy():
            self.open_path(urls[0].toLocalFile())
            event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_busy() and QMessageBox.question(
            self, self._t("error"), self._t("close_processing"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        if self._is_busy():
            self.cancel_export()
        self._cancel_waveform()
        self.player.stop()
        event.accept()
