"""Validate the files that agents write and the TUI reads.

Extension point: a rule is a function that adds errors or warnings to a
Report. To add a rule, write the function and append it to MAP_RULES,
ACTIVITY_RULES or CODE_RULES. Rules run only after the file passes its JSON schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator

from .model import downstream, find_cycle, fingerprint, structure, width
from .paths import SCHEMA_DIR, Paths


@dataclass
class Report:
    file: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: object | None = None  # set only when there are no errors
    stale: bool = False  # translations: made from an older map.json

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


def known_from(m: dict, paths: Paths, r: Report) -> None:
    ids = {s["id"] for s in m["stages"]}
    for i, d in enumerate(m["requirements"]["deliver"]):
        for f in d["from"]:
            if f not in ids:
                r.errors.append(f"requirements/deliver/{i}/from: no stage has id '{f}'")


def layers_connect(m: dict, paths: Paths, r: Report) -> None:
    """Every stage should go into a deliverable, and every deliverable should come from a stage."""
    direct = {f for d in m["requirements"]["deliver"] for f in d["from"]}
    for s in m["stages"]:
        if s["id"] not in direct and not direct & set(downstream(m["stages"], s["id"])):
            r.warnings.append(f"stages/{s['id']}: its output goes into no deliverable; "
                              "add it to a deliverable's `from`, or check its `next`")
    for i, d in enumerate(m["requirements"]["deliver"]):
        if not d["from"]:
            r.warnings.append(f"requirements/deliver/{i}: no stage makes it; set `from` if a stage does")


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


# Members must read the map comfortably. These limits are hints, so they only warn.
# Widths are terminal columns: a CJK character counts as two.
READABLE = {"goal": 120, "name": 24, "does": 60, "input": 40, "output": 40, "item": 100, "deliver": 40}
MAX_ITEMS = 7


def readable(m: dict, paths: Paths, r: Report) -> None:
    def long(where: str, text: str, limit: int) -> None:
        if width(text) > limit:
            r.warnings.append(f"{where}: long for a reader ({width(text)} columns, aim for {limit}); shorten it")

    long("goal", m["goal"], READABLE["goal"])
    for key, items in m["requirements"].items():
        if key == "sources":
            continue
        if len(items) > MAX_ITEMS:
            r.warnings.append(f"requirements/{key}: {len(items)} items; aim for {MAX_ITEMS} or fewer")
        for i, item in enumerate(items):
            if key == "deliver":
                long(f"requirements/deliver/{i}/text", item["text"], READABLE["deliver"])
            else:
                long(f"requirements/{key}/{i}", item, READABLE["item"])
    for s in m["stages"]:
        for key in ("name", "does", "input", "output"):
            long(f"stages/{s['id']}/{key}", s[key], READABLE[key])


MAP_RULES: list[MapRule] = [
    unique_ids, known_next, no_loops, known_from, layers_connect, stage_paths_exist, sources_exist, readable,
]


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


# ---------- code rules ----------

CodeRule = Callable[[dict, Paths, "set[str] | None", Report], None]


def code_known_stages(c: dict, paths: Paths, ids: set[str] | None, r: Report) -> None:
    if ids is None:
        return
    for sid in c:
        if sid not in ids:
            r.warnings.append(f"{sid}: no stage in map.json has this id")


def code_files_exist(c: dict, paths: Paths, ids: set[str] | None, r: Report) -> None:
    for sid, entry in c.items():
        for i, step in enumerate(entry["steps"]):
            f = step["file"].split("::")[0]
            if not (paths.root / f).exists():
                r.warnings.append(f"{sid}/steps/{i}/file: '{f}' does not exist")


def code_readable(c: dict, paths: Paths, ids: set[str] | None, r: Report) -> None:
    for sid, entry in c.items():
        for i, step in enumerate(entry["steps"]):
            if width(step["does"]) > READABLE["does"]:
                r.warnings.append(f"{sid}/steps/{i}/does: long for a reader ({width(step['does'])} columns, "
                                  f"aim for {READABLE['does']}); shorten it")


CODE_RULES: list[CodeRule] = [code_known_stages, code_files_exist, code_readable]


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


def check_translation(paths: Paths, language: str, original: dict) -> Report:
    """A translation must keep the structure of the original and name its fingerprint."""
    r = Report(paths.translation(language))
    data = _load(r)
    if data is _FAILED:
        return r
    r.errors += _schema_errors("map", data)
    if r.errors:
        return r
    if data["language"] != language:
        r.errors.append(f"language: is '{data['language']}', but the file name says '{language}'")
    if "source" not in data:
        r.errors.append("source: missing; set it to the fingerprint that `ezgoggles check` prints")
    if structure(data) != structure(original):
        r.errors.append("stage ids, paths and next, and each deliverable's due and from, "
                        "must be the same as in map.json, in the same order")
    readable(data, paths, r)
    if r.ok:
        r.data = data
        if data["source"] != fingerprint(original):
            r.stale = True
            r.warnings.append("made from an older map.json; translate it again")
    return r


def check_translations(paths: Paths, original: dict) -> list[Report]:
    if not paths.translations.is_dir():
        return []
    out = []
    for f in sorted(paths.translations.glob("map.*.json")):
        out.append(check_translation(paths, f.name[len("map."):-len(".json")], original))
    return out


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


def check_code(paths: Paths, stage_ids: set[str] | None) -> Report:
    """The personal code flow. A missing file is fine: it is written only in learning mode."""
    r = Report(paths.code)
    if not paths.code.exists():
        r.data = {}
        return r
    data = _load(r)
    if data is _FAILED:
        return r
    r.errors += _schema_errors("code", data)
    if r.errors:
        return r
    for rule in CODE_RULES:
        rule(data, paths, stage_ids, r)
    if r.ok:
        r.data = data
    return r
