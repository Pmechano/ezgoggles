"""The task layer: what the course asks for."""

from __future__ import annotations

import json
from datetime import date

from textual.containers import HorizontalGroup, VerticalGroup
from textual.widgets import Static

from ...context import Context
from ...model import due_date, topo_order, used_for
from .base import Status, View, esc, map_problem


def deliverables(ctx: Context) -> list[tuple[dict, bool]]:
    """(deliverable, mine) by deadline, then map order. `mine`: the user's work goes into it."""
    m = ctx.map
    mine = {id(d) for d, _ in used_for(m, ctx.mine)} if ctx.mine else set()
    items = list(enumerate(m["requirements"]["deliver"]))
    items.sort(key=lambda it: (due_date(it[1]) or date.max, it[0]))
    return [(d, id(d) in mine) for _, d in items]


def made_by(ctx: Context, d: dict) -> str:
    if not d["from"]:
        return "—"
    if set(d["from"]) == ctx.stage_ids and len(ctx.stage_ids) > 2:
        return ctx.t("task.all")
    names = [s["name"] for s in topo_order(ctx.stages) if s["id"] in d["from"]]
    return ctx.t("punct.sep").join(names)


def short_due(d: dict) -> str:
    day = due_date(d)
    if day is None:
        return "—"
    return f"{day.month}/{day.day}{d['due'][10:]}"


class TaskView(View):
    key = "task"

    DEFAULT_CSS = """
    TaskView .row { height: auto; padding: 0 1; border-left: thick transparent; }
    TaskView .row.mine { border-left: thick $accent; }
    TaskView .row.head { color: $text-muted; }
    TaskView .what { width: 1fr; }
    TaskView .due { width: 12; }
    TaskView .from { width: 1fr; color: $text-muted; }
    TaskView .row.mine .what { text-style: bold; }
    TaskView #task-rows { height: auto; margin-bottom: 1; }
    TaskView #task-more { padding: 0 1 0 2; }
    """

    def compose(self):
        yield Static("", id="task-msg")
        yield VerticalGroup(id="task-rows")
        yield Static("", id="task-more")

    def update_from(self, ctx: Context) -> None:
        msg = self.query_one("#task-msg", Static)
        rows = self.query_one("#task-rows", VerticalGroup)
        more = self.query_one("#task-more", Static)
        problem = map_problem(ctx)
        msg.display = bool(problem)
        msg.update(problem or "")
        rows.remove_children()
        if problem:
            more.update("")
            return
        head = HorizontalGroup(
            Static(ctx.t("task.what"), classes="what"),
            Static(ctx.t("task.due"), classes="due"),
            Static(ctx.t("task.from"), classes="from"),
            classes="row head",
        )
        lines = [head]
        for d, mine in deliverables(ctx):
            lines.append(HorizontalGroup(
                Static(esc(d["text"]), classes="what"),
                Static(short_due(d), classes="due"),
                Static(esc(made_by(ctx, d)), classes="from"),
                classes="row mine" if mine else "row",
            ))
        rows.mount_all(lines)
        more.update(self.more(ctx))

    @staticmethod
    def more(ctx: Context) -> str:
        req = ctx.map["requirements"]
        sep, colon = ctx.t("punct.sep"), ctx.t("punct.colon")
        out = [f"[$text-muted]{ctx.t('task.grading')}{colon}[/]{esc(sep.join(req['grading']))}"]
        for note in req.get("notes") or []:
            out.append(f"[$text-muted]{ctx.t('task.notes')}{colon}[/]{esc(note)}")
        if req["sources"]:
            out.append(f"\n[$text-muted]{ctx.t('map.sources')} {esc(sep.join(req['sources']))}[/]")
        return "\n".join(out)

    @staticmethod
    def token(ctx: Context) -> object:
        if ctx.map is None:
            return None
        return json.dumps(ctx.map["requirements"], ensure_ascii=False, sort_keys=True)

    @staticmethod
    def status(ctx: Context, seen: object, today: date | None = None) -> Status | None:
        if ctx.map is None:
            return None
        if seen is not None and seen != TaskView.token(ctx):
            return Status(ctx.t("tab.changed"), "act")
        today = today or date.today()
        mine = [d for d, m in deliverables(ctx) if m] or ctx.map["requirements"]["deliver"]
        days = sorted(n for d in mine if (day := due_date(d)) and (n := (day - today).days) >= 0)
        if not days:
            return None
        return Status(ctx.t("tab.today") if days[0] == 0 else ctx.t("tab.days", n=str(days[0])))
