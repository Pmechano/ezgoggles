"""Domain rules for the map and the activity log. No I/O, no UI."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import date

NO_CHANGE = {"", "none", "无", "无变化", "no change"}


def fingerprint(m: dict) -> str:
    """A short hash of a map's content. Translations record it in `source`."""
    data = {k: v for k, v in m.items() if k != "source"}
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def structure(m: dict) -> list[tuple]:
    """The parts of a map that a translation must not change."""
    stages = [(s["id"], s["path"], tuple(s["next"])) for s in m["stages"]]
    deliver = [(d.get("due"), tuple(d["from"])) for d in m["requirements"]["deliver"]]
    return stages + deliver


def width(text: str) -> int:
    """Terminal columns: CJK characters take two."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def stage_label(stage: dict) -> str:
    return f"{stage['id']} · {stage['name']}"


def topo_order(stages: list[dict]) -> list[dict]:
    """Stages in data-flow order. Ties keep the map order. Stages in a loop keep the map order."""
    by_id = {s["id"]: s for s in stages}
    indeg = {s["id"]: 0 for s in stages}
    for s in stages:
        for n in s["next"]:
            if n in indeg:
                indeg[n] += 1
    order: list[dict] = []
    ready = [s["id"] for s in stages if indeg[s["id"]] == 0]
    while ready:
        sid = ready.pop(0)
        order.append(by_id[sid])
        for n in by_id[sid]["next"]:
            if n in indeg:
                indeg[n] -= 1
                if indeg[n] == 0:
                    ready.append(n)
    placed = {s["id"] for s in order}
    return order + [s for s in stages if s["id"] not in placed]


def upstream(stages: list[dict], sid: str) -> list[dict]:
    return [s for s in stages if sid in s["next"]]


def downstream(stages: list[dict], sid: str) -> dict[str, str]:
    """Every stage that the output of `sid` reaches, mapped to the next stage on the way there."""
    nexts = {s["id"]: s["next"] for s in stages}
    via: dict[str, str] = {}
    todo = [(n, n) for n in nexts.get(sid, [])]
    while todo:
        n, first = todo.pop(0)
        if n in via or n == sid or n not in nexts:
            continue
        via[n] = first
        todo += [(m, first) for m in nexts[n]]
    return via


# ---------- task layer <-> solution layer ----------


def used_for(m: dict, sid: str) -> list[tuple[dict, str | None]]:
    """The deliverables that the work of `sid` goes into.

    Each item is (deliverable, via): via is None when the stage feeds the
    deliverable directly, or the next stage on the way to it.
    """
    reach = downstream(m["stages"], sid)
    out = []
    for d in m["requirements"]["deliver"]:
        if sid in d["from"]:
            out.append((d, None))
        else:
            hits = [reach[f] for f in d["from"] if f in reach]
            if hits:
                out.append((d, hits[0]))
    return out


def due_date(d: dict) -> date | None:
    due = d.get("due")
    try:
        return date.fromisoformat(due[:10]) if due else None
    except ValueError:
        return None


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Return one loop as [a, b, ..., a], or None."""
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


def handoff_changed(plan: dict) -> bool:
    value = plan.get("handoffChange")
    return isinstance(value, str) and value.strip().lower() not in NO_CHANGE
