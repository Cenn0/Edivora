"""Bounded, render-accurate local preview of a complete one-lane sequence.

This is intentionally NOT a live multitrack engine: the exact current export
filtergraph is rendered asynchronously to a private temporary media file
before playback. UI remains responsive, cancel kills the single FFmpeg child,
and the temporary file is discarded on close. Never advertises generic GPU
support or preview of arbitrarily long timelines.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QProcess, QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSlider,
    QVBoxLayout,
)

from ..core.media_project import MediaSequence
from ..core.media_sequence import SequenceExport, commit_sequence_export
from .media_window import clock

MAX_PREVIEW_MS = 120_000
MAX_RENDER_WALL_SECONDS = 180
MAX_PREVIEW_BYTES = 512 * 1024 * 1024


def preview_allowed(sequence: MediaSequence) -> bool:
    """A short preview must be within the normal media validator's limits."""
    sequence.validated()
    return sequence.length_ms <= MAX_PREVIEW_MS


class SequencePreviewDialog(QDialog):
    """Play an exact assembled (at most 2 min) audio/video render, locally."""

    def __init__(self, sequence: MediaSequence, *, engine: str,
                 video_profile: str = "hd", language: str = "en", parent=None) -> None:
        if not preview_allowed(sequence):
            raise ValueError("A full-sequence preview is limited to two minutes.")
        super().__init__(parent)
        self._de = language == "de"
        self._folder = tempfile.TemporaryDirectory(prefix="edivora-sequence-preview-")
        suffix = ".mp4" if sequence.kind == "video" else ".wav"
        self._destination = Path(self._folder.name) / ("preview" + suffix)
        self._plan = SequenceExport(sequence, self._destination, video_profile).validated()
        self._temporary = self._plan.temp_output()
        self._engine = engine
        self._process: QProcess | None = None
        self._stderr = bytearray()
        self._stdout = bytearray()
        self._started_at = 0.0
        self._cancelled = False
        self._failure: str | None = None
        self._ready = False
        self._cleaned = False

        self.setWindowTitle("Gesamte Sequenz ansehen" if self._de else "Preview full sequence")
        self.setMinimumSize(500, 340 if sequence.kind == "video" else 210)
        self.resize(770, 480 if sequence.kind == "video" else 240)
        layout = QVBoxLayout(self)
        self.message = QLabel("Vorschau wird lokal vorbereitet …" if self._de
                              else "Preparing local sequence preview …")
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.message)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.8)
        self.player.setAudioOutput(self.audio)
        if sequence.kind == "video":
            self.video = QVideoWidget(self)
            layout.addWidget(self.video, 1)
            self.player.setVideoOutput(self.video)
        else:
            self.video = None
            layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, sequence.length_ms)
        self.seek.setEnabled(False)
        self.seek.sliderMoved.connect(self.player.setPosition)
        layout.addWidget(self.seek)

        controls = QHBoxLayout()
        self.play_button = QPushButton("Abspielen" if self._de else "Play")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.toggle_play)
        controls.addWidget(self.play_button)
        self.clock_label = QLabel("00:00:00 / " + clock(sequence.length_ms))
        controls.addWidget(self.clock_label)
        controls.addStretch()
        self.close_button = QPushButton("Abbrechen" if self._de else "Cancel")
        self.close_button.clicked.connect(self.close)
        controls.addWidget(self.close_button)
        layout.addLayout(controls)

        self.player.positionChanged.connect(self._position)
        self.player.playbackStateChanged.connect(self._playback_state)
        self.player.errorOccurred.connect(self._playback_error)

        self.watchdog = QTimer(self)
        self.watchdog.setInterval(300)
        self.watchdog.timeout.connect(self._guard_resource_limits)
        QTimer.singleShot(0, self._start_render)

    @property
    def preview_ready(self) -> bool:
        return self._ready

    def _start_render(self) -> None:
        if self._cleaned or self._process is not None:
            return
        try:
            args = self._plan.ffmpeg_arguments(self._temporary)
            process = QProcess(self)
            self._process = process
            self._started_at = time.monotonic()
            process.setProgram(self._engine)
            process.setArguments(args)
            process.readyReadStandardOutput.connect(self._collect_progress)
            process.readyReadStandardError.connect(self._collect_stderr)
            process.finished.connect(
                lambda code, status, p=process: self._finished(p, code)
            )
            process.errorOccurred.connect(
                lambda error, p=process: self._start_error(p, error)
            )
            self.watchdog.start()
            process.start()
        except (ValueError, OSError, RuntimeError) as exc:
            self._show_failure(str(exc))

    def _collect_progress(self) -> None:
        process = self._process
        if process is None:
            return
        self._stdout.extend(bytes(process.readAllStandardOutput()))
        if len(self._stdout) > 16 * 1024:
            del self._stdout[:-8192]
        while b"\n" in self._stdout:
            line, _, remainder = self._stdout.partition(b"\n")
            self._stdout = bytearray(remainder)
            if line.startswith(b"out_time_us="):
                try:
                    microseconds = max(0, int(line.split(b"=", 1)[1]))
                    percent = microseconds / (self._plan.sequence.length_ms * 1000) * 100
                    self.progress.setValue(min(99, max(0, round(percent))))
                except ValueError:
                    pass

    def _collect_stderr(self) -> None:
        process = self._process
        if process is not None:
            self._stderr.extend(bytes(process.readAllStandardError()))
            if len(self._stderr) > 4096:
                del self._stderr[:-4096]

    def _guard_resource_limits(self) -> None:
        if self._process is None:
            return
        if time.monotonic() - self._started_at > MAX_RENDER_WALL_SECONDS:
            self._failure = ("Zeitlimit für die Vorschau überschritten."
                             if self._de else "Preview rendering timed out.")
            self._process.kill()
        elif self._temporary.is_file() and self._temporary.stat().st_size > MAX_PREVIEW_BYTES:
            self._failure = ("Vorschau überschreitet das Größenlimit."
                             if self._de else "Preview exceeds the temporary size limit.")
            self._process.kill()

    def _start_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process is self._process and error == QProcess.ProcessError.FailedToStart:
            self._finished(process, -1)

    def _finished(self, process: QProcess, code: int) -> None:
        if process is not self._process:
            return
        self.watchdog.stop()
        self._collect_progress()
        self._collect_stderr()
        self._process = None
        process.deleteLater()
        try:
            if self._cancelled or self._cleaned:
                return
            if self._failure is not None:
                raise RuntimeError(self._failure)
            if code != 0:
                reason = self._stderr.decode("utf-8", "replace").strip()[-250:]
                raise RuntimeError(reason or "The local renderer failed.")
            if self._temporary.stat().st_size > MAX_PREVIEW_BYTES:
                raise ValueError("Preview exceeds the temporary size limit.")
            commit_sequence_export(self._plan, self._temporary)
            self._ready = True
            self.progress.setValue(100)
            self.progress.hide()
            self.message.setText(
                "Komplette Vorschau aus dem echten Export-Renderpfad."
                if self._de else "Full preview from the actual export rendering path."
            )
            self.player.setSource(QUrl.fromLocalFile(str(self._destination)))
            self.seek.setEnabled(True)
            self.play_button.setEnabled(True)
        except (OSError, RuntimeError, ValueError) as exc:
            self._show_failure(str(exc))
        finally:
            self._temporary.unlink(missing_ok=True)
            self.close_button.setText("Schließen" if self._de else "Close")

    def _show_failure(self, detail: str) -> None:
        self.watchdog.stop()
        self.message.setText(("Vorschau fehlgeschlagen: " if self._de
                              else "Preview failed: ") + detail[-320:])
        self.close_button.setText("Schließen" if self._de else "Close")

    def _position(self, position: int) -> None:
        if not self.seek.isSliderDown():
            self.seek.setValue(max(0, position))
        self.clock_label.setText(clock(position) + " / " + clock(self._plan.sequence.length_ms))

    def _playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setText(("Pause" if playing else "Abspielen") if self._de
                                 else ("Pause" if playing else "Play"))

    def _playback_error(self, error: QMediaPlayer.Error, _message: str) -> None:
        if error != QMediaPlayer.Error.NoError and self._ready:
            self.message.setText(
                "Der lokale Multimedia-Decoder kann die Vorschau nicht wiedergeben."
                if self._de else "The local multimedia decoder cannot play the preview."
            )

    def toggle_play(self) -> None:
        if not self._ready:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._process is not None:
            self._cancelled = True
            process = self._process
            process.kill()
            if not process.waitForFinished(3000):
                self.message.setText(
                    "Medienprozess wird beendet …" if self._de else "Stopping media process …"
                )
                event.ignore()  # Never delete a directory still used by FFmpeg.
                return
            if self._process is process:
                self._finished(process, -1)
        self.player.stop()
        self.player.setSource(QUrl())
        if self.video is not None:
            self.player.setVideoOutput(None)
        self.player.setAudioOutput(None)
        self.watchdog.stop()
        if not self._cleaned:
            self._folder.cleanup()
            self._cleaned = True
        event.accept()
