"""One snapshot of everything a view needs, loaded in one place.

Panels and commands read a Context. They never load files or call git.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import i18n
from .check import Report, check_activity, check_code, check_map, check_translation
from .paths import Paths
from .progress import Progress, stage_progress
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
    translation_report: Report | None = None
    code_report: Report | None = None
    progress: dict[str, Progress] = field(default_factory=dict)  # from git; empty when unknown
    map: dict | None = field(init=False)  # what the user reads: a translation, or the original
    translation: str = field(init=False)  # native | ok | missing | stale | invalid | none
    stages: list[dict] = field(init=False)
    stage_ids: set[str] = field(init=False)
    mine: str | None = field(init=False)  # the user's stage, from the branch name

    def __post_init__(self) -> None:
        original = self.original_map
        tr = self.translation_report
        if original is None:
            self.map, self.translation = None, "none"
        elif original["language"] == self.user.language:
            self.map, self.translation = original, "native"
        elif tr is None or not tr.file.exists():
            self.map, self.translation = original, "missing"
        elif not tr.ok:
            self.map, self.translation = original, "invalid"
        elif tr.stale:
            self.map, self.translation = original, "stale"
        else:
            self.map, self.translation = tr.data, "ok"
        self.stages = self.map["stages"] if self.map else []
        self.stage_ids = {s["id"] for s in self.stages}
        self.mine = stage_from_branch(self.branch, self.user.name, self.stage_ids)

    @property
    def original_map(self) -> dict | None:
        d = self.map_report.data
        return d if isinstance(d, dict) else None

    @property
    def activity(self) -> dict | None:
        d = self.activity_report.data
        return d if isinstance(d, dict) else None

    @property
    def code(self) -> dict:
        """The personal code flow, by stage id. Empty when missing or invalid."""
        d = self.code_report.data if self.code_report else None
        return d if isinstance(d, dict) else {}

    @property
    def stage_by_id(self) -> dict[str, dict]:
        return {s["id"]: s for s in self.stages}

    def t(self, key: str, **kw: str) -> str:
        return i18n.tr(self.user.language, key, **kw)


def load_context(
    paths: Paths,
    user: User,
    branch: str | None = None,
    changed: int | None = None,
    progress: dict[str, Progress] | None = None,
) -> Context:
    mr = check_map(paths)
    original = mr.data if isinstance(mr.data, dict) else None
    ids = {s["id"] for s in original["stages"]} if original else None
    ar = check_activity(paths, ids)
    tr = None
    if original and original["language"] != user.language:
        tr = check_translation(paths, user.language, original)
    cr = check_code(paths, ids)
    return Context(paths, user, mr, ar, branch, changed, tr, cr, progress or {})


PROGRESS_FIRST = 1e9  # makes the first poll read the progress


class Watcher:
    """Builds a new Context only when the files or the git state change."""

    GIT_EVERY = 2.0  # seconds; git is slower than stat
    PROGRESS_EVERY = 10.0  # seconds; one git call per stage and per stage branch

    def __init__(self, paths: Paths) -> None:
        self.paths = paths
        self._sig: tuple | None = None
        self._git_at = 0.0
        self._branch: str | None = None
        self._changed: int | None = None
        self._progress_at = -PROGRESS_FIRST
        self._progress: dict[str, Progress] = {}

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
        if force or now - self._progress_at >= self.PROGRESS_EVERY:
            self._progress_at = now
            m = check_map(self.paths).data
            self._progress = stage_progress(self.paths, m["stages"]) if isinstance(m, dict) else {}
        sig = (
            self._mtime(self.paths.map),
            self._mtime(self.paths.activity),
            self._mtime(self.paths.translation(user.language)),
            self._mtime(self.paths.code),
            self._branch,
            self._changed,
            tuple(sorted(self._progress.items())),
        )
        if not force and sig == self._sig:
            return None
        self._sig = sig
        return load_context(self.paths, user, self._branch, self._changed, self._progress)
