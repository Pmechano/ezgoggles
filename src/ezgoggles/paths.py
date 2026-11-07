"""Locate the group project and the files that ezgoggles reads and writes."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = "goggles-data"
LOCAL_DIR = ".local"

PLUGIN_DIR = Path(__file__).resolve().parents[2]
SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def data(self) -> Path:
        return self.root / DATA_DIR

    @property
    def local(self) -> Path:
        return self.data / LOCAL_DIR

    @property
    def map(self) -> Path:
        return self.data / "map.json"

    @property
    def activity(self) -> Path:
        return self.local / "activity.json"

    @property
    def user(self) -> Path:
        return self.local / "user.json"

    @property
    def pid(self) -> Path:
        return self.local / "tui.pid"


def find_root(start: Path | None = None) -> Path:
    """Return the group project root.

    The root is the nearest parent that holds goggles-data/. If there is none,
    the root is the git top level. If that also fails, the root is the start dir.
    """
    start = (start or Path.cwd()).resolve()
    for d in (start, *start.parents):
        if (d / DATA_DIR).is_dir():
            return d
    top = git(start, "rev-parse", "--show-toplevel")
    if top:
        # Inside the ezgoggles submodule itself, go up to the superproject.
        sup = git(start, "rev-parse", "--show-superproject-working-tree")
        return Path(sup or top).resolve()
    return start


def git(cwd: Path, *args: str) -> str | None:
    """Run git and return stripped stdout, or None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def read_json(path: Path) -> object | None:
    """Return the parsed JSON, or None if the file is missing or broken."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
