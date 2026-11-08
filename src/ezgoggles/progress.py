"""How far each stage is, read only from git. Nobody writes anything for it.

It does not say who did how much. It says whether a stage's output is on
the base branch, where the next stage can take it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .paths import Paths
from .project import git

BASES = ("origin/main", "main", "origin/master", "master")


@dataclass(frozen=True)
class Progress:
    on_base: str | None = None  # last commit on the base branch that touches the stage path
    working: bool = False  # a stage branch has commits that are not on the base branch

    @property
    def state(self) -> str:
        """working | merged | none"""
        if self.working:
            return "working"
        return "merged" if self.on_base else "none"


def base_ref(paths: Paths) -> str | None:
    for ref in BASES:
        if git(paths.root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    return None


def stage_branches(paths: Paths, ids: set[str]) -> dict[str, list[str]]:
    """Local and remote branches named <name>/<stage-id>, by stage id."""
    out: dict[str, list[str]] = {}
    refs = git(paths.root, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes") or ""
    for ref in refs.splitlines():
        if ref.startswith("refs/heads/"):
            branch = ref[len("refs/heads/"):]
        elif ref.startswith("refs/remotes/"):
            branch = ref[len("refs/remotes/"):].partition("/")[2]
        else:
            continue
        owner, _, sid = branch.partition("/")
        if owner and sid in ids:
            out.setdefault(sid, []).append(ref)
    return out


def stage_progress(paths: Paths, stages: list[dict]) -> dict[str, Progress]:
    base = base_ref(paths)
    if base is None:
        return {}
    branches = stage_branches(paths, {s["id"] for s in stages})
    out = {}
    for s in stages:
        working = any(
            (git(paths.root, "rev-list", "--count", f"{base}..{ref}") or "0") != "0"
            for ref in branches.get(s["id"], [])
        )
        on_base = git(paths.root, "log", "-1", "--format=%H", base, "--", s["path"]) or None
        out[s["id"]] = Progress(on_base, working)
    return out
