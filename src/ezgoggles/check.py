"""Validate the files that agents write and the TUI reads.

Extension point: a rule is a function that adds errors or warnings to a
Report. To add a rule, write the function and append it to MAP_RULES or
ACTIVITY_RULES. Rules run only after the file passes its JSON schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator

from .model import find_cycle
from .paths import SCHEMA_DIR, Paths


@dataclass
class Report:
    file: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: object | None = None  # set only when there are no errors

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------- map rules ----------

MapRule = Callable[[dict, Paths, Report], None]


def unique_ids(m: dict, paths: Paths, r: Report) -> None:
    seen: set[str] = set()
    for s in m["stages"]:
        if s["id"] in seen:
            r.errors.append(f"stages: id '{s['id']}' is used more than once")
        seen.add(s["id"])


def known_next(m: dict, paths: Paths, r: Report) -> None:
    ids = {s["id"] for s in m["stages"]}
    for s in m["stages"]:
        for n in s["next"]:
            if n not in ids:
                r.errors.append(f"stages/{s['id']}/next: no stage has id '{n}'")
            elif n == s["id"]:
                r.errors.append(f"stages/{s['id']}/next: a stage cannot hand off to itself")


def no_loops(m: dict, paths: Paths, r: Report) -> None:
    cycle = find_cycle({s["id"]: s["next"] for s in m["stages"]})
    if cycle:
        r.warnings.append(
            "stages: the handoffs form a loop (" + " -> ".join(cycle) + "); "
            "the TUI shows these stages in file order"
        )


def stage_paths_exist(m: dict, paths: Paths, r: Report) -> None:
    for s in m["stages"]:
        if not (paths.root / s["path"]).exists():
            r.warnings.append(f"stages/{s['id']}/path: '{s['path']}' does not exist yet")


def sources_exist(m: dict, paths: Paths, r: Report) -> None:
    sources = m["requirements"]["sources"]
    if not sources:
        r.warnings.append("requirements/sources: empty; list the original course materials")
    for src in sources:
        if not (paths.root / src).exists():
            r.warnings.append(f"requirements/sources: '{src}' does not exist")


MAP_RULES: list[MapRule] = [unique_ids, known_next, no_loops, stage_paths_exist, sources_exist]


# ---------- activity rules ----------

ActivityRule = Callable[[dict, "set[str] | None", Report], None]


def known_stages(a: dict, ids: set[str] | None, r: Report) -> None:
    if ids is None:
        return
    for sid in a:
        if sid not in ids:
            r.warnings.append(f"{sid}: no stage in map.json has this id")


def finished_needs_handoff(a: dict, ids: set[str] | None, r: Report) -> None:
    for sid, plans in a.items():
        for i, plan in enumerate(plans):
            if all(it["done"] for it in plan["items"]) and "handoffChange" not in plan:
                r.warnings.append(f"{sid}/{i}: all items are done but handoffChange is missing")


ACTIVITY_RULES: list[ActivityRule] = [known_stages, finished_needs_handoff]


# ---------- engine ----------

_FAILED = object()


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _load(report: Report) -> object:
    """Return the parsed JSON, or _FAILED after an error is recorded."""
    try:
        text = report.file.read_text(encoding="utf-8-sig")  # PowerShell adds a BOM
    except FileNotFoundError:
        report.errors.append("file does not exist")
        return _FAILED
    except OSError as e:
        report.errors.append(f"cannot read file: {e}")
        return _FAILED
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        report.errors.append(f"not valid JSON: {e.msg} (line {e.lineno}, column {e.colno})")
        return _FAILED


def _schema_errors(name: str, data: object) -> list[str]:
    out = []
    for err in sorted(_validator(name).iter_errors(data), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(top level)"
        out.append(f"{where}: {err.message}")
    return out


def check_map(paths: Paths) -> Report:
    r = Report(paths.map)
    data = _load(r)
    if data is _FAILED:
        return r
    r.errors += _schema_errors("map", data)
    if r.errors:
        return r
    for rule in MAP_RULES:
        rule(data, paths, r)
    if r.ok:
        r.data = data
    return r


def check_activity(paths: Paths, stage_ids: set[str] | None) -> Report:
    """stage_ids is None when the map is not valid."""
    r = Report(paths.activity)
    if not paths.activity.exists():
        r.data = {}
        return r
    data = _load(r)
    if data is _FAILED:
        return r
    r.errors += _schema_errors("activity", data)
    if r.errors:
        return r
    for rule in ACTIVITY_RULES:
        rule(data, stage_ids, r)
    if r.ok:
        r.data = data
    return r
