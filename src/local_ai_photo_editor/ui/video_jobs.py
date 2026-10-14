"""Qt orchestration for offline preview/restoration with bounded process lifetime."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import tempfile

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..core.video_job import VideoJob


class RestorationRunner(QObject):
    progress = Signal(int)
    finished = Signal(object, object)  # response, temporary job folder

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.process: QProcess | None = None
        self.folder: Path | None = None
        self._temporary: tempfile.TemporaryDirectory | None = None
        self._buffer = bytearray()
        self._error = bytearray()
        self._cancelled = False
        self._pid = 0

    @property
    def busy(self) -> bool:
        return self.process is not None

    def start(self, request: VideoJob, parent_folder: Path | None = None) -> None:
        if self.busy:
            raise RuntimeError("A video job is already running.")
        request.validated()
        self.cleanup()
        self._temporary = tempfile.TemporaryDirectory(prefix=".edivora-restoration-",
                                                       dir=parent_folder)
        self.folder = Path(self._temporary.name)
        (self.folder / "request.json").write_text(json.dumps(request.to_dict()), encoding="utf-8")
        self._buffer.clear()
        self._error.clear()
        self._cancelled = False
        self._pid = 0
        from ..__main__ import media_job_command
        program, arguments = media_job_command("restore", self.folder)
        process = QProcess(self)
        self.process = process
        if os.name != "nt":
            parameters = QProcess.UnixProcessParameters()
            parameters.flags = QProcess.UnixProcessFlag.CreateNewSession
            process.setUnixProcessParameters(parameters)
        process.setProgram(program)
        process.setArguments(arguments)
        process.started.connect(lambda: setattr(self, "_pid", process.processId()))
        process.readyReadStandardOutput.connect(self._read_progress)
        process.readyReadStandardError.connect(self._read_error)
        process.finished.connect(lambda code, _status: self._done(process, code))
        process.errorOccurred.connect(lambda error: self._failed_to_start(process, error))
        process.start()

    def _read_progress(self) -> None:
        if not self.process:
            return
        self._buffer.extend(bytes(self.process.readAllStandardOutput()))
        if len(self._buffer) > 8192:
            del self._buffer[:-8192]
        while b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            try:
                value = json.loads(line).get("progress")
                if type(value) is int and 0 <= value <= 100:
                    self.progress.emit(value)
            except (ValueError, AttributeError):
                pass

    def _read_error(self) -> None:
        if self.process:
            self._error.extend(bytes(self.process.readAllStandardError()))
            del self._error[:-8192]

    def _failed_to_start(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._done(process, -1)

    def _done(self, process: QProcess, code: int) -> None:
        if self.process is not process:
            return
        self._read_error()
        self._read_progress()
        self.process = None
        self._pid = 0
        process.deleteLater()
        response = {"ok": False, "cancelled": self._cancelled,
                    "message": self._error.decode("utf-8", errors="replace")[-800:]}
        path = self.folder / "result.json"
        try:
            if path.is_file() and not path.is_symlink() and path.stat().st_size <= 8192:
                loaded = json.loads(path.read_text("utf-8"))
                if type(loaded) is dict:
                    response = loaded
            if code != 0 or self._cancelled:
                response["ok"] = False
            if self._cancelled:
                response["cancelled"] = True
        except (OSError, ValueError):
            pass
        self.finished.emit(response, self.folder)

    def cancel(self) -> None:
        if self.process is None:
            return
        self._cancelled = True
        (self.folder / "cancel").touch()
        process, pid = self.process, self._pid
        # Normal cancellation interrupts between bounded inference tiles. The
        # worker watchdog also kills a decoder blocked on a pipe. Escalation
        # never targets the editor's own session/process group.
        QTimer.singleShot(10_000, lambda: self._kill(process, pid))

    def _kill(self, process: QProcess, pid: int) -> None:
        if self.process is not process:
            return
        if os.name != "nt" and pid > 0:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            # The Windows worker installs its kill-on-close Job Object before
            # spawning FFmpeg. No child can outlive that worker after this kill.
            process.kill()

    def cleanup(self) -> None:
        if self.busy:
            raise RuntimeError("Cannot remove files while a video job is running.")
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
            self.folder = None
