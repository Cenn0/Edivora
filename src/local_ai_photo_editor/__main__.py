"""Desktop, worker and packaged smoke-test entry points."""

from __future__ import annotations

import builtins
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PillowImage

SMOKE_TIMEOUT_SECONDS = 120


def _compiled_executable() -> str | None:
    """Resolve Nuitka's actual program path without guessing an interpreter."""
    compiled = globals().get("__compiled__")
    if compiled is None:
        return None
    program = getattr(compiled, "process_exe", None)
    if not program:
        # Nuitka 4.2.2 exposes this builtin and uses it for multiprocessing.
        # Newer versions expose the path on __compiled__.process_exe instead.
        program = getattr(builtins, "__nuitka_binary_exe", None)
    if not program:
        raise RuntimeError("The compiled application did not expose its executable path.")
    return str(program)


def worker_command(directory: str | Path) -> tuple[str, list[str]]:
    args = ["--worker", str(directory)]
    program = _compiled_executable()
    if program is not None:
        return program, args
    if getattr(sys, "frozen", False):
        return sys.executable, args
    return sys.executable, ["-m", "local_ai_photo_editor", *args]


def _bundled_qt_plugin_directory() -> Path | None:
    """Resolve the Windows standalone layout without importing Qt."""
    executable = _compiled_executable()
    if executable is None:
        return None
    plugins = Path(executable).parent / "PySide6" / "qt-plugins"
    platform_plugin = plugins / "platforms" / "qwindows.dll"
    if not platform_plugin.is_file():
        raise FileNotFoundError(2, "The bundled Qt Windows platform plugin is missing.", str(platform_plugin))
    return plugins


def _configure_bundled_qt_plugins() -> Path | None:
    """Apply our package layout after Qt imports and before QApplication."""
    plugins = _bundled_qt_plugin_directory()
    if plugins is not None:
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.setLibraryPaths([str(plugins)])
    return plugins


