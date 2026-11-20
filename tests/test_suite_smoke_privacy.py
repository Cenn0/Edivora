"""Regressions for public CI suite-smoke diagnostic privacy (synthetic data only)."""
from __future__ import annotations

import inspect
import json
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from local_ai_photo_editor import suite_smoke


class SuiteSmokePrivacyTests(unittest.TestCase):
    def test_failure_details_never_reflect_exception_message_or_untrusted_phase(self) -> None:
        detail = suite_smoke._safe_failure_details("neural-job", ValueError("synthetic-hidden-marker"))
        rendered = json.dumps(detail)
        self.assertEqual(detail["status"], "error")
        self.assertEqual(detail["error_phase"], "unknown")
        self.assertEqual(detail["error_type"], "ValueError")
        self.assertNotIn("synthetic-hidden-marker", rendered)
        self.assertNotIn("traceback", rendered)

    def test_failure_details_preserve_only_fixed_phase_names(self) -> None:
        detail = suite_smoke._safe_failure_details("real_cpu_worker", RuntimeError("synthetic-hidden-marker"))
        self.assertEqual(detail["error_phase"], "real_cpu_worker")
        self.assertNotIn("synthetic-hidden-marker", json.dumps(detail))

    def test_neural_worker_discards_child_output_and_raises_opaque_error(self) -> None:
        with patch.object(suite_smoke.subprocess, "run", return_value=SimpleNamespace(returncode=13)) as run:
            with self.assertRaisesRegex(RuntimeError, "^Neural worker subprocess failed\\.$") as raised:
                suite_smoke._run_neural_worker(["synthetic-worker", "--fixture"])
        run.assert_called_once_with(
            ["synthetic-worker", "--fixture"], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=90, check=False,
        )
        self.assertNotIn("synthetic-hidden-marker", str(raised.exception))

    def test_neural_worker_success_and_timeout_diagnostics(self) -> None:
        with patch.object(suite_smoke.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
            suite_smoke._run_neural_worker(["synthetic-worker"])
        timeout = subprocess.TimeoutExpired(["synthetic-hidden-marker"], 90)
        summary = suite_smoke._safe_failure_details("real_cpu_worker", timeout)
        self.assertEqual(summary["error_type"], "TimeoutExpired")
        self.assertNotIn("synthetic-hidden-marker", json.dumps(summary))

    def test_smoke_report_does_not_serialize_raw_paths_or_tracebacks(self) -> None:
        source = inspect.getsource(suite_smoke.suite_smoke)
        self.assertIn('"executable": "standalone" if executable else "source"', source)
        self.assertIn("_safe_failure_details(report.get", source)
        self.assertNotIn("traceback.format_exc", source)
        self.assertNotIn("result.stderr.decode", source)


if __name__ == "__main__":
    unittest.main()
