"""Ways to open a new terminal window that runs the TUI.

Extension point: subclass Launcher, implement `available` and `command`,
and add an instance to LAUNCHERS. `open` tries the available launchers in
list order and uses the first one that starts.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..paths import Paths


@dataclass
class Command:
    argv: list[str]
    popen: dict = field(default_factory=dict)


def tui_argv(paths: Paths) -> list[str]:
    return [sys.executable, "-m", "ezgoggles", "tui", "--root", str(paths.root)]


def window_title(paths: Paths) -> str:
    return f"ezgoggles - {paths.root.name}"


def is_wsl() -> bool:
    if sys.platform != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower()
    except OSError:
        return False


class Launcher:
    name = "launcher"

    def available(self) -> bool:
        raise NotImplementedError

    def command(self, paths: Paths) -> Command:
        raise NotImplementedError


# ---------- Windows ----------

class WindowsTerminal(Launcher):
    name = "windows-terminal"

    def available(self) -> bool:
        return os.name == "nt" and shutil.which("wt") is not None

    def command(self, paths: Paths) -> Command:
        return Command([shutil.which("wt") or "wt", "-w", "new", "new-tab", "--title",
                        window_title(paths), "-d", str(paths.root), *tui_argv(paths)])


class WindowsConsole(Launcher):
    name = "windows-console"

    def available(self) -> bool:
        return os.name == "nt"

    def command(self, paths: Paths) -> Command:
        return Command(tui_argv(paths), {
            "creationflags": getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            "cwd": str(paths.root),
        })


# ---------- macOS ----------

class MacTerminal(Launcher):
    name = "macos-terminal"

    def available(self) -> bool:
        return sys.platform == "darwin"

    def command(self, paths: Paths) -> Command:
        script = f"cd {shlex.quote(str(paths.root))} && exec {shlex.join(tui_argv(paths))}"
        script = script.replace("\\", "\\\\").replace('"', '\\"')
        return Command([
            "osascript",
            "-e", f'tell application "Terminal" to do script "{script}"',
            "-e", 'tell application "Terminal" to activate',
        ])


# ---------- WSL: the window opens on the Windows side ----------

def _wsl_inner(paths: Paths) -> list[str]:
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    return ["wsl.exe", *(["-d", distro] if distro else []), "--cd", str(paths.root), "--", *tui_argv(paths)]


def _win_cwd() -> dict:
    # cmd.exe complains when its working dir is a Linux path.
    return {"cwd": "/mnt/c"} if Path("/mnt/c").is_dir() else {}


class WslWindowsTerminal(Launcher):
    name = "wsl-windows-terminal"

    def available(self) -> bool:
        return is_wsl() and shutil.which("wt.exe") is not None

    def command(self, paths: Paths) -> Command:
        return Command([shutil.which("wt.exe") or "wt.exe", "-w", "new", "new-tab", "--title",
                        window_title(paths), *_wsl_inner(paths)], _win_cwd())


class WslCmd(Launcher):
    name = "wsl-cmd"

    def available(self) -> bool:
        return is_wsl() and shutil.which("cmd.exe") is not None

    def command(self, paths: Paths) -> Command:
        return Command(["cmd.exe", "/c", "start", window_title(paths), *_wsl_inner(paths)], _win_cwd())


# ---------- Ubuntu ----------

class GnomeTerminal(Launcher):
    name = "gnome-terminal"

    def available(self) -> bool:
        return (
            sys.platform == "linux"
            and not is_wsl()
            and bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
            and shutil.which("gnome-terminal") is not None
        )

    def command(self, paths: Paths) -> Command:
        return Command(["gnome-terminal", f"--title={window_title(paths)}",
                        f"--working-directory={paths.root}", "--", *tui_argv(paths)])


LAUNCHERS: list[Launcher] = [
    WindowsTerminal(),
    WindowsConsole(),
    MacTerminal(),
    WslWindowsTerminal(),
    WslCmd(),
    GnomeTerminal(),
]


def available_launchers() -> list[Launcher]:
    return [ln for ln in LAUNCHERS if ln.available()]
