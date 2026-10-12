"""Desktop, worker and packaged smoke-test entry points."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PillowImage

SMOKE_TIMEOUT_SECONDS = 120


def worker_command(directory: str | Path) -> tuple[str, list[str]]:
    args = ["--worker", str(directory)]
    compiled = globals().get("__compiled__")
    if compiled is not None:
        # Nuitka 4.3's standalone sys.executable names a Python executable in
        # the distribution directory. process_exe identifies this actual app.
        program = getattr(compiled, "process_exe", None)
        if not program:
            raise RuntimeError("The compiled application did not expose its executable path.")
        return str(program), args
    if getattr(sys, "frozen", False):
        return sys.executable, args
    return sys.executable, ["-m", "local_ai_photo_editor", *args]


def _synthetic_photo() -> PillowImage:
    from PIL import Image, ImageDraw

    picture = Image.new("RGBA", (384, 256), (237, 240, 245, 255))
    draw = ImageDraw.Draw(picture)
    draw.ellipse((96, 32, 288, 224), fill=(160, 53, 36, 255))
    draw.ellipse((144, 52, 200, 90), fill=(226, 99, 75, 255))
    return picture


def smoke_test(output_directory: Path) -> int:
    """Exercise the actual child worker; this is not a segmentation benchmark."""
    from PIL import Image
    from .ai.models import MODEL_SHA256
    from .core import export_image, load_image

    output_directory.mkdir(parents=True, exist_ok=False)
    phase = "synthetic_image"
    diagnostics = {"sys_executable": sys.executable}
    try:
        picture = _synthetic_photo()
        phase = "create_job_directory"
        with tempfile.TemporaryDirectory(prefix="local-ai-photo-editor-smoke-") as temporary:
            directory = Path(temporary)
            status_path = directory / "result.json"
            try:
                phase = "write_input"
                export_image(picture, directory / "input.png")
                phase = "write_request"
                (directory / "request.json").write_text(
                    json.dumps({"version": 1, "operation": "remove_background"}),
                    encoding="utf-8",
                )
                phase = "worker_command"
                program, arguments = worker_command(directory)
                diagnostics.update({
                    "program": program,
                    "arguments": arguments,
                    "program_exists": Path(program).is_file(),
                })
                phase = "start_and_wait_for_worker"
                # run() kills and waits for this child before raising TimeoutExpired.
                completed = subprocess.run(
                    [program, *arguments],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=SMOKE_TIMEOUT_SECONDS,
                    check=False,
                )
                diagnostics["returncode"] = completed.returncode
                phase = "worker_exit"
                if completed.returncode != 0:
                    raise RuntimeError("The smoke-test worker failed.")
                phase = "read_worker_status"
                if status_path.stat().st_size > 4096:
                    raise ValueError("The worker returned an invalid status file.")
                if json.loads(status_path.read_text(encoding="utf-8")) != {"status": "ok"}:
                    raise ValueError("The worker did not report a successful job.")
                phase = "read_worker_output"
                result_path = directory / "output.png"
                with Image.open(result_path) as encoded:
                    if encoded.format != "PNG" or encoded.size != picture.size:
                        raise ValueError("The worker returned an invalid PNG result.")
                    encoded.verify()
                result = load_image(result_path)
                phase = "validate_transparency"
                if result.mode != "RGBA":
                    raise ValueError("The worker result has no alpha channel.")
                low, high = result.getchannel("A").getextrema()
                if low == 255 or high == 0:
                    raise ValueError("The worker did not preserve a foreground with transparency.")
                phase = "export_output"
                export_image(result, output_directory / "smoke-output.png")
                phase = "cleanup_job"
            finally:
                # This CLI uses synthetic pixels only. Preserve the bounded
                # child status before TemporaryDirectory removes the job.
                try:
                    if status_path.is_file() and status_path.stat().st_size <= 4096:
                        (output_directory / "worker-result.json").write_bytes(status_path.read_bytes())
                except OSError as archive_error:
                    diagnostics["status_archive_error"] = str(archive_error)
        report = {
            "status": "ok",
            "scope": "worker_runtime_only",
            "provider": "CPUExecutionProvider",
            "model_sha256": MODEL_SHA256,
            "dimensions": list(result.size),
            "worker": diagnostics,
        }
        code = 0
    except Exception as exc:
        import traceback

        report = {
            "status": "error",
            "scope": "worker_runtime_only",
            "phase": phase,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "worker": diagnostics,
        }
        code = 1
    (output_directory / "smoke-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return code


def ui_smoke_test(output_directory: Path) -> int:
    """Capture the actual window and verify that its Qt event loop shuts down."""
    output_directory.mkdir(parents=True, exist_ok=False)
    app = None
    window = None
    capture_timer = None
    watchdog = None
    quit_on_last_window_closed = None
    code = 1
    report = {"status": "error", "scope": "ui_startup_and_capture_only"}

    def record_error(exc: Exception, phase: str) -> None:
        nonlocal code, report
        code = 1
        report = {
            "status": "error",
            "scope": "ui_startup_and_capture_only",
            "phase": phase,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from shiboken6 import delete
        from .ui import EditorWindow

        app = QApplication.instance() or QApplication(sys.argv[:1])
        app.setApplicationName("localAiPhotoEditor")
        app.setOrganizationName("localAiPhotoEditor")
        quit_on_last_window_closed = app.quitOnLastWindowClosed()
        # Exit only after the window and its children have been destroyed.
        app.setQuitOnLastWindowClosed(False)
        window = EditorWindow()
        picture = _synthetic_photo()
        window.set_document(picture)
        window.set_language("de")
        window.show()
        captures = {}
        languages = ("de", "en")
        capture_timer = QTimer(app)
        capture_timer.setSingleShot(True)
        watchdog = QTimer(app)
        watchdog.setSingleShot(True)

        def window_destroyed(*_args) -> None:
            nonlocal window
            window = None
            try:
                watchdog.stop()
            except Exception as exc:
                record_error(exc, "shutdown")
            finally:
                app.exit(code)

        def finish() -> None:
            capture_timer.stop()
            try:
                if not window.close():
                    raise RuntimeError("The editor refused to close.")
                # The running event loop delivers DeferredDelete before exit.
                window.deleteLater()
            except Exception as exc:
                record_error(exc, "shutdown")
                app.exit(1)

        def capture_next() -> None:
            nonlocal code, report
            try:
                language = languages[len(captures)]
                capture = window.grab()
                if capture.isNull() or capture.width() <= 0 or capture.height() <= 0:
                    raise RuntimeError("The editor window did not render.")
                filename = f"ui-smoke-{language}.png"
                if not capture.save(str(output_directory / filename), "PNG"):
                    raise OSError("The editor window capture could not be saved.")
                captures[language] = {
                    "file": filename,
                    "dimensions": [capture.width(), capture.height()],
                }
                if len(captures) < len(languages):
                    window.set_language(languages[len(captures)])
                    capture_timer.start(100)
                    return
                report = {
                    "status": "ok",
                    "scope": "ui_startup_and_capture_only",
                    "image_dimensions": list(picture.size),
                    "captures": captures,
                }
                code = 0
            except Exception as exc:
                record_error(exc, "capture")
            finish()

        def timed_out() -> None:
            record_error(TimeoutError("The UI smoke test did not finish within 30 seconds."), "event_loop")
            app.exit(1)

        window.destroyed.connect(window_destroyed)
        capture_timer.timeout.connect(capture_next)
        watchdog.timeout.connect(timed_out)
        capture_timer.start(100)
        watchdog.start(30_000)
        loop_code = app.exec()
        if loop_code != 0 or code != 0 or window is not None:
            if report["status"] != "error" or "error_type" not in report:
                record_error(RuntimeError("The Qt event loop did not complete a clean shutdown."), "event_loop")
        report["event_loop_exit_code"] = loop_code
    except Exception as exc:
        record_error(exc, "startup")
    finally:
        try:
            # Also dispose of a partially started window after an exception or
            # timeout. QApplication must outlive every QWidget and QPixmap.
            if window is not None:
                delete(window)
                window = None
            for timer in (capture_timer, watchdog):
                if timer is not None:
                    timer.stop()
                    delete(timer)
            if app is not None and quit_on_last_window_closed is not None:
                app.setQuitOnLastWindowClosed(quit_on_last_window_closed)
        except Exception as exc:
            record_error(exc, "cleanup")
    (output_directory / "ui-smoke-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return code


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 2 and args[0] == "--worker":
        from .worker import run_job
        return run_job(Path(args[1]))
    if len(args) == 2 and args[0] == "--smoke-test":
        return smoke_test(Path(args[1]))
    if len(args) == 2 and args[0] == "--ui-smoke-test":
        return ui_smoke_test(Path(args[1]))
    if args:
        return 2
    from PySide6.QtWidgets import QApplication
    from .ui import EditorWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("localAiPhotoEditor")
    app.setOrganizationName("localAiPhotoEditor")
    window = EditorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

