"""One TUI per project: a pid file in goggles-data/.local/."""

from __future__ import annotations

import os
import time

from ..paths import Paths, read_json, write_json

# A launch that has not written its own pid after this many seconds failed.
LAUNCH_GRACE = 20.0


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def other_tui_pid(paths: Paths) -> int | None:
    """The pid of a live TUI for this project other than this process."""
    info = read_json(paths.pid)
    if isinstance(info, dict):
        pid = info.get("pid")
        if isinstance(pid, int) and pid != os.getpid() and pid_alive(pid):
            return pid
    return None


def tui_running(paths: Paths) -> bool:
    info = read_json(paths.pid)
    if not isinstance(info, dict):
        return False
    pid = info.get("pid")
    if isinstance(pid, int):
        return pid_alive(pid)
    launching = info.get("launching")
    return isinstance(launching, (int, float)) and time.time() - launching < LAUNCH_GRACE


def mark_launching(paths: Paths) -> None:
    write_json(paths.pid, {"pid": None, "launching": time.time()})


def claim(paths: Paths) -> None:
    write_json(paths.pid, {"pid": os.getpid(), "started": time.time()})


def release(paths: Paths) -> None:
    info = read_json(paths.pid)
    if isinstance(info, dict) and info.get("pid") in (os.getpid(), None):
        try:
            paths.pid.unlink()
        except OSError:
            pass
