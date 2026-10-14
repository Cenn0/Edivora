"""Run the opt-in precision editor: python -m local_ai_photo_editor.detail_editor.

The normal application entry point and existing portable releases are unchanged.
The original module continues to own the isolated AI subprocess protocol.
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        from .__main__ import main as original_main
        return original_main(args)
    from PySide6.QtWidgets import QApplication
    from .ui.precision_window import EditorWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("localAiPhotoEditor")
    app.setOrganizationName("localAiPhotoEditor")
    window = EditorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
