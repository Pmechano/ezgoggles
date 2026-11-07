"""Facts about the group project that come from git and the directory layout."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .paths import DATA_DIR, Paths


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


def find_root(start: Path | None = None) -> Path:
    """Return the group project root.

    The root is the nearest parent that holds goggles-data/. If there is none,
    the root is the git top level (the superproject when we are inside the
    ezgoggles submodule). If that also fails, the root is the start dir.
    """
    start = (start or Path.cwd()).resolve()
    for d in (start, *start.parents):
        if (d / DATA_DIR).is_dir():
            return d
    top = git(start, "rev-parse", "--show-toplevel")
    if top:
        sup = git(start, "rev-parse", "--show-superproject-working-tree")
        return Path(sup or top).resolve()
    return start


def current_branch(paths: Paths) -> str | None:
    # symbolic-ref also works in a repo with no commits yet.
    return git(paths.root, "symbolic-ref", "--short", "HEAD") or git(
        paths.root, "rev-parse", "--abbrev-ref", "HEAD"
    )


def stage_from_branch(branch: str | None, name: str, stage_ids: set[str]) -> str | None:
    """Branches are named <name>/<stage-id>. Return the stage id, or None."""
    if not branch or "/" not in branch:
        return None
    owner, _, sid = branch.partition("/")
    if owner == name and sid in stage_ids:
        return sid
    return None


def changed_files(paths: Paths) -> int | None:
    out = git(paths.root, "status", "--porcelain")
    if out is None:
        return None
    return len([line for line in out.splitlines() if line.strip()])
