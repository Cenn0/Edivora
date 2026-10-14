"""Local media export and Qt-startup smoke evidence for Windows artifacts.

Synthetic signals only. This is not a claim of manual, hardware or codec coverage.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
import traceback

from .core.media import MediaExport, commit_export, ffmpeg_executable
from .core.media_project import load_media_project, save_media_project
from .core.media_sequence import SequenceExport, commit_sequence_export
from .ai.voice import analyze_voice, verified_voice_model
from .ai.video_frame import extract_ai_frame


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
            if name in {"video", "audio"}:
                media = source_video if name == "video" else source_audio
                window.open_path(media)
                deadline = time.monotonic() + 12
                while window.duration_ms <= 0 and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.04)
                if window.duration_ms <= 0:
                    raise RuntimeError(
                        f"Qt Multimedia failed to determine duration for synthetic {name}; "
                        "packaged playback backend may be missing."
                    )
                report[f"{name}_qt_duration_ms"] = window.duration_ms
                # The visual range must be identical to the validated
                # duration/range used for a real FFmpeg export.
                window.timeline._edit_boundary("start", 300)
                window.timeline._edit_boundary("end", 1500)
                if (round(window.start_spin.value() * 1000),
                    round(window.end_spin.value() * 1000)) != (300, 1500):
                    raise RuntimeError(f"Timeline-to-export sync failed for {name}")
                extension = ".mp4" if name == "video" else ".wav"
                timeline_plan = window._build_export(
                    directory / f"timeline-export-{name}{extension}"
                )
                temp = timeline_plan.temp_output()
                _run([ffmpeg, *timeline_plan.ffmpeg_arguments(temp)])
                commit_export(timeline_plan, temp)
                report[f"{name}_timeline_export_bytes"] = timeline_plan.destination.stat().st_size
                report[f"{name}_selected_range_ms"] = [300, 1500]
                if name == "audio":
                    # Waveform generation is asynchronous and never blocks
                    # media loading. Capture only after the short sample finishes.
                    deadline = time.monotonic() + 12
                    while window._wave_process is not None and time.monotonic() < deadline:
                        app.processEvents()
                        time.sleep(0.04)
            screenshot = directory / f"{name}.png"
            if not window.grab().save(str(screenshot), "PNG") or screenshot.stat().st_size < 100:
                raise RuntimeError(f"Qt shell capture failed: {name}")
            snapshots[name] = screenshot.name
            window.close()
            window.deleteLater()
            app.processEvents()
        report["screenshots"] = snapshots

        report["phase"] = "multi_clip_project_and_export"
        from .ui.sequence_window import SequenceWindow

        sequence_captures = {}
        for kind, file in (("video", source_video), ("audio", source_audio)):
            window = SequenceWindow(kind, compiled_executable)
            window.show()
            app.processEvents()
            try:
                # Load one real clip, then append another instance (not a
                # mocked list). Validate both QMediaPlayer and project model.
                for number in range(2):
                    window.open_path(file)
                    deadline = time.monotonic() + 12
                    while len(window.clips) <= number and time.monotonic() < deadline:
                        app.processEvents()
                        time.sleep(0.04)
                    if len(window.clips) != number + 1:
                        raise RuntimeError(f"Could not import media clip {number + 1} into {kind}.")
                window.clips[0] = window.clips[0].__class__(
                    **{**window.clips[0].__dict__, "start_ms": 100, "end_ms": 1000}
                )
                window.clips[1] = window.clips[1].__class__(
                    **{**window.clips[1].__dict__, "start_ms": 200, "end_ms": 1100}
                )
                project = directory / f"multi-{kind}.{ 'edvp' if kind == 'video' else 'edap'}"
                save_media_project(window._snapshot(), project)
                loaded = load_media_project(project)
                if len(loaded.clips) != 2 or loaded.length_ms != 1800:
                    raise RuntimeError("Multi-clip project round trip changed clip order/ranges.")
                extension = ".mp4" if kind == "video" else ".wav"
                plan = SequenceExport(loaded, directory / f"multi-{kind}{extension}")
                temporary = plan.temp_output()
                _run([ffmpeg, *plan.ffmpeg_arguments(temporary)])
                commit_sequence_export(plan, temporary)
                if plan.destination.stat().st_size <= 1000:
                    raise RuntimeError("Multi-clip render produced no useful output.")
                report[f"{kind}_multi_bytes"] = plan.destination.stat().st_size
                screenshot = directory / f"sequence-{kind}.png"
                if not window.grab().save(str(screenshot), "PNG"):
                    raise RuntimeError(f"Sequence {kind} capture failed.")
                sequence_captures[kind] = screenshot.name
            finally:
                window._dirty = False
                window.close()
                window.deleteLater()
                app.processEvents()
        report["sequence_screenshots"] = sequence_captures

        # Real local AI inference, independently of empty/mock GUI actions:
        # one Silero voice inference and one pinned U2NETP still-frame cutout.
        report["phase"] = "local_ai"
        verified_voice_model()
        voice_ranges = analyze_voice(source_audio, 100, 1600, ffmpeg=ffmpeg)
        report["voice_segments"] = voice_ranges
        # The existing photo smoke subject is a deterministic synthetic circle.
        from .__main__ import _synthetic_photo
        still = directory / "ai-source.png"
        _synthetic_photo().save(still)
        moving = directory / "ai-video.mp4"
        _run([
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(still), "-t", "1",
            "-vf", "fps=10", "-c:v", "mpeg4", "-y", str(moving),
        ])
        extracted = directory / "ai-frame.png"
        extract_ai_frame(moving, 200, extracted, ffmpeg=ffmpeg)
        if not extracted.is_file() or extracted.stat().st_size <= 1000:
            raise RuntimeError("Local video-frame AI did not create the PNG.")
        report["ai_frame_bytes"] = extracted.stat().st_size

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
