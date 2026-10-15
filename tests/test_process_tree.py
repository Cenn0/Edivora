"""Regression checks for FFmpeg descendant ownership and cancellation."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from local_ai_photo_editor.core.process_tree import kill_media_ai_process_group


def _process_running(pid: int) -> bool:
    if os.name == "nt":
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.GetExitCodeProcess.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.restype = wintypes.BOOL
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            result = wintypes.DWORD()
            return bool(k32.GetExitCodeProcess(handle, ctypes.byref(result))) and result.value == 259
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # POSIX orphan children can briefly be zombies awaiting init to reap.
    status = Path(f"/proc/{pid}/stat")
    if status.exists():
        try:
            return status.read_text("utf-8").split(") ", 1)[-1][:1] != "Z"
        except FileNotFoundError:
            return False
    return True


class MediaAiProcessTreeTests(unittest.TestCase):
    def test_cancellation_terminates_real_nested_child(self) -> None:
        # The synthetic child never touches media, models or the network.
        worker = """
import subprocess, sys, time
from local_ai_photo_editor.core.process_tree import protect_media_ai_worker
protect_media_ai_worker()
child = subprocess.Popen(
    [sys.executable, '-c', 'import time; time.sleep(12)'],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(child.pid, flush=True)
time.sleep(12)
"""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        with subprocess.Popen(
            [sys.executable, "-u", "-c", worker],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env,
            start_new_session=(os.name != "nt"),
        ) as supervisor:
            assert supervisor.stdout is not None
            assert supervisor.stderr is not None
            line = supervisor.stdout.readline().strip()
            if not line:
                self.fail("The native media AI worker did not initialize: " + supervisor.stderr.read()[-500:])
            child_pid = int(line)
            try:
                self.assertTrue(_process_running(child_pid))
                if os.name != "nt":
                    self.assertTrue(kill_media_ai_process_group(supervisor.pid))
                else:
                    supervisor.kill()  # worker's Job Object closes and kills its descendants
                supervisor.wait(timeout=5)
                deadline = time.monotonic() + 4
                while _process_running(child_pid) and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertFalse(_process_running(child_pid), "FFmpeg-like descendant survived cancellation")
            finally:
                if supervisor.poll() is None:
                    supervisor.kill()
                    supervisor.wait(timeout=5)
                if _process_running(child_pid):
                    if os.name == "nt":
                        # A failed test must not leave a synthetic process alive.
                        subprocess.run(["taskkill", "/PID", str(child_pid), "/F"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       timeout=5, check=False)
                    else:
                        os.kill(child_pid, signal.SIGKILL)

    @unittest.skipIf(os.name == "nt", "Unix process groups are not a Windows cancellation primitive")
    def test_never_signals_an_unrelated_process_group(self) -> None:
        with patch("os.getpgid", return_value=99999), patch("os.killpg") as kill:
            self.assertFalse(kill_media_ai_process_group(12345))
            kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
