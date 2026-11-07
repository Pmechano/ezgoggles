"""`ezgoggles open`: start the TUI in a new terminal window, once per project.

The only rule: if the TUI is not running, start it. We never block exit,
never restart it in the background, and never keep anything resident.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..paths import PLUGIN_DIR, Paths
from . import pidfile
from .launchers import Command, available_launchers


def _q(arg: str) -> str:
    return f'"{arg}"' if any(c.isspace() for c in arg) else arg


def manual_command(paths: Paths, plugin: Path = PLUGIN_DIR) -> str:
    """One command that starts the TUI by hand from any directory.

    No `cd ... &&`: Windows PowerShell 5.1 cannot parse `&&`.
    """
    return f"uv run --project {_q(str(plugin))} ezgoggles --root {_q(str(paths.root))} tui"


def spawn(cmd: Command) -> bool:
    kwargs = dict(cmd.popen)
    if os.name != "nt":
        kwargs.setdefault("start_new_session", True)
    try:
        subprocess.Popen(
            cmd.argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except OSError:
        return False
    return True


def open_tui(paths: Paths) -> str:
    """Start the TUI if it is not running.

    Return 'running', 'started', 'disabled' (EZGOGGLES_NO_WINDOW is set) or 'manual'.
    """
    if pidfile.tui_running(paths):
        return "running"
    if os.environ.get("EZGOGGLES_NO_WINDOW"):  # tests and CI
        return "disabled"
    pidfile.mark_launching(paths)
    for launcher in available_launchers():
        if spawn(launcher.command(paths)):
            return "started"
    pidfile.release(paths)
    return "manual"
