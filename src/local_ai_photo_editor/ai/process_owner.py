"""Own encoder/decoder children, bound diagnostics, and stop blocked pipe jobs.

This is lifecycle management, not a native-decoder security sandbox.
"""
from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path
import subprocess
import threading
import time


class WindowsJob:
    """A worker-only, non-inheritable kill-on-close Job Object (Windows 8+)."""
    def __init__(self) -> None:
        self.handle = None
        self.parent_handle = None
        if os.name != "nt":
            return
        import ctypes as c
        from ctypes import wintypes as w
        class Basic(c.Structure):
            _fields_ = [("per_process", c.c_longlong), ("per_job", c.c_longlong),
                        ("flags", w.DWORD), ("min_ws", c.c_size_t), ("max_ws", c.c_size_t),
                        ("active", w.DWORD), ("affinity", c.c_size_t),
                        ("priority", w.DWORD), ("scheduling", w.DWORD)]
        class Io(c.Structure):
            _fields_ = [(name, c.c_ulonglong) for name in
                        ("read_ops", "write_ops", "other_ops", "read", "write", "other")]
        class Extended(c.Structure):
            _fields_ = [("basic", Basic), ("io", Io), ("process_memory", c.c_size_t),
                        ("job_memory", c.c_size_t), ("peak_process", c.c_size_t),
                        ("peak_job", c.c_size_t)]
        kernel = c.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        kernel.CreateJobObjectW.restype = w.HANDLE
        kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        kernel.SetInformationJobObject.restype = w.BOOL
        kernel.GetCurrentProcess.restype = w.HANDLE
        kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        kernel.AssignProcessToJobObject.restype = w.BOOL
        kernel.CloseHandle.argtypes = [w.HANDLE]
        kernel.CloseHandle.restype = w.BOOL
        self.kernel, self.ctypes, self.info = kernel, c, Extended()
        handle = kernel.CreateJobObjectW(None, None)
        if not handle:
            raise c.WinError(c.get_last_error())
        self.info.basic.flags = 0x00002000
        if not kernel.SetInformationJobObject(handle, 9, c.byref(self.info), c.sizeof(self.info)):
            error = c.get_last_error()
            kernel.CloseHandle(handle)
            raise c.WinError(error)
        if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
            error = c.get_last_error()
            kernel.CloseHandle(handle)  # No assigned process, safe to close.
            raise c.WinError(error)
        self.handle = handle
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.WaitForSingleObject.restype = w.DWORD
        self.parent_handle = kernel.OpenProcess(0x00100000, False, os.getppid())
        if not self.parent_handle:
            error = c.get_last_error()
            self.close()
            raise c.WinError(error)

    def parent_alive(self) -> bool:
        return self.parent_handle is None or self.kernel.WaitForSingleObject(self.parent_handle, 0) == 258

    def close(self) -> None:
        if self.parent_handle is not None:
            self.kernel.CloseHandle(self.parent_handle)
            self.parent_handle = None
        if self.handle is not None:
            # All children have been reaped first. Disarm before closing because
            # the worker itself belongs to the job and must return an exit code.
            c = self.ctypes
            self.info.basic.flags = 0
            if not self.kernel.SetInformationJobObject(
                    self.handle, 9, c.byref(self.info), c.sizeof(self.info)):
                raise c.WinError(c.get_last_error())
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class ProcessOwner:
    def __init__(self, folder: Path, timeout: float) -> None:
        self.folder, self.deadline = folder, time.monotonic() + timeout
        self.parent = os.getppid()
        self.children: list[subprocess.Popen] = []
        self.errors: dict[int, bytearray] = {}
        self.readers: list[threading.Thread] = []
        self.stopped = threading.Event()
        self.cancelled = threading.Event()
        self.lock = threading.Lock()
        self.job = WindowsJob()
        self.monitor = threading.Thread(target=self._watch, daemon=True)
        self.monitor.start()

    def _watch(self) -> None:
        while not self.stopped.wait(.1):
            if ((self.folder / "cancel").exists() or time.monotonic() > self.deadline
                    or os.getppid() != self.parent or not self.job.parent_alive()):
                self.cancelled.set()
                self.kill_children()
                return

    def check(self) -> None:
        if self.cancelled.is_set() or (self.folder / "cancel").exists():
            raise InterruptedError("Restoration cancelled or time limit exceeded.")

    def spawn(self, arguments: list[str], **kwargs) -> subprocess.Popen:
        self.check()
        with self.lock:
            self.check()
            child = subprocess.Popen(arguments, stderr=subprocess.PIPE,
                                     creationflags=0x08000000 if os.name == "nt" else 0,
                                     **kwargs)
            self.children.append(child)
            tail = self.errors[child.pid] = bytearray()
        def drain() -> None:
            try:
                while chunk := child.stderr.read(4096):
                    tail.extend(chunk)
                    del tail[:-32_768]
            finally:
                child.stderr.close()
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        self.readers.append(reader)
        return child

    def wait(self, child: subprocess.Popen, timeout: float = 60) -> None:
        code = child.wait(timeout=timeout)
        self.check()
        if code:
            message = self.errors[child.pid].decode("utf-8", errors="replace")[-1200:]
            raise RuntimeError("Media processing failed: " + message)

    def kill_children(self) -> None:
        with self.lock:
            for child in self.children:
                if child.poll() is None:
                    child.kill()

    def close(self) -> None:
        self.stopped.set()
        self.kill_children()
        for child in self.children:
            with suppress(subprocess.TimeoutExpired):
                child.wait(timeout=10)
            for stream in (child.stdin, child.stdout):
                if stream is not None:
                    with suppress(OSError):
                        stream.close()
        self.monitor.join(timeout=2)
        for reader in self.readers:
            reader.join(timeout=2)
        self.job.close()
