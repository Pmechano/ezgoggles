"""Validate the files that agents write and the TUI reads."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .paths import SCHEMA_DIR, Paths

NO_CHANGE = {"", "none", "无", "无变化", "no change"}


@dataclass
class Report:
    file: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: object | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


_FAILED = object()


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
    report = Report(paths.map)
    data = _load(report)
    if data is _FAILED:
        return report
    report.errors += _schema_errors("map", data)
    if report.errors:
        return report

    stages = data["stages"]
    ids = [s["id"] for s in stages]
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            report.errors.append(f"stages: id '{i}' is used more than once")
        seen.add(i)
    for s in stages:
        for n in s["next"]:
            if n not in seen:
                report.errors.append(f"stages/{s['id']}/next: no stage has id '{n}'")
            elif n == s["id"]:
                report.errors.append(f"stages/{s['id']}/next: a stage cannot hand off to itself")
        if not (paths.root / s["path"]).exists():
            report.warnings.append(f"stages/{s['id']}/path: '{s['path']}' does not exist yet")
    cycle = _find_cycle({s["id"]: s["next"] for s in stages})
    if cycle:
        report.warnings.append(
            "stages: the handoffs form a loop (" + " -> ".join(cycle) + "); "
            "the TUI shows these stages in file order"
        )
    for src in data["requirements"]["sources"]:
        if not (paths.root / src).exists():
            report.warnings.append(f"requirements/sources: '{src}' does not exist")
    if not data["requirements"]["sources"]:
        report.warnings.append("requirements/sources: empty; list the original course materials")

    if not report.errors:
        report.data = data
    return report


def _find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {}  # 1 = on the current path, 2 = done
    path: list[str] = []

    def visit(n: str) -> list[str] | None:
        state[n] = 1
        path.append(n)
        for m in graph.get(n, []):
            if m not in graph or m == n:
                continue
            if state.get(m) == 1:
                return path[path.index(m):] + [m]
            if m not in state and (found := visit(m)):
                return found
        path.pop()
        state[n] = 2
        return None

    for n in graph:
        if n not in state and (found := visit(n)):
            return found
    return None


def check_activity(paths: Paths, stage_ids: set[str] | None) -> Report:
    report = Report(paths.activity)
    if not paths.activity.exists():
        report.data = {}
        return report
    data = _load(report)
    if data is _FAILED:
        return report
    report.errors += _schema_errors("activity", data)
    if report.errors:
        return report
    for sid, plans in data.items():
        if stage_ids is not None and sid not in stage_ids:
            report.warnings.append(f"{sid}: no stage in map.json has this id")
        for i, plan in enumerate(plans):
            finished = all(it["done"] for it in plan["items"])
            if finished and "handoffChange" not in plan:
                report.warnings.append(
                    f"{sid}/{i}: all items are done but handoffChange is missing"
                )
    report.data = data
    return report


def handoff_changed(plan: dict) -> bool:
    value = plan.get("handoffChange")
    return isinstance(value, str) and value.strip().lower() not in NO_CHANGE


def run_check(paths: Paths) -> int:
    """Print a report for the agent. Return the process exit code."""
    m = check_map(paths)
    ids = {s["id"] for s in m.data["stages"]} if m.data else None
    a = check_activity(paths, ids)
    bad = False
    for r in (m, a):
        rel = r.file.relative_to(paths.root).as_posix()
        if r.ok:
            print(f"OK    {rel}")
        else:
            bad = True
            print(f"ERROR {rel}")
            for e in r.errors:
                print(f"  - {e}")
        for w in r.warnings:
            print(f"  warning: {w}")
    if bad:
        print(f"Schemas: {SCHEMA_DIR.as_posix()}")
    return 1 if bad else 0
