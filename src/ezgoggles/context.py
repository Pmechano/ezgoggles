"""One snapshot of everything a view needs, loaded in one place.

Panels and commands read a Context. They never load files or call git.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import i18n
from .check import Report, check_activity, check_map
from .paths import Paths
from .project import changed_files, current_branch, stage_from_branch
from .user import User


@dataclass
class Context:
    paths: Paths
    user: User
    map_report: Report
    activity_report: Report
    branch: str | None = None
    changed: int | None = None
    stages: list[dict] = field(init=False)
    stage_ids: set[str] = field(init=False)
    mine: str | None = field(init=False)  # the user's stage, from the branch name

    def __post_init__(self) -> None:
        m = self.map
        self.stages = m["stages"] if m else []
        self.stage_ids = {s["id"] for s in self.stages}
        self.mine = stage_from_branch(self.branch, self.user.name, self.stage_ids)

    @property
    def map(self) -> dict | None:
        d = self.map_report.data
        return d if isinstance(d, dict) else None

    @property
    def activity(self) -> dict | None:
        d = self.activity_report.data
        return d if isinstance(d, dict) else None

    @property
    def stage_by_id(self) -> dict[str, dict]:
        return {s["id"]: s for s in self.stages}

    def t(self, key: str, **kw: str) -> str:
        return i18n.tr(self.user.language, key, **kw)


def load_context(paths: Paths, user: User, branch: str | None = None, changed: int | None = None) -> Context:
    mr = check_map(paths)
    ids = {s["id"] for s in mr.data["stages"]} if isinstance(mr.data, dict) else None
    ar = check_activity(paths, ids)
    return Context(paths, user, mr, ar, branch, changed)


class Watcher:
    """Builds a new Context only when the files or the git state change."""

    GIT_EVERY = 2.0  # seconds; git is slower than stat

    def __init__(self, paths: Paths) -> None:
        self.paths = paths
        self._sig: tuple | None = None
        self._git_at = 0.0
        self._branch: str | None = None
        self._changed: int | None = None

    def _mtime(self, f) -> int | None:
        try:
            return f.stat().st_mtime_ns
        except OSError:
            return None

    def poll(self, user: User, force: bool = False) -> Context | None:
        now = time.monotonic()
        if force or now - self._git_at >= self.GIT_EVERY:
            self._git_at = now
            self._branch = current_branch(self.paths)
            self._changed = changed_files(self.paths)
        sig = (self._mtime(self.paths.map), self._mtime(self.paths.activity), self._branch, self._changed)
        if not force and sig == self._sig:
            return None
        self._sig = sig
        return load_context(self.paths, user, self._branch, self._changed)
