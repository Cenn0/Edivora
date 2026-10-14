"""Qt lifecycle adapter for one local subject-selection process."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image
from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..core.selection_io import SubjectJobError, read_subject_result


class SubjectSelectionJob(QObject):
    """Emit exactly one result after process exit and temporary-file cleanup.

    The process is a cancellation/memory boundary, not an OS security sandbox.
    No photos, metadata or diagnostic streams are uploaded or printed.
    """
    finished = Signal(object, str, bool)  # mask or None, public error code, cleanup failed

    def __init__(self, parent: QObject | None = None, timeout_ms: int = 180_000) -> None:
        super().__init__(parent)
        if type(timeout_ms) is not int or timeout_ms <= 0:
            raise ValueError("A positive process timeout is required.")
        self._process: QProcess | None = None
        self._directory: Path | None = None
        self._size = (0, 0)
        self._stop_reason = ""
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(timeout_ms)
        self._timeout.timeout.connect(lambda: self.cancel("TIMEOUT"))

    @property
    def is_running(self) -> bool:
        return self._process is not None

    def start(self, image: Image.Image) -> None:
        if self.is_running:
            raise RuntimeError("A selection is already being computed.")
        from ..__main__ import worker_command
        self._stop_reason = ""
        try:
            self._directory = Path(tempfile.mkdtemp(prefix="localai-selection-"))
            image.save(self._directory / "input.png", format="PNG")
            self._size = image.size
            from .model_settings import get_preference
            from ..ai.catalog import TASK_IMAGE
            (self._directory / "request.json").write_text(
                json.dumps({"version": 1, "operation": "select_subject",
                            "model": get_preference(TASK_IMAGE)}), encoding="utf-8")
            program, arguments = worker_command(self._directory)
            process = QProcess(self)
            self._process = process
            process.setProgram(program)
            process.setArguments(arguments)
            process.setStandardOutputFile(QProcess.nullDevice())
            process.setStandardErrorFile(QProcess.nullDevice())
            process.finished.connect(lambda code, status: self._finish(process, code))
            process.errorOccurred.connect(lambda error: self._error(process, error))
            process.started.connect(lambda: process.kill() if self._stop_reason else None)
            self._timeout.start()
            process.start()
        except (OSError, ValueError, MemoryError):
            self._timeout.stop()
            process = self._process
            self._process = None
            if process is not None:
                process.deleteLater()
            cleanup_failed = self._cleanup()
            self.finished.emit(None, "START_FAILED", cleanup_failed)

    def cancel(self, reason: str = "CANCELLED") -> None:
        if self._process is None:
            return
        self._stop_reason = reason if reason in {"CANCELLED", "TIMEOUT"} else "CANCELLED"
        self._process.kill()
        # No deletion here: finished/FailedToStart owns cleanup after exit.

    def _error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process is self._process and error == QProcess.ProcessError.FailedToStart:
            self._finish(process, -1, "START_FAILED")

    def _cleanup(self) -> bool:
        directory, self._directory = self._directory, None
        if directory is not None:
            try:
                shutil.rmtree(directory)
            except OSError:
                return True
        return False

    def _finish(self, process: QProcess, exit_code: int, error: str = "") -> None:
        if process is not self._process or process.state() != QProcess.ProcessState.NotRunning:
            return
        self._timeout.stop()
        result = None
        error = self._stop_reason or error
        if not error:
            try:
                result = read_subject_result(self._directory, self._size, exit_code)
            except SubjectJobError as exc:
                error = exc.code
            except (OSError, ValueError, TypeError, MemoryError):
                error = "INFERENCE_ERROR"
        self._process = None
        process.deleteLater()
        cleanup_failed = self._cleanup()
        self.finished.emit(result, error, cleanup_failed)
