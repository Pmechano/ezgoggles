"""`ezgoggles open`: start the TUI in a new terminal window, once per project.

The only rule: if the TUI is not running, start it. We never block exit,
never restart it in the background, and never keep anything resident.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .paths import Paths, read_json, write_json

# A launch that has not written its own pid after this many seconds failed.
LAUNCH_GRACE = 20.0


# ---------- pid file ----------

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


def tui_running(paths: Paths) -> bool:
    info = read_json(paths.pid)
    if not isinstance(info, dict):
        return False
    pid = info.get("pid")
    if isinstance(pid, int):
        return pid_alive(pid)
    launching = info.get("launching")
    return isinstance(launching, (int, float)) and time.time() - launching < LAUNCH_GRACE


def claim_pid(paths: Paths) -> None:
    write_json(paths.pid, {"pid": os.getpid(), "started": time.time()})


def release_pid(paths: Paths) -> None:
    info = read_json(paths.pid)
    if isinstance(info, dict) and info.get("pid") == os.getpid():
        try:
            paths.pid.unlink()
        except OSError:
            pass


# ---------- platform ----------

def is_wsl() -> bool:
    if sys.platform != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower()
    except OSError:
        return False


def tui_argv(paths: Paths) -> list[str]:
    return [sys.executable, "-m", "ezgoggles", "tui", "--root", str(paths.root)]


def manual_command(paths: Paths) -> str:
    """The command a user can type to start the TUI by hand."""
    plugin = Path(__file__).resolve().parents[2]
    try:
        plugin_arg = plugin.relative_to(paths.root).as_posix()
    except ValueError:
        plugin_arg = str(plugin)
    return f'cd "{paths.root}" && uv run --project {plugin_arg} ezgoggles tui'


def window_title(paths: Paths) -> str:
    return f"ezgoggles - {paths.root.name}"


def launch_commands(paths: Paths) -> list[tuple[list[str], dict]]:
    """Candidate (argv, Popen kwargs) pairs for this platform, best first."""
    argv = tui_argv(paths)
    title = window_title(paths)
    root = str(paths.root)
    out: list[tuple[list[str], dict]] = []

    if os.name == "nt":
        wt = shutil.which("wt")
        if wt:
            out.append(([wt, "-w", "new", "new-tab", "--title", title, "-d", root, *argv], {}))
        out.append((argv, {"creationflags": subprocess.CREATE_NEW_CONSOLE, "cwd": root}))
        return out

    if sys.platform == "darwin":
        script = f"cd {shlex.quote(root)} && exec {shlex.join(argv)}"
        script = script.replace("\\", "\\\\").replace('"', '\\"')
        out.append(([
            "osascript",
            "-e", f'tell application "Terminal" to do script "{script}"',
            "-e", 'tell application "Terminal" to activate',
        ], {}))
        return out

    if is_wsl():
        distro = os.environ.get("WSL_DISTRO_NAME", "")
        inner = ["wsl.exe", *(["-d", distro] if distro else []), "--cd", root, "--", *argv]
        # cmd.exe complains when its working dir is a Linux path.
        win_cwd = "/mnt/c" if Path("/mnt/c").is_dir() else None
        wt = shutil.which("wt.exe")
        if wt:
            out.append(([wt, "-w", "new", "new-tab", "--title", title, *inner], {"cwd": win_cwd}))
        if shutil.which("cmd.exe"):
            out.append((["cmd.exe", "/c", "start", title, *inner], {"cwd": win_cwd}))
        return out

    # Ubuntu (GNOME). Other Linux desktops are not supported.
    if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and shutil.which(
        "gnome-terminal"
    ):
        out.append((["gnome-terminal", f"--title={title}", f"--working-directory={root}", "--", *argv], {}))
    return out


def _spawn(argv: list[str], kwargs: dict) -> bool:
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    if os.name != "nt":
        kwargs.setdefault("start_new_session", True)
    try:
        subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except OSError:
        return False
    return True


def open_tui(paths: Paths) -> str:
    """Start the TUI if it is not running. Return 'running', 'started' or 'manual'."""
    if tui_running(paths):
        return "running"
    write_json(paths.pid, {"pid": None, "launching": time.time()})
    for argv, kwargs in launch_commands(paths):
        if _spawn(argv, kwargs):
            return "started"
    try:
        paths.pid.unlink()
    except OSError:
        pass
    return "manual"
