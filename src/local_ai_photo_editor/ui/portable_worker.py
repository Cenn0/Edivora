"""Qt worker for explicit portable media copying; never blocks the GUI loop."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..core.media_project import MediaSequence
from ..core.portable_media import create_portable_media_folder


class PortableMediaWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, sequence: MediaSequence, directory: Path, parent=None):
        super().__init__(parent)
        self._sequence = sequence
        self._directory = directory

    def run(self) -> None:
        try:
            project = create_portable_media_folder(
                self._sequence, self._directory,
                cancelled=self.isInterruptionRequested,
            )
        except (OSError, ValueError, InterruptedError) as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(str(project))
