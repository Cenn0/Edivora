"""Real source/standalone regression evidence using generated media only.

Windows constrains top-level windows to the physical test desktop. Oversized
client layouts are therefore tested as embedded widgets using the same native
Qt platform; the evidence records this distinction, never as desktop acceptance.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback


class _LayoutSurface:
    """Test exact client sizes without mistaking desktop bounds for UI defects."""
    def __init__(self, window):
        self.window = window
        self.flags = window.windowFlags()
        self.host = None

    def resize(self, width: int, height: int) -> str:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QWidget
        window = self.window
        available = window.screen().availableGeometry()
        # Reserve the same frame/taskbar margins as fit_initial_window. The
        # native test remains an actual, fully on-screen top-level window.
        room = (max(1, available.width() - 40), max(1, available.height() - 60))
        native = width <= room[0] and height <= room[1]
        if native:
            if window.parentWidget() is not None:
                window.setParent(None, self.flags)
            if self.host is not None:
                self.host.hide()
            window.resize(width, height)
            window.move(available.x() + 20, available.y() + 20)
            window.show()
            return "native-top-level"
        if self.host is None:
            self.host = QWidget()
            self.host.setWindowTitle("Edivora layout verification surface")
        self.host.resize(*room)
        self.host.move(available.x() + 20, available.y() + 20)
        if window.parentWidget() is not self.host:
            window.setParent(self.host, Qt.WindowType.Widget)
        window.move(0, 0)
        window.resize(width, height)
        self.host.show()
        window.show()
        return "embedded-native-client-layout"

    def close(self) -> None:
        if self.host is not None:
            self.host.close()
            self.host.deleteLater()
            self.host = None


def suite_smoke(output: Path, executable: str | None = None) -> int:
    from PySide6.QtCore import QSize, qVersion
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QAbstractButton, QAbstractSpinBox, QComboBox, QScrollArea, QSlider
    from .__main__ import _synthetic_photo, media_job_command
    from .ai.restoration import MODEL_SHA256, verified_bytes
    from .core.media import ffmpeg_executable
    from .core.media_project import MediaClip, MediaSequence, load_media_project, save_media_project
    from .core.video_adjustments import VideoAdjustments
    from .core.video_job import VideoJob
    from .ui.launcher import LauncherWindow
    from .ui.sequence_window import SequenceWindow
    from .ui.window import EditorWindow
    from .ui.responsive import in_viewport
    from .ui.video_dialog import VideoEnhancementDialog
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "executable": executable, "qt": qVersion(),
              "platform": os.environ.get("QT_QPA_PLATFORM"), "scale": os.environ.get("QT_SCALE_FACTOR", "1"),
              "scope": "synthetic source or standalone suite regression; native top-level windows where the desktop fits, embedded native-Qt client layouts otherwise; not Windows 11 / quality / licence approval",
              "layout_observations": []}
    windows = []
    surfaces = {}
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    ffmpeg = ffmpeg_executable(executable)

    def check(condition, message):
        if not condition:
            raise AssertionError(message)

    def wait(predicate, seconds=30):
        until = time.monotonic() + seconds
        while not predicate() and time.monotonic() < until:
            QTest.qWait(20)
        check(predicate(), "Timed out waiting for a real Qt/worker operation.")

    def phase(value):
        report["phase"] = value
        (output / "suite-smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def visible(widget, parent):
        check(widget.isVisibleTo(parent) and in_viewport(widget, parent),
              f"Clipped control: {widget.accessibleName()} / {widget.objectName()} in {parent.size()}")

    def reachable(window):
        for scroll in window.findChildren(QScrollArea):
            if not scroll.isVisibleTo(window):
                continue
            page = scroll.widget()
            for widget in (page.findChildren(QAbstractButton) + page.findChildren(QAbstractSpinBox)
                           + page.findChildren(QComboBox) + page.findChildren(QSlider)):
                if widget.isVisibleTo(page):
                    scroll.ensureWidgetVisible(widget, 0, 0)
                    QTest.qWait(5)
                    check(in_viewport(widget, scroll.viewport()),
                          f"Unreachable inspector control: {widget.accessibleName()}")
            scroll.verticalScrollBar().setValue(0)

    def capture(window, name):
        QTest.qWait(50)
        check(window.grab().save(str(output / (name + ".png"))), "Screenshot save failed.")

    def resize_and_check(window, name, language, width, height):
        if window not in surfaces:
            surfaces[window] = _LayoutSurface(window)
        mode = surfaces[window].resize(width, height)
        QTest.qWait(100)
        def wh(size):
            return [size.width(), size.height()]
        observation = {"window": name, "language": language, "requested": [width, height],
                       "actual": wh(window.size()), "minimum": wh(window.minimumSize()),
                       "minimum_hint": wh(window.minimumSizeHint()),
                       "maximum": wh(window.maximumSize()), "mode": mode,
                       "available_screen": wh(window.screen().availableGeometry().size()),
                       "device_pixel_ratio": window.devicePixelRatioF()}
        report["layout_observations"].append(observation)
        if window.size() != QSize(width, height):
            capture(window, f"resize-failure-{name}-{language}-{width}x{height}")
        check(window.size() == QSize(width, height), f"Window did not resize: {observation}")
        if mode == "native-top-level":
            check(window.screen().availableGeometry().contains(window.frameGeometry()),
                  f"Native window extends beyond the test desktop: {observation}")

    try:
        phase("verify_model")
        verified_bytes()
        report["restoration_model_sha256"] = MODEL_SHA256
        phase("generate_media")
        source = output / "synthetic-source.mp4"
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
            "testsrc2=size=128x96:rate=30", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "3", "-c:v", "mpeg4", "-c:a", "aac", str(source)], check=True, timeout=30)
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        clip = MediaClip.create("video", source, 3000)
        recipe = VideoAdjustments(exposure=12, saturation=-15, warmth=-20, denoise=15, sharpness=10)
        phase("real_cpu_worker")
        job = output / "neural-job"
        job.mkdir()
        request = VideoJob(source, 0, 400, 100, recipe, 60, "render")
        (job / "request.json").write_text(json.dumps(request.to_dict()), encoding="utf-8")
        program, args = media_job_command("restore", job)
        result = subprocess.run([program, *args], capture_output=True, timeout=90)
        check(result.returncode == 0, result.stderr.decode("utf-8", errors="replace")[-1000:])
        report["neural_result"] = json.loads((job / "result.json").read_text("utf-8"))
        check(report["neural_result"]["frames"] == 12, "Wrong restored frame count.")
        audio = subprocess.check_output([ffmpeg, "-v", "error", "-i", str(job / "output.mp4"),
            "-map", "0:a:0", "-f", "s16le", "pipe:1"], timeout=30)
        check(len(audio) > 20_000, "Restored clip lost its audio.")
        check(hashlib.sha256(source.read_bytes()).hexdigest() == original_hash, "Original was changed.")
        phase("project_v2")
        edited = replace(clip, video_adjustments=recipe)
        sequence = MediaSequence("video", (edited,), edited.id)
        project = output / "synthetic-project.edvp"
        save_media_project(sequence, project)
        check(load_media_project(project) == sequence, "Project recipe round-trip failed.")
        phase("native_layout_matrix")
        launched = []
        launcher = LauncherWindow(lambda tool: launched.append(tool) or True)
        photo = EditorWindow()
        photo.set_document(_synthetic_photo())
        video = SequenceWindow("video", executable)
        audio_window = SequenceWindow("audio", executable)
        windows.extend((launcher, photo, video, audio_window))
        for window in windows:
            window.show()
        video.open_path(source)
        wait(lambda: len(video.clips) == 1 and not video._loading)
        for language in ("de", "en"):
            photo.set_language(language)
            for window in (launcher, video, audio_window):
                window.language_combo.setCurrentIndex(0 if language == "de" else 1)
            for width, height in ((640, 480), (960, 540), (1280, 800), (1920, 1080)):
                for name, window in zip(("launcher", "photo", "video", "audio"), windows):
                    resize_and_check(window, name, language, width, height)
                    if name == "launcher":
                        for button in launcher.quick_buttons.values():
                            visible(button, launcher)
                    elif name == "photo":
                        for button in (photo.open_button, photo.export_button, photo.undo_button,
                                       photo.redo_button, photo.original_button, photo.language_combo):
                            visible(button, photo)
                        reachable(photo)
                    else:
                        for button in (window.open_button, window.export_button, window.save_project_button,
                                       window.undo_button, window.redo_button, window.play_button,
                                       window.stop_button, window.add_button, window.remove_button,
                                       window.split_button, window.duplicate_button, window.timeline):
                            visible(button, window)
                        for index in range(window.inspector_tabs.count()):
                            window.inspector_tabs.setCurrentIndex(index)
                            QTest.qWait(10)
                            reachable(window)
                        window.inspector_tabs.setCurrentIndex(0)
                    if width in (640, 1280):
                        capture(window, f"{name}-{language}-{width}")
        launcher.quick_buttons["photo"].click()
        launcher.quick_buttons["video"].click()
        launcher.quick_buttons["audio"].click()
        check(launched == ["photo", "video", "audio"] and launcher.isVisible(), "Launcher closed after opening tools.")
        phase("native_real_preview_dialog")
        for language in ("de", "en"):
            dialog = VideoEnhancementDialog(edited, 100, language, (source, project))
            windows.append(dialog)
            dialog.show()
            wait(lambda: dialog.apply_button.isEnabled())
            check(dialog.ai.isEnabled(), "Bundled neural model was not discovered in the GUI.")
            for width, height in ((640, 480), (1280, 800)):
                resize_and_check(dialog, "video-improve", language, width, height)
                for control in (dialog.preview_button, dialog.apply_button, dialog.cancel_button, dialog.compare):
                    visible(control, dialog)
                for index in range(dialog.tabs.count()):
                    dialog.tabs.setCurrentIndex(index)
                    QTest.qWait(10)
                    reachable(dialog)
                    capture(dialog, f"video-improve-{language}-{width}-tab{index}")
            dialog.sliders["exposure"].setValue(20)
            check(not dialog.apply_button.isEnabled(), "Stale preview could be accepted.")
            dialog.calculate_preview()
            wait(lambda: dialog.apply_button.isEnabled())
            dialog.apply()
            check(dialog.result_clip.video_adjustments.exposure == 20, "Recipe was not accepted.")
            dialog.close()
        phase("complete")
        check(hashlib.sha256(source.read_bytes()).hexdigest() == original_hash, "Original changed after UI checks.")
        report.update(status="ok", source_sha256=original_hash, actual_model_inference=True,
                      layouts=["640x480", "960x540", "1280x800", "1920x1080"], languages=["de", "en"])
        code = 0
    except Exception:
        report.update(status="error", traceback=traceback.format_exc())
        print(report["traceback"], flush=True)
        code = 1
    finally:
        for window in reversed(windows):
            if hasattr(window, "runner") and window.runner.busy:
                window.runner.cancel()
                wait(lambda: not window.runner.busy)
            if hasattr(window, "_dirty"):
                window._dirty = False
            window.close()
            window.deleteLater()
        for surface in surfaces.values():
            surface.close()
        app.processEvents()
        (output / "suite-smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return code
