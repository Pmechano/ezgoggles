"""Facts about the group project that come from git."""

from __future__ import annotations

from .paths import Paths, git


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
