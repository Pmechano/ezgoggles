"""Turn map.json and activity.json into Markdown and tree labels.

Pure functions, so tests do not need a running app.
"""

from __future__ import annotations

from rich.text import Text

from ..check import handoff_changed
from .i18n import tr


def topo_order(stages: list[dict]) -> list[dict]:
    """Stages in data-flow order. Ties keep the order of map.json."""
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
    order += [s for s in stages if s["id"] not in placed]  # cycles: keep file order
    return order


def upstream(stages: list[dict], sid: str) -> list[dict]:
    return [s for s in stages if sid in s["next"]]


def _label(s: dict) -> str:
    return f"{s['id']} · {s['name']}"


def requirements_md(lang: str, m: dict) -> str:
    req = m["requirements"]
    out = req["content"].rstrip()
    if req["sources"]:
        files = ", ".join(f"`{p}`" for p in req["sources"])
        out += f"\n\n---\n\n*{tr(lang, 'sources')}: {files}*"
    return out


def map_md(lang: str, m: dict, mine: str | None) -> str:
    stages = m["stages"]
    by_id = {s["id"]: s for s in stages}
    order = topo_order(stages)
    lines = [f"**{m['title']}**", "", m["goal"].strip(), ""]

    if all(len(s["next"]) <= 1 for s in stages) and len(order) > 1:
        chain = " → ".join(f"`{s['id']}`" for s in order)
        lines += [f"{tr(lang, 'map.flow')}: {chain}", ""]

    for s in order:
        you = f"  {tr(lang, 'stage.you')}" if s["id"] == mine else ""
        nxt = ", ".join(_label(by_id[n]) for n in s["next"] if n in by_id) or tr(lang, "stage.end")
        lines += [
            f"#### {_label(s)}{you}",
            "",
            f"- {tr(lang, 'stage.path')}: `{s['path']}`",
            f"- {tr(lang, 'stage.input')}: {s['input']}",
            f"- {tr(lang, 'stage.output')}: {s['output']}",
            f"- {tr(lang, 'stage.next')}: {nxt}",
            "",
        ]
    return "\n".join(lines).rstrip()


def stage_md(lang: str, m: dict, mine: str | None, branch: str | None, name: str, mode: str) -> str:
    stages = m["stages"]
    by_id = {s["id"]: s for s in stages}
    if mine is None or mine not in by_id:
        ids = ", ".join(f"`{s['id']}`" for s in topo_order(stages))
        return tr(lang, "stage.none", branch=branch or "?", name=name or "<name>", ids=ids)

    s = by_id[mine]
    ups = upstream(stages, mine)
    frm = ", ".join(_label(u) for u in ups) or tr(lang, "stage.start")
    nxt = ", ".join(_label(by_id[n]) for n in s["next"] if n in by_id) or tr(lang, "stage.end")
    lines = [
        f"### {_label(s)}",
        "",
        f"- {tr(lang, 'stage.path')}: `{s['path']}`",
        f"- {tr(lang, 'stage.from')}: {frm}",
        f"- {tr(lang, 'stage.input')}: {s['input']}",
        f"- {tr(lang, 'stage.output')}: {s['output']}",
        f"- {tr(lang, 'stage.next')}: {nxt}",
    ]
    if mode == "learn" and s.get("detail", "").strip():
        lines += ["", f"#### {tr(lang, 'stage.detail')}", "", s["detail"].strip()]
    return "\n".join(lines)


# ---------- activity tree ----------

def stage_order_for_activity(activity: dict, stages: list[dict], mine: str | None) -> list[str]:
    known = [s["id"] for s in topo_order(stages)]
    keys = [k for k in known if k in activity]
    keys += [k for k in activity if k not in keys]
    if mine in keys:
        keys.remove(mine)
        keys.insert(0, mine)
    return keys


def stage_label(sid: str, stages: list[dict], mine: str | None, lang: str) -> Text:
    name = next((s["name"] for s in stages if s["id"] == sid), None)
    t = Text(f"{sid} · {name}" if name else sid, style="bold")
    if sid == mine:
        t.append(f"  {tr(lang, 'stage.you')}", style="italic")
    return t


def plan_label(plan: dict) -> Text:
    items = plan["items"]
    done = sum(1 for it in items if it["done"])
    time = plan["time"][5:16].replace("T", " ")
    t = Text(f"{time}  ", style="dim")
    t.append(plan["title"])
    t.append(f"  [{done}/{len(items)}]", style="green" if done == len(items) else "yellow")
    return t


def item_label(item: dict, lang: str) -> Text:
    t = Text("✓ " if item["done"] else "○ ", style="green" if item["done"] else "")
    t.append(item["text"], style="dim" if item["done"] else "")
    if item.get("byUser"):
        t.append(f"  ({tr(lang, 'activity.byuser')})", style="bold magenta")
    return t


def summary_label(plan: dict, lang: str) -> Text | None:
    if "summary" not in plan:
        return None
    t = Text(f"{tr(lang, 'activity.summary')}: ", style="bold")
    t.append(plan["summary"])
    return t


def handoff_label(plan: dict, lang: str) -> Text | None:
    if "handoffChange" not in plan:
        return None
    changed = handoff_changed(plan)
    t = Text(f"{tr(lang, 'activity.handoff')}: ", style="bold reverse yellow" if changed else "bold")
    t.append(plan["handoffChange"], style="bold yellow" if changed else "dim")
    return t
