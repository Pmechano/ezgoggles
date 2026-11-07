"""Domain rules for the map and the activity log. No I/O, no UI."""

from __future__ import annotations

NO_CHANGE = {"", "none", "无", "无变化", "no change"}


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
