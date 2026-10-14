"""Local media export and Qt-startup smoke evidence for Windows artifacts.

Synthetic signals only. This is not a claim of manual, hardware or codec coverage.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import traceback

from .core.media import MediaExport, commit_export, ffmpeg_executable


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, timeout=60, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def media_smoke_test(directory: Path, compiled_executable: str | None = None) -> int:
    directory.mkdir(parents=True, exist_ok=False)
    report: dict[str, object] = {"status": "error", "phase": "engine", "scope": "synthetic_media_and_qt_shell"}
    try:
        ffmpeg = ffmpeg_executable(compiled_executable)
        report["engine"] = subprocess.check_output(
            [ffmpeg, "-version"], timeout=15
        ).decode("utf-8", "replace").splitlines()[0]
        source_video = directory / "input.mp4"
        source_audio = directory / "input.wav"
        _run([
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "2", "-c:v", "mpeg4", "-c:a", "aac", "-y", str(source_video),
        ])
        _run([
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000",
            "-t", "2", "-c:a", "pcm_s16le", "-y", str(source_audio),
        ])
        report["phase"] = "export_video"
        video = MediaExport(
            "video", source_video, directory / "video.mp4", 2000, 200, 1600, mute=True
        )
        temp_video = video.temp_output()
        _run([ffmpeg, *video.ffmpeg_arguments(temp_video)])
        commit_export(video, temp_video)
        report["video_bytes"] = video.destination.stat().st_size

        report["phase"] = "export_audio"
        audio = MediaExport(
            "audio", source_audio, directory / "audio.wav", 2000, 100, 1800,
            volume_percent=125, fade_in_ms=200, fade_out_ms=200,
        )
        temp_audio = audio.temp_output()
        _run([ffmpeg, *audio.ffmpeg_arguments(temp_audio)])
        commit_export(audio, temp_audio)
        report["audio_bytes"] = audio.destination.stat().st_size

        report["phase"] = "qt_shells"
        from PySide6.QtWidgets import QApplication
        from .ui.launcher import LauncherWindow
        from .ui.media_window import MediaWindow

        app = QApplication.instance() or QApplication([])
        windows = [
            ("launcher", LauncherWindow(lambda _: True)),
            ("video", MediaWindow("video", compiled_executable)),
            ("audio", MediaWindow("audio", compiled_executable)),
        ]
        snapshots = {}
        for name, window in windows:
            window.show()
            app.processEvents()
            screenshot = directory / f"{name}.png"
            if not window.grab().save(str(screenshot), "PNG") or screenshot.stat().st_size < 100:
                raise RuntimeError(f"Qt shell capture failed: {name}")
            snapshots[name] = screenshot.name
            window.close()
            window.deleteLater()
            app.processEvents()
        report["screenshots"] = snapshots
        report["phase"] = "complete"
        report["status"] = "ok"
        return 0
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        return 1
    finally:
        (directory / "media-smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
