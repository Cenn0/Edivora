"""OS lifetime controls for nested local-media AI workers (not a sandbox).

Qt owns the outer worker QProcess. On POSIX, Qt must create that worker in a
new session; cancelling signals its entire process group. On Windows, the
worker joins a kill-on-close Job Object *before* it starts any FFmpeg process.
No new privileges, arbitrary subprocess commands or network access.
"""
from __future__ import annotations

import os
import signal


_WINDOWS_MEDIA_JOB_HANDLE = None


def protect_media_ai_worker() -> None:
    """Fail closed on Windows if native descendant lifetime cannot be bound."""
    global _WINDOWS_MEDIA_JOB_HANDLE
    if os.name != "nt":
        return
    if _WINDOWS_MEDIA_JOB_HANDLE is not None:
        return

    import ctypes
    from ctypes import wintypes

    class BasicLimitInfo(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class ExtendedLimitInfo(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInfo),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "Could not create media AI Job Object")
    try:
        limits = ExtendedLimitInfo()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise OSError(ctypes.get_last_error(), "Could not enable kill-on-job-close")
        if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
            raise OSError(ctypes.get_last_error(), "Could not contain local media AI process")
    except BaseException:
        kernel32.CloseHandle(job)
        raise
    # The *worker* holds the only application handle. Hard-killing the worker
    # closes it in the kernel, terminating all inherited FFmpeg descendants.
    # It must not be inherited by its child processes.
    _WINDOWS_MEDIA_JOB_HANDLE = job


def kill_media_ai_process_group(pid: int) -> bool:
    """Kill a Qt-owned POSIX session, including nested FFmpeg descendants.

    Return False only if the target is not a verified new-session leader,
    in which case callers should terminate the direct worker. Never signal
    a process group belonging to the application or an unrelated process.
    """
    if os.name == "nt" or type(pid) is not int or pid <= 0:
        return False
    try:
        if os.getpgid(pid) != pid:
            return False
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        # Qt may have reaped the worker during the cancellation request.
        pass
    return True
