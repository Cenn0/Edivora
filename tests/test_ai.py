from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from local_ai_photo_editor import __main__ as entry
from local_ai_photo_editor.ai.background import apply_mask, output_mask, prepare_input
from local_ai_photo_editor.ai.models import (
    MODEL_SHA256, MODEL_SIZE, ModelIntegrityError, ModelMissingError, verified_model_bytes,
)
from local_ai_photo_editor.worker import run_job


class InputPreparationTests(unittest.TestCase):
    def test_black_input_does_not_create_nan(self):
        source = Image.new("RGB", (3, 9), "black")
        value = prepare_input(source)
        self.assertEqual(value.shape, (1, 3, 320, 320))
        self.assertEqual(value.dtype, np.float32)
        self.assertTrue(value.flags.c_contiguous)
        self.assertTrue(np.isfinite(value).all())
        np.testing.assert_allclose(value[0, :, 0, 0], -np.array([.485, .456, .406]) / np.array([.229, .224, .225]), rtol=1e-6)

    def test_white_input_matches_upstream_normalization(self):
        actual = prepare_input(Image.new("RGB", (8, 8), "white"))
        np.testing.assert_allclose(actual[0, :, 0, 0], (1 - np.array([.485, .456, .406])) / np.array([.229, .224, .225]), rtol=1e-6)

    def test_preparation_never_mutates_source(self):
        source = Image.new("RGBA", (8, 8), (18, 52, 99, 31))
        before = source.tobytes()
        prepare_input(source)
        self.assertEqual(source.tobytes(), before)


class MaskTests(unittest.TestCase):
    def test_mask_multiplies_existing_alpha_and_preserves_colours(self):
        source = Image.new("RGBA", (3, 1), (80, 120, 255, 128))
        mask = Image.fromarray(np.array([[0, 128, 255]], dtype=np.uint8))
        result = apply_mask(source, mask)
        self.assertEqual(list(result.getchannel("A").tobytes()), [0, 64, 128])
        self.assertEqual(result.convert("RGB").tobytes(), source.convert("RGB").tobytes())
        self.assertEqual(source.getpixel((0, 0))[3], 128)

    def test_mask_dimensions_must_match(self):
        with self.assertRaises(ValueError):
            apply_mask(Image.new("RGB", (2, 2)), Image.new("L", (3, 3)))

    def test_prediction_is_resized_to_photo(self):
        output = np.linspace(0, 1, 320 * 320, dtype=np.float32).reshape(1, 1, 320, 320)
        result = output_mask(output, (640, 480))
        self.assertEqual(result.size, (640, 480))
        self.assertEqual(result.mode, "L")
        self.assertEqual(result.getextrema(), (0, 255))

    def test_rejects_constant_nonfinite_or_wrong_output(self):
        values = [np.ones((1, 1, 320, 320), dtype=np.float32), np.full((1, 1, 320, 320), np.nan), np.zeros((320, 320))]
        for value in values:
            with self.subTest(shape=value.shape), self.assertRaises(ValueError):
                output_mask(value, (20, 20))


