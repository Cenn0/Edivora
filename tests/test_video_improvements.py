"""Real FFmpeg corrections, strict project migration, CPU inference and job safety."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from local_ai_photo_editor.ai.restoration import Denoiser, model_available, verified_bytes
from local_ai_photo_editor.core.media import ffmpeg_executable
from local_ai_photo_editor.core.media_history import MediaHistory, same_content
from local_ai_photo_editor.core.media_project import MediaClip, MediaSequence, load_media_project, save_media_project
from local_ai_photo_editor.core.media_sequence import SequenceExport, commit_sequence_export
from local_ai_photo_editor.core.video_adjustments import PRESETS, VideoAdjustments
from local_ai_photo_editor.core.video_job import VideoJob, install_restored_clip, validate_destination


def fixture(root: Path, *, audio: bool = True, seconds: str = "0.4") -> Path:
    source = root / ("source.mp4" if audio else "silent.mp4")
    args = [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
            "testsrc2=size=128x96:rate=30"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
    args += ["-t", seconds, "-c:v", "mpeg4", "-c:a", "aac", "-y", str(source)]
    subprocess.run(args, check=True, capture_output=True, timeout=30)
    return source


class VideoProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.mp4"
        self.source.write_bytes(b"fixture" * 300)
        self.clip = MediaClip.create("video", self.source, 1000, has_audio=False)

    def test_adjustment_bounds_types_and_unknown_fields(self):
        for key in VideoAdjustments.__dataclass_fields__:
            for value in (True, 2.5, "1", float("nan"), 101, -101):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    VideoAdjustments(**{key: value}).validated()
        for data in ({}, {"unknown": 2}, {**VideoAdjustments().to_dict(), "filter": "movie=x"}):
            with self.assertRaises(ValueError):
                VideoAdjustments.from_dict(data)
        self.assertFalse(VideoAdjustments().has_effect)
        self.assertEqual(VideoAdjustments().filters(), [])

    def test_project_v2_persists_recipe_and_reads_strict_legacy_v1(self):
        recipe = VideoAdjustments(exposure=12, warmth=-25, denoise=20)
        seq = MediaSequence("video", (replace(self.clip, video_adjustments=recipe),), self.clip.id)
        path = self.root / "project.edvp"
        save_media_project(seq, path)
        self.assertEqual(load_media_project(path), seq)
        data = json.loads(path.read_text("utf-8"))
        self.assertEqual(data["version"], 2)
        data["version"] = 1
        data["clips"][0].pop("video_adjustments")
        path.write_text(json.dumps(data), encoding="utf-8")
        old = load_media_project(path)
        self.assertEqual(old.clips[0].video_adjustments, VideoAdjustments())
        data["version"] = 2
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_media_project(path)

    def test_project_save_protects_hardlinked_original(self):
        alias = self.root / "alias.edvp"
        os.link(self.source, alias)
        before = self.source.read_bytes()
        with self.assertRaises(ValueError):
            save_media_project(MediaSequence("video", (self.clip,), self.clip.id), alias)
        self.assertEqual(self.source.read_bytes(), before)

    def test_job_rejects_unknown_keys_duplicate_json_and_invalid_ranges(self):
        valid = VideoJob(self.source, 0, 1000, 100, VideoAdjustments()).to_dict()
        for change in ({"strength": True}, {"mode": "shell"}, {"at_ms": 1000},
                       {"source": "https://example.invalid/x.mp4"}, {"end_ms": 7_200_001},
                       {"mode": "render", "strength": 50, "end_ms": 30_001}, {"unknown": 1}):
            (self.root / "request.json").write_text(json.dumps({**valid, **change}))
            with self.subTest(change=change), self.assertRaises((ValueError, OSError)):
                VideoJob.read(self.root)
        (self.root / "request.json").write_text('{"mode":"preview","mode":"render"}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            VideoJob.read(self.root)
        (self.root / "request.json").write_bytes(b"x" * 16_385)
        with self.assertRaises(ValueError):
            VideoJob.read(self.root)

    def test_derived_export_protects_aliases_and_is_atomic(self):
        destination = self.root / "result.mp4"
        destination.write_bytes(b"existing output")
        stage = self.root / ".stage"
        stage.mkdir()
        output = stage / "output.mp4"
        output.write_bytes(b"complete new output")
        install_restored_clip(output, destination, (self.source,))
        self.assertEqual(destination.read_bytes(), b"complete new output")
        with self.assertRaises(ValueError):
            validate_destination(self.source, (self.source,))
        alias = self.root / "alias.mp4"
        os.link(self.source, alias)
        with self.assertRaises(ValueError):
            validate_destination(alias, (self.source,))
        output.write_bytes(b"")
        with self.assertRaises(ValueError):
            install_restored_clip(output, destination, (self.source,))
        self.assertEqual(destination.read_bytes(), b"complete new output")

    def test_history_is_bounded_coalesces_and_discards_redo_after_edit(self):
        empty = MediaSequence("video", ())
        first = MediaSequence("video", (self.clip,), self.clip.id)
        history = MediaHistory(empty, limit=4)
        history.record(first)
        for volume in (50, 60, 70):
            history.record(replace(first, clips=(replace(self.clip, volume_percent=volume),)), "volume")
        self.assertEqual(len(history.states), 3)
        self.assertEqual(history.undo(), first)
        self.assertEqual(history.undo(), empty)
        self.assertTrue(history.can_redo)
        history.record(first)
        self.assertFalse(history.can_redo)
        for exposure in range(8):
            history.record(replace(first, clips=(replace(self.clip,
                video_adjustments=VideoAdjustments(exposure=exposure)),)))
        self.assertEqual(len(history.states), 4)
        self.assertTrue(same_content(first, replace(first, selected_id=None)))


class ActualVideoCorrectionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = fixture(self.root)
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def test_every_preset_and_extreme_controls_decode_to_actual_frames(self):
        from local_ai_photo_editor.ai.video_restoration import run_job
        from PIL import Image
        previews = []
        recipes = [*PRESETS.values(), VideoAdjustments(100, -100, 100, -100, 100, 100, 100)]
        for recipe in recipes:
            with tempfile.TemporaryDirectory(dir=self.root) as temporary:
                folder = Path(temporary)
                job = VideoJob(self.source, 0, 400, 100, recipe)
                (folder / "request.json").write_text(json.dumps(job.to_dict()))
                self.assertTrue(run_job(folder)["ok"])
                with Image.open(folder / "after.png") as picture:
                    previews.append(np.asarray(picture).copy())
        self.assertTrue(any(not np.array_equal(previews[0], p) for p in previews[1:]))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.digest)

    def test_real_hd_full_hd_export_and_original_protection(self):
        clip = MediaClip.create("video", self.source, 400,
            video_adjustments=VideoAdjustments(exposure=15, saturation=-20))
        for profile, dimensions in (("hd", (1280, 720)), ("full_hd", (1920, 1080))):
            dest = self.root / f"{profile}.mp4"
            plan = SequenceExport(MediaSequence("video", (clip,), clip.id), dest, profile)
            temp = plan.temp_output()
            args = plan.ffmpeg_arguments(temp)
            self.assertIn("eq=", args[args.index("-filter_complex") + 1])
            result = subprocess.run([ffmpeg_executable(), *args], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            commit_sequence_export(plan, temp)
            decoded = subprocess.run([ffmpeg_executable(), "-hide_banner", "-loglevel", "error",
                "-i", str(dest), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                capture_output=True, timeout=30, check=True)
            import io
            from PIL import Image
            with Image.open(io.BytesIO(decoded.stdout)) as image:
                self.assertEqual(image.size, dimensions)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.digest)

    def test_watchdog_interrupts_a_blocked_child(self):
        from local_ai_photo_editor.ai.process_owner import ProcessOwner
        owner = ProcessOwner(self.root, 30)
        self.addCleanup(owner.close)
        child = owner.spawn([sys.executable, "-c", "import time; time.sleep(60)"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        (self.root / "cancel").touch()
        with self.assertRaises(InterruptedError):
            owner.wait(child, timeout=5)
        self.assertIsNotNone(child.poll())


@unittest.skipUnless(model_available(), "Real DnCNN tests require the verified build-time model.")
class ActualNeuralRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.denoiser = Denoiser()

    def test_real_model_reduces_synthetic_noise_without_mutating_input(self):
        noisy = np.rint(np.clip(.5 + np.random.default_rng(7).normal(0, .08, (64, 64, 3)), 0, 1) * 255).astype(np.uint8)
        original = noisy.copy()
        with patch("socket.socket.connect", side_effect=AssertionError("No network")):
            cleaned = self.denoiser.apply(noisy, 100)
        self.assertTrue(np.array_equal(noisy, original))
        before = np.mean((noisy.astype(float) - 127.5) ** 2)
        after = np.mean((cleaned.astype(float) - 127.5) ** 2)
        self.assertLess(after, before * .2)
        self.assertTrue(np.array_equal(self.denoiser.apply(noisy, 0), noisy))

    def test_tiles_match_full_frame_inference_at_seams(self):
        rgb = np.random.default_rng(12).integers(60, 195, (173, 187, 3), dtype=np.uint8)
        source = rgb.astype(np.float32) / 255
        full = self.denoiser.session.run(["output"], {"input": np.ascontiguousarray(source.transpose(2, 0, 1)[None])})[0]
        expected = np.rint(np.clip(full[0].transpose(1, 2, 0), 0, 1) * 255).astype(np.uint8)
        actual = self.denoiser.apply(rgb, 100)
        self.assertLessEqual(int(np.max(np.abs(actual.astype(int) - expected.astype(int)))), 1)
        with self.assertRaises(InterruptedError):
            self.denoiser.apply(rgb, 100, lambda: True)

    def test_invalid_arrays_and_tampered_model_fail_closed(self):
        for image, strength in ((np.zeros((3, 3)), 10), (np.zeros((1, 1, 3), dtype=np.uint8), True)):
            with self.assertRaises(ValueError):
                self.denoiser.apply(image, strength)
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "bad.onnx"
            from local_ai_photo_editor.ai.restoration import MODEL_BYTES
            bad.write_bytes(b"x" * MODEL_BYTES)
            with patch("local_ai_photo_editor.ai.restoration.model_path", return_value=bad):
                with self.assertRaises(ValueError):
                    verified_bytes()

    def test_neural_video_preserves_audio_and_supports_silent_clips(self):
        from local_ai_photo_editor.ai.video_restoration import run_job
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for has_audio in (True, False):
                source = fixture(root, audio=has_audio)
                before = source.read_bytes()
                with tempfile.TemporaryDirectory(dir=root) as working:
                    folder = Path(working)
                    request = VideoJob(source, 0, 400, 100, VideoAdjustments(exposure=10), 60, "render")
                    (folder / "request.json").write_text(json.dumps(request.to_dict()))
                    result = run_job(folder)
                    self.assertEqual(result["frames"], 12)
                    self.assertEqual(result["duration_ms"], 400)
                    self.assertEqual((result["width"], result["height"]), (128, 96))
                    if has_audio:
                        audio = subprocess.run([ffmpeg_executable(), "-hide_banner", "-loglevel", "error",
                            "-i", str(folder / "output.mp4"), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                            "-f", "s16le", "pipe:1"], check=True, capture_output=True, timeout=15)
                        self.assertGreater(len(audio.stdout), 10_000)
                        self.assertGreater(np.abs(np.frombuffer(audio.stdout, dtype=np.int16).astype(int)).max(), 0)
                self.assertEqual(source.read_bytes(), before)

@unittest.skipUnless(model_available(), "Verified DnCNN model required.")
class WorkerOwnershipTests(unittest.TestCase):
    def test_force_stopping_owned_worker_reaps_native_children(self):
        import queue
        import signal
        import threading
        import time
        from local_ai_photo_editor.__main__ import media_job_command
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = fixture(root, seconds="3")
            job = root / "job"
            job.mkdir()
            request = VideoJob(source, 0, 3000, 100, VideoAdjustments(), 60, "render")
            (job / "request.json").write_text(json.dumps(request.to_dict()))
            program, args = media_job_command("restore", job)
            child = subprocess.Popen([program, *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     start_new_session=os.name != "nt", text=True)
            events = queue.Queue()
            def drain():
                try:
                    for line in child.stdout:
                        events.put(json.loads(line))
                finally:
                    child.stdout.close()
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            pids = []
            try:
                until = time.monotonic() + 15
                while time.monotonic() < until:
                    event = events.get(timeout=max(.1, until - time.monotonic()))
                    if "children" in event:
                        pids = event["children"]
                        break
                self.assertEqual(len(pids), 2)
                if os.name == "nt":
                    child.kill()  # kill-on-close Job Object, not taskkill / all processes
                else:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)
                def running(pid):
                    if os.name == "nt":
                        import ctypes as c
                        from ctypes import wintypes as w
                        kernel = c.WinDLL("kernel32", use_last_error=True)
                        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
                        kernel.OpenProcess.restype = w.HANDLE
                        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
                        kernel.WaitForSingleObject.restype = w.DWORD
                        kernel.CloseHandle.argtypes = [w.HANDLE]
                        handle = kernel.OpenProcess(0x00100000, False, pid)
                        if not handle:
                            return False
                        try:
                            return kernel.WaitForSingleObject(handle, 0) == 258
                        finally:
                            kernel.CloseHandle(handle)
                    try:
                        return Path(f"/proc/{pid}/stat").read_text().split(")", 1)[1].split()[0] != "Z"
                    except FileNotFoundError:
                        return False
                until = time.monotonic() + 10
                while any(running(pid) for pid in pids) and time.monotonic() < until:
                    time.sleep(.05)
                self.assertFalse(any(running(pid) for pid in pids), "Native encoder/decoder outlived their worker.")
            finally:
                if child.poll() is None:
                    if os.name == "nt":
                        child.kill()
                    else:
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
                reader.join(timeout=2)