def _synthetic_photo() -> PillowImage:
    import numpy as np
    from PIL import Image

    # This fixture needs only pixels, so no drawing or font imports are needed.
    # Those imports were a visible crash site of Nuitka 4.3's signal-connection
    # regression; neither fonts nor this fixture were its established cause.
    pixels = np.empty((256, 384, 4), dtype=np.uint8)
    pixels[:] = (237, 240, 245, 255)
    y, x = np.ogrid[:256, :384]
    foreground = (x - 192) ** 2 + (y - 128) ** 2 <= 96 ** 2
    highlight = (x - 172) ** 2 * 19 ** 2 + (y - 71) ** 2 * 28 ** 2 <= 28 ** 2 * 19 ** 2
    pixels[foreground] = (160, 53, 36, 255)
    pixels[highlight] = (226, 99, 75, 255)
    return Image.fromarray(pixels)


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
    """Exercise image codecs after Qt startup, capture the window and exit."""
    import faulthandler
    import os

    output_directory.mkdir(parents=True, exist_ok=False)
    app = None
    window = None
    capture_timer = None
    watchdog = None
    quit_on_last_window_closed = None
    qt_messages = None
    native_faults = None
    previous_qt_handler = None
    qt_handler_installed = False
    fault_handler_installed = False
    message_handler_errors = []
    qt_details = {}
    image_io = {}
    scope = "ui_startup_image_io_project_and_capture"
    runtime = {
        "sys_executable": sys.executable,
        "process_exe": None,
        "argv": sys.argv,
        "working_directory": str(Path.cwd()),
        "environment": {name: os.environ.get(name) for name in (
            "QT_QPA_PLATFORM", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_DEBUG_PLUGINS",
        )},
    }
    startup_phase = "initialize"
    code = 1
    report = {"status": "error", "scope": scope}

    def checkpoint(phase: str, status: str = "running") -> None:
        nonlocal startup_phase
        startup_phase = phase
        # Closing this file flushes a usable checkpoint even if Qt later calls
        # abort(), bypassing Python exception handling and the final report.
        (output_directory / "ui-startup.json").write_text(json.dumps({
            "status": status, "phase": phase, "runtime": runtime, "qt": qt_details,
            "image_io": image_io,
        }, indent=2), encoding="utf-8")

    def record_error(exc: Exception, phase: str) -> None:
        nonlocal code, report
        code = 1
        report = {
            "status": "error",
            "scope": scope,
            "phase": phase,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    try:
        checkpoint("resolve_compiled_executable")
        runtime["process_exe"] = _compiled_executable()
        checkpoint("before_qt_import")
        qt_messages = (output_directory / "qt-messages.log").open("w", encoding="utf-8")
        native_faults = (output_directory / "python-fault.log").open("w", encoding="utf-8")
        if not faulthandler.is_enabled():
            faulthandler.enable(file=native_faults, all_threads=True)
            fault_handler_installed = True
        checkpoint("import_qt_core")
        from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTimer, qInstallMessageHandler, qVersion

        def qt_message_handler(message_type, context, message) -> None:
            try:
                qt_messages.write(f"{message_type} [{context.category}]: {message}\n")
                qt_messages.flush()
            except Exception as exc:
                message_handler_errors.append(f"{type(exc).__name__}: {exc}")
            if previous_qt_handler is not None:
                previous_qt_handler(message_type, context, message)
            # Qt still terminates after a fatal message; logging never changes
            # the native error or turns a failed startup into a successful test.

        previous_qt_handler = qInstallMessageHandler(qt_message_handler)
        qt_handler_installed = True
        library_paths = list(QCoreApplication.libraryPaths())
        qt_details.update({
            "version": qVersion(),
            "core_module_file": sys.modules["PySide6.QtCore"].__file__,
            "plugins_path": QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath),
            "prefix_path": QLibraryInfo.path(QLibraryInfo.LibraryPath.PrefixPath),
            "library_paths_before_configuration": library_paths,
            "windows_plugin_candidates_before_configuration": [
                {"path": str(Path(path) / "platforms" / "qwindows.dll"),
                 "exists": (Path(path) / "platforms" / "qwindows.dll").is_file()}
                for path in library_paths
            ],
        })
        checkpoint("import_qt_widgets")
        from PySide6.QtWidgets import QApplication
        from shiboken6 import delete

        checkpoint("import_editor")
        from .ui import EditorWindow

        checkpoint("configure_bundled_qt_plugins")
        plugins = _configure_bundled_qt_plugins()
        qt_details["configured_plugins_path"] = str(plugins) if plugins is not None else None
        library_paths = list(QCoreApplication.libraryPaths())
        qt_details["library_paths_before_app"] = library_paths
        qt_details["windows_plugin_candidates_before_app"] = [
            {"path": str(Path(path) / "platforms" / "qwindows.dll"),
             "exists": (Path(path) / "platforms" / "qwindows.dll").is_file()}
            for path in library_paths
        ]
        checkpoint("create_application")
        app = QApplication.instance() or QApplication(sys.argv[:1])
        qt_details["library_paths_after_app"] = list(QCoreApplication.libraryPaths())
        qt_details["application_directory"] = QCoreApplication.applicationDirPath()
        qt_details["platform"] = app.platformName()
        from .branding import APP_NAME, app_icon
        app.setApplicationName(APP_NAME)
        app.setOrganizationName(APP_NAME)
        app.setWindowIcon(app_icon())
        quit_on_last_window_closed = app.quitOnLastWindowClosed()
        # Exit only after the window and its children have been destroyed.
        app.setQuitOnLastWindowClosed(False)
        checkpoint("create_editor_window")
        window = EditorWindow()
        checkpoint("create_synthetic_photo")
        picture = _synthetic_photo()
        from .core import export_image, load_image

        # Exercise real encoder/decoder imports after QApplication exists.
        # Showing an in-memory Pillow fixture alone would miss this path.
        source_path = output_directory / "ui-input.png"
        checkpoint("export_synthetic_png_after_qt")
        export_image(picture, source_path)
        checkpoint("load_synthetic_png_after_qt")
        decoded = load_image(source_path)
        if decoded.size != picture.size or decoded.mode != picture.mode or decoded.tobytes() != picture.tobytes():
            raise ValueError("The synthetic PNG import did not preserve dimensions, mode and pixels.")
        image_io.update({
            "after_qt_initialization": True,
            "input_file": source_path.name,
            "input_dimensions": list(decoded.size),
            "input_mode": decoded.mode,
            "input_pixels_preserved": True,
        })
        checkpoint("set_document")
        window.set_document(decoded, source_path=source_path)
        checkpoint("set_language")
        window.set_language("de")
        checkpoint("show_window")
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
                checkpoint("window_destroyed")
                watchdog.stop()
            except Exception as exc:
                record_error(exc, "shutdown")
            finally:
                app.exit(code)

        def finish() -> None:
            capture_timer.stop()
            try:
                checkpoint("close_window")
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
                checkpoint(f"capture_{language}")
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
                checkpoint("read_current_document")
                current = window.document.current
                if current.size != picture.size or current.mode != picture.mode or current.tobytes() != picture.tobytes():
                    raise ValueError("The displayed document did not preserve the imported pixels.")
                image_io["document_pixels_preserved"] = True
                image_io["exports"] = {}
                for format_name, suffix in (("PNG", "png"), ("JPEG", "jpg"), ("WebP", "webp")):
                    export_path = output_directory / f"ui-export.{suffix}"
                    checkpoint(f"export_current_document_{suffix}")
                    export_image(current, export_path, source_path=window.document.source_path)
                    checkpoint(f"verify_exported_document_{suffix}")
                    exported = load_image(export_path)
                    if exported.size != current.size or exported.mode not in ("RGB", "RGBA"):
                        raise ValueError(f"The {format_name} export returned invalid dimensions or mode.")
                    if format_name == "JPEG":
                        if exported.mode != "RGB":
                            raise ValueError("The JPEG export must decode as RGB.")
                        validation = "dimensions_and_rgb_mode"
                    else:
                        # WebP may omit a fully opaque alpha channel. Compare
                        # all visible colour and alpha values in a common mode.
                        if exported.convert("RGBA").tobytes() != current.convert("RGBA").tobytes():
                            raise ValueError(f"The lossless {format_name} export did not preserve pixels.")
                        validation = "dimensions_and_exact_rgba_pixels"
                    image_io["exports"][format_name] = {
                        "file": export_path.name,
                        "dimensions": list(exported.size),
                        "mode": exported.mode,
                        "validation": validation,
                    }
                # The native application must also round-trip an editable
                # project. This catches omitted standard-library/modules in
                # a frozen binary that normal image export would not exercise.
                checkpoint("edit_and_save_project")
                source_bytes_before_project = source_path.read_bytes()
                window.rotate_clockwise()
                rotated = window.document.current
                if rotated.size != (picture.height, picture.width) or not window.document.can_undo:
                    raise ValueError("The editor did not apply the project test edit.")
                project_path = output_directory / "ui-session.laip"
                window._write_project(project_path)
                if not project_path.is_file():
                    raise OSError("The editor failed to save a local project.")
                checkpoint("reload_project")
                window.open_project_path(project_path)
                project = window.document
                if (
                    window._project_path != project_path.absolute()
                    or project.source_path is not None
                    or project.original.tobytes() != picture.tobytes()
                    or project.current.tobytes() != rotated.tobytes()
                    or not project.can_undo
                    or window._has_unexported_changes()
                ):
                    raise ValueError("The editor did not restore the editable project exactly.")
                checkpoint("project_undo_redo")
                window.undo()
                if project.current.tobytes() != picture.tobytes():
                    raise ValueError("Project Undo did not restore the imported pixels.")
                window.redo()
                if project.current.tobytes() != rotated.tobytes():
                    raise ValueError("Project Redo did not restore the edited pixels.")
                window.save_project()
                if window._has_unexported_changes() or source_path.read_bytes() != source_bytes_before_project:
                    raise ValueError("The project did not save cleanly.")
                checkpoint("manual_mask_refinement")
                before_mask = window.document.current
                window.mask_button.click()
                if not window.mask_button.isChecked():
                    raise ValueError("The foreground brush did not become available.")
                window.mask_mode_combo.setCurrentIndex(1)  # erase
                window.mask_feather_slider.setValue(0)
                window._mask_stroke_finished(((0.5, 0.5),))
                if not window.mask_apply_button.isEnabled():
                    raise ValueError("The foreground correction was not previewed.")
                if window.document.current.tobytes() != before_mask.tobytes():
                    raise ValueError("The foreground brush changed pixels before acceptance.")
                window.apply_mask_refinement()
                edited_mask = window.document.current
                middle = (edited_mask.width // 2, edited_mask.height // 2)
                if (
                    edited_mask.getpixel(middle)[3] != 0
                    or edited_mask.convert("RGB").tobytes() != before_mask.convert("RGB").tobytes()
                    or not window.document.can_undo
                ):
                    raise ValueError("Mask correction did not change alpha exclusively.")
                window.undo()
                if window.document.current.tobytes() != before_mask.tobytes():
                    raise ValueError("Mask correction Undo did not restore original alpha.")
                window.redo()
                if window.document.current.tobytes() != edited_mask.tobytes():
                    raise ValueError("Mask correction Redo did not restore the corrected alpha.")
                checkpoint("save_and_reopen_corrected_mask")
                window.save_project()
                window.open_project_path(project_path)
                if window.document.current.tobytes() != edited_mask.tobytes():
                    raise ValueError("Saved project did not restore the manually corrected mask.")
                if window._has_unexported_changes() or source_path.read_bytes() != source_bytes_before_project:
                    raise ValueError("Manual mask save changed the source image or left a dirty project.")
                image_io["project"] = {
                    "file": project_path.name,
                    "original_preserved": True,
                    "accepted_pixels_preserved": True,
                    "undo_redo_restored": True,
                    "manual_alpha_only_refinement": True,
                    "corrected_alpha_persisted": True,
                }
                report = {
                    "status": "ok",
                    "scope": scope,
                    "image_dimensions": list(picture.size),
                    "captures": captures,
                }
                code = 0
            except Exception as exc:
                record_error(exc, startup_phase)
            finish()

        def timed_out() -> None:
            record_error(TimeoutError("The UI smoke test did not finish within 30 seconds."), "event_loop")
            app.exit(1)

        window.destroyed.connect(window_destroyed)
        capture_timer.timeout.connect(capture_next)
        watchdog.timeout.connect(timed_out)
        capture_timer.start(100)
        watchdog.start(30_000)
        checkpoint("event_loop")
        loop_code = app.exec()
        if loop_code != 0 or code != 0 or window is not None:
            if report["status"] != "error" or "error_type" not in report:
                record_error(RuntimeError("The Qt event loop did not complete a clean shutdown."), "event_loop")
        report["event_loop_exit_code"] = loop_code
    except Exception as exc:
        record_error(exc, startup_phase)
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
        finally:
            if qt_handler_installed:
                qInstallMessageHandler(previous_qt_handler)
            if fault_handler_installed:
                faulthandler.disable()
            for stream in (qt_messages, native_faults):
                if stream is not None:
                    stream.close()
    report["qt"] = qt_details
    report["runtime"] = runtime
    report["image_io"] = image_io
    if message_handler_errors:
        report["message_handler_errors"] = message_handler_errors
    (output_directory / "ui-smoke-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    checkpoint("complete" if code == 0 else startup_phase, status=report["status"])
    return code


def tool_command(tool: str) -> tuple[str, list[str]]:
    """Spawn the same standalone EXE; source mode spawns the installed module."""
    if tool not in {"photo", "video", "audio"}:
        raise ValueError("Unknown editor type.")
    compiled = _compiled_executable()
    if compiled is not None:
        return compiled, ["--tool", tool]
    if getattr(sys, "frozen", False):
        return sys.executable, ["--tool", tool]
    return sys.executable, ["-m", "local_ai_photo_editor", "--tool", tool]


def media_job_command(operation: str, directory: str | Path) -> tuple[str, list[str]]:
    """Run built-in, local AI workers in the same packaged application."""
    if operation not in ("voice", "frame", "restore"):
        raise ValueError("Unsupported media AI operation.")
    executable = _compiled_executable()
    command = ["--media-ai-job", operation, str(directory)]
    if executable is not None:
        return executable, command
    if getattr(sys, "frozen", False):
        return sys.executable, command
    return sys.executable, ["-m", "local_ai_photo_editor", *command]


def launch_tool(tool: str) -> bool:
    """Detach each editor so closing another editor or the hub is harmless."""
    from PySide6.QtCore import QProcess
    program, arguments = tool_command(tool)
    started, _pid = QProcess.startDetached(program, arguments)
    return bool(started)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 2 and args[0] == "--worker":
        from .worker import run_job
        return run_job(Path(args[1]))
    if len(args) == 3 and args[0] == "--media-ai-job":
        if args[1] not in {"voice", "frame", "restore"}:
            return 2
        if args[1] == "restore":
            # Restoration's ProcessOwner installs its own Windows kill-on-close
            # Job Object. Do not assign the worker to a second, independent job:
            # that can fail on Windows and prevent all video previews.
            from .ai.video_restoration import restoration_worker
            return restoration_worker(Path(args[2]), _compiled_executable())
        from .core.process_tree import protect_media_ai_worker
        protect_media_ai_worker()  # Voice/frame jobs own nested FFmpeg before launch.
        if args[1] == "voice":
            from .ai.voice import voice_worker
            return voice_worker(Path(args[2]), _compiled_executable())
        from .ai.video_frame import frame_worker
        return frame_worker(Path(args[2]), _compiled_executable())
    if len(args) == 2 and args[0] == "--smoke-test":
        return smoke_test(Path(args[1]))
    if len(args) == 2 and args[0] == "--ui-smoke-test":
        return ui_smoke_test(Path(args[1]))
    if len(args) == 2 and args[0] == "--suite-smoke-test":
        _configure_bundled_qt_plugins()
        from .suite_smoke import suite_smoke
        return suite_smoke(Path(args[1]), _compiled_executable())
    if len(args) == 2 and args[0] == "--media-smoke-test":
        _configure_bundled_qt_plugins()
        from .media_smoke import media_smoke_test
        return media_smoke_test(Path(args[1]), _compiled_executable())
    if args in ([], ["--launcher"]):
        mode = "launcher"
    elif len(args) == 2 and args[0] == "--tool" and args[1] in {"photo", "video", "audio"}:
        mode = args[1]
    else:
        return 2

    from PySide6.QtWidgets import QApplication

    _configure_bundled_qt_plugins()
    app = QApplication(sys.argv[:1])
    from .branding import APP_NAME, app_icon
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(app_icon())
    if mode == "launcher":
        from .ui.launcher import LauncherWindow
        window = LauncherWindow(launch_tool)
    elif mode == "photo":
        from .ui import EditorWindow
        window = EditorWindow()
    else:
        from .ui.sequence_window import SequenceWindow
        window = SequenceWindow(mode, _compiled_executable())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