class ModelIntegrityTests(unittest.TestCase):
    def test_missing_model_is_an_explicit_error(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ModelMissingError):
                verified_model_bytes(Path(root) / "absent.onnx")

    def test_rejects_wrong_size_and_same_size_wrong_digest(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "model.onnx"
            for data in (b"bad", bytes(MODEL_SIZE), bytes(MODEL_SIZE + 1)):
                target.write_bytes(data)
                with self.subTest(length=len(data)), self.assertRaises(ModelIntegrityError):
                    verified_model_bytes(target)

    def test_returns_the_verified_bytes_not_a_reopenable_path(self):
        payload = b"test-model-bytes"
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "model.onnx"
            target.write_bytes(payload)
            with patch("local_ai_photo_editor.ai.models.MODEL_SIZE", len(payload)), patch("local_ai_photo_editor.ai.models.MODEL_SHA256", hashlib.sha256(payload).hexdigest()):
                self.assertEqual(verified_model_bytes(target), payload)
        self.assertEqual(len(MODEL_SHA256), 64)


class WorkerTests(unittest.TestCase):
    def test_unknown_operations_are_rejected_without_loading_a_model(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "request.json").write_text(json.dumps({"version": 1, "operation": "run_python"}))
            self.assertEqual(run_job(directory), 1)
            status = json.loads((directory / "result.json").read_text())
            self.assertEqual(status["status"], "error")
            self.assertFalse((directory / "output.png").exists())

    def test_missing_model_does_not_trigger_a_download(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "request.json").write_text(json.dumps({"version": 1, "operation": "remove_background"}))
            Image.new("RGB", (16, 16), "white").save(directory / "input.png")
            with patch("local_ai_photo_editor.ai.background.verified_model_bytes", side_effect=ModelMissingError("missing")), patch("socket.socket", side_effect=AssertionError("Network use is forbidden")):
                self.assertEqual(run_job(directory), 1)
            self.assertEqual(json.loads((directory / "result.json").read_text())["code"], "MODEL_MISSING")
            self.assertFalse((directory / "output.png").exists())

    def test_cli_worker_reports_a_rejected_job_without_gui_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="worker path with spaces ") as root:
            directory = Path(root)
            (directory / "request.json").write_text(
                json.dumps({"version": 1, "operation": "unsupported"}), encoding="utf-8",
            )
            program, arguments = entry.worker_command(directory)
            completed = subprocess.run(
                [program, *arguments], capture_output=True, timeout=10, check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertEqual(json.loads((directory / "result.json").read_text())["status"], "error")


class WorkerCommandTests(unittest.TestCase):
    def test_packaged_worker_reuses_the_executable_without_a_python_module_switch(self):
        directory = Path("job with spaces")
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(entry.worker_command(directory), (sys.executable, ["--worker", str(directory)]))

    def test_nuitka_worker_uses_process_exe_instead_of_the_absent_python_executable(self):
        directory = Path("job with spaces")
        executable = str(Path("portable app") / "LocalAiPhotoEditor.exe")
        python_executable = str(Path("portable app") / "python.exe")
        compiled = SimpleNamespace(process_exe=executable)
        with patch.dict(entry.__dict__, {"__compiled__": compiled}), patch.object(sys, "executable", python_executable):
            self.assertEqual(entry.worker_command(directory), (executable, ["--worker", str(directory)]))

    def test_nuitka_worker_rejects_missing_process_exe_without_guessing_an_interpreter(self):
        with patch.dict(entry.__dict__, {"__compiled__": SimpleNamespace(process_exe=None)}):
            with self.assertRaisesRegex(RuntimeError, "executable path"):
                entry.worker_command("job")


class SmokeProtocolTests(unittest.TestCase):
    """Mocked process results validate the smoke harness, not model inference."""

    @staticmethod
    def _write_worker_result(command, outcome="ok"):
        directory = Path(command[-1])
        with Image.open(directory / "input.png") as source:
            result = source.convert("RGBA")
        if outcome == "wrong_size":
            result = result.resize((16, 16))
        if outcome == "transparent":
            result.putalpha(0)
        elif outcome != "opaque":
            red, green, blue, _ = result.getpixel((0, 0))
            result.putpixel((0, 0), (red, green, blue, 0))
        if outcome == "not_png":
            result.convert("RGB").save(directory / "output.png", format="JPEG")
        else:
            result.save(directory / "output.png", format="PNG")
        status = {"status": "error" if outcome == "error_status" else "ok"}
        (directory / "result.json").write_text(json.dumps(status), encoding="utf-8")
        return subprocess.CompletedProcess(command, 1 if outcome == "failed_exit" else 0)

    def test_smoke_invokes_the_worker_and_cleans_up_its_job(self):
        jobs = []

        def complete_job(command, **kwargs):
            directory = Path(command[-1])
            jobs.append(directory)
            self.assertEqual(command[-2], "--worker")
            self.assertEqual(
                json.loads((directory / "request.json").read_text()),
                {"version": 1, "operation": "remove_background"},
            )
            self.assertGreater(kwargs["timeout"], 0)
            return self._write_worker_result(command)

        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "smoke"
            with patch.object(entry.subprocess, "run", side_effect=complete_job) as runner:
                self.assertEqual(entry.smoke_test(output), 0)
            runner.assert_called_once()
            report = json.loads((output / "smoke-result.json").read_text())
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["scope"], "worker_runtime_only")
            self.assertEqual(report["worker"]["returncode"], 0)
            self.assertEqual(json.loads((output / "worker-result.json").read_text()), {"status": "ok"})
            with Image.open(output / "smoke-output.png") as result:
                self.assertEqual(result.size, (384, 256))
            self.assertFalse(jobs[0].exists())

    def test_worker_failure_or_invalid_artifacts_cannot_pass_the_smoke_test(self):
        outcomes = ("failed_exit", "error_status", "not_png", "wrong_size", "opaque", "transparent")
        with tempfile.TemporaryDirectory() as root:
            for outcome in outcomes:
                with self.subTest(outcome=outcome):
                    output = Path(root) / outcome
                    with patch.object(
                        entry.subprocess, "run",
                        side_effect=lambda command, **kwargs: self._write_worker_result(command, outcome),
                    ):
                        self.assertEqual(entry.smoke_test(output), 1)
                    report = json.loads((output / "smoke-result.json").read_text())
                    self.assertEqual(report["status"], "error")
                    self.assertEqual(
                        json.loads((output / "worker-result.json").read_text())["status"],
                        "error" if outcome == "error_status" else "ok",
                    )
                    self.assertFalse((output / "smoke-output.png").exists())

    def test_missing_executable_status_and_output_have_distinct_diagnostics(self):
        phases = ("start_and_wait_for_worker", "read_worker_status", "read_worker_output")
        with tempfile.TemporaryDirectory() as root:
            for phase in phases:
                with self.subTest(phase=phase):
                    jobs = []

                    def missing_file(command, **kwargs):
                        directory = Path(command[-1])
                        jobs.append(directory)
                        if phase == "start_and_wait_for_worker":
                            raise FileNotFoundError(2, "The executable does not exist.", command[0])
                        if phase == "read_worker_output":
                            (directory / "result.json").write_text('{"status": "ok"}', encoding="utf-8")
                        return subprocess.CompletedProcess(command, 0)

                    output = Path(root) / phase
                    with patch.object(entry.subprocess, "run", side_effect=missing_file):
                        self.assertEqual(entry.smoke_test(output), 1)
                    report = json.loads((output / "smoke-result.json").read_text())
                    self.assertEqual(report["phase"], phase)
                    self.assertEqual(report["error_type"], "FileNotFoundError")
                    self.assertTrue(report["error_message"])
                    self.assertIn("FileNotFoundError", report["traceback"])
                    self.assertEqual(report["worker"]["program"], sys.executable)
                    self.assertEqual(report["worker"]["arguments"][-2], "--worker")
                    if phase != "start_and_wait_for_worker":
                        self.assertEqual(report["worker"]["returncode"], 0)
                    self.assertFalse(jobs[0].exists())

    def test_timeout_reports_failure_and_removes_the_worker_job(self):
        jobs = []

        def timeout(command, **kwargs):
            jobs.append(Path(command[-1]))
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "timeout"
            with patch.object(entry.subprocess, "run", side_effect=timeout):
                self.assertEqual(entry.smoke_test(output), 1)
            report = json.loads((output / "smoke-result.json").read_text())
            self.assertEqual(report["error_type"], "TimeoutExpired")
            self.assertFalse(jobs[0].exists())


if __name__ == "__main__":
    unittest.main()

