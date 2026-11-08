"""The solution layer: the stages, and what each stage gives to the next.

The whole flow fits on one screen: one line per stage, and the handoff on
the arrow between two stages. Only the selected stage opens into a card.
"""

from __future__ import annotations

import json

from textual.containers import VerticalGroup
from textual.events import Click
from textual.message import Message
from textual.widgets import Static

from ...context import Context
from ...model import handoff_changed, topo_order, upstream, used_for
from ..widgets import Arrow, motion_on
from .base import Status, View, esc, map_problem

MARKS = {"merged": ("✓", "$success"), "working": ("◐", "$accent"), "none": ("·", "$text-muted")}


def mark(ctx: Context, sid: str) -> str:
    p = ctx.progress.get(sid)
    if p is None:
        return " "
    glyph, colour = MARKS[p.state]
    return f"[{colour}]{glyph}[/]"


def latest_handoff(ctx: Context) -> str | None:
    """The handoff change in the latest plan of the user's stage, if it is a real change."""
    plans = (ctx.activity or {}).get(ctx.mine or "", [])
    if plans and handoff_changed(plans[-1]):
        return plans[-1]["handoffChange"]
    return None


def goes_into(ctx: Context, sid: str) -> str:
    sep = ctx.t("punct.sep")
    parts = []
    for d, via in used_for(ctx.map, sid):
        text = esc(d["text"])
        if via is not None:
            text += f"[$text-muted]{esc(ctx.t('flow.via', name=ctx.stage_by_id[via]['name']))}[/]"
        parts.append(text)
    return sep.join(parts)


def row_markup(ctx: Context, s: dict, selected: bool) -> str:
    you = f"  [b $accent]{esc(ctx.t('flow.you'))}[/]" if s["id"] == ctx.mine else ""
    name = esc(s["name"])
    if not selected:
        return f"{mark(ctx, s['id'])}  [b]{name}[/]{you}   [$text-muted]{esc(s['does'])}[/]"
    p = ctx.progress.get(s["id"])
    state = f"   [$text-muted]{ctx.t('flow.' + ('empty' if p.state == 'none' else p.state))}[/]" if p else ""
    lines = [
        f"{mark(ctx, s['id'])}  [b $accent]{name}[/]{you}{state}",
        f"   {esc(s['does'])}",
    ]
    if into := goes_into(ctx, s["id"]):
        lines.append(f"   [$text-muted]{ctx.t('flow.used_for')}[/]  {into}")
    if s["id"] == ctx.mine and (change := latest_handoff(ctx)):
        lines.append(f"   [b $warning]{ctx.t('tab.handoff')}[/]  {esc(change)}")
    if ctx.user.mode == "learn":
        lines.append(f"   [$text-muted]{esc(ctx.t('flow.path', path=s['path']))}[/]")
    return "\n".join(lines)


class StageRow(Static):
    class Picked(Message):
        def __init__(self, sid: str) -> None:
            super().__init__()
            self.sid = sid

    def __init__(self, sid: str) -> None:
        super().__init__("", classes="stage")
        self.sid = sid

    def on_click(self, event: Click) -> None:
        self.post_message(self.Picked(self.sid))


class FlowView(View):
    key = "flow"

    DEFAULT_CSS = """
    FlowView #flow-msg { color: $text-muted; margin-bottom: 1; }
    FlowView #flow { height: auto; }
    FlowView .stage { padding: 0 1; border-left: thick transparent; }
    FlowView .stage:hover { background: $boost; }
    FlowView .stage.selected { border-left: thick $accent; background: $accent 8%; }
    FlowView Arrow { padding: 0 0 0 2; }
    FlowView #flow-legend { color: $text-muted; margin-top: 1; padding: 0 1; }
    """

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.ctx: Context | None = None
        self.order: list[str] = []
        self.selected: str | None = None

    def compose(self):
        yield Static("", id="flow-msg")
        yield VerticalGroup(id="flow")
        yield Static("", id="flow-legend")

    # ----- building -----

    def update_from(self, ctx: Context) -> None:
        old = self.ctx
        self.ctx = ctx
        msg = self.query_one("#flow-msg", Static)
        legend = self.query_one("#flow-legend", Static)
        problem = map_problem(ctx)
        if problem or ctx.mine is None:
            msg.update(problem or ctx.t("flow.none"))
        msg.display = bool(problem) or ctx.mine is None
        if problem:
            self.query_one("#flow").remove_children()
            self.order = []
            legend.update("")
            return
        order = [s["id"] for s in topo_order(ctx.stages)]
        if order != self.order:
            self.order = order
            self._build(ctx)
        if self.selected not in order or (old is not None and old.mine != ctx.mine):
            self.selected = ctx.mine or order[0]
        self._draw(ctx)
        legend.update(self._legend(ctx))
        if old is not None and old.map is not None:
            self._arrivals(old, ctx)

    def _build(self, ctx: Context) -> None:
        flow = self.query_one("#flow", VerticalGroup)
        flow.remove_children()
        widgets = []
        for sid in self.order:
            widgets.append(StageRow(sid))
            widgets.append(Arrow(classes=f"out-{sid}"))
        flow.mount_all(widgets)

    def _draw(self, ctx: Context) -> None:
        by_id = ctx.stage_by_id
        for i, sid in enumerate(self.order):
            s = by_id[sid]
            for row in self.query(StageRow):
                if row.sid == sid:
                    row.update(row_markup(ctx, s, sid == self.selected))
                    row.set_class(sid == self.selected, "selected")
            nxt = self.order[i + 1] if i + 1 < len(self.order) else None
            arrow = self._arrow(sid)
            if arrow is None:
                continue
            if not s["next"]:
                arrow.set(s["output"], final=True)
            elif s["next"] == [nxt]:
                arrow.set(s["output"])
            else:
                names = ctx.t("punct.list").join(by_id[n]["name"] for n in s["next"] if n in by_id)
                arrow.set(s["output"], end=ctx.t("flow.goes_to", names=names))

    def _arrow(self, sid: str) -> Arrow | None:
        found = self.query(f".out-{sid}")
        return found.first(Arrow) if found else None

    def _legend(self, ctx: Context) -> str:
        if not ctx.progress:
            return ""
        return "   ".join(
            f"[{c}]{g}[/] {ctx.t('flow.' + ('empty' if k == 'none' else k))}" for k, (g, c) in MARKS.items()
        )

    def _arrivals(self, old: Context, new: Context) -> None:
        """Upstream work landed on the base branch: light the arrow into the user's stage."""
        if new.mine is None:
            return
        for u in upstream(new.stages, new.mine):
            before, after = old.progress.get(u["id"]), new.progress.get(u["id"])
            if before and after and before.on_base != after.on_base and after.on_base:
                if arrow := self._arrow(u["id"]):
                    arrow.fill()

    # ----- interaction -----

    def on_stage_row_picked(self, event: StageRow.Picked) -> None:
        self._select(event.sid)

    def move(self, delta: int) -> bool:
        if not self.order or self.selected is None:
            return False
        i = max(0, min(len(self.order) - 1, self.order.index(self.selected) + delta))
        self._select(self.order[i])
        return True

    def _select(self, sid: str) -> None:
        if self.ctx is None or sid == self.selected:
            return
        self.selected = sid
        self._draw(self.ctx)
        for row in self.query(StageRow):
            if row.sid == sid:
                row.scroll_visible(animate=False)
        if arrow := self._arrow(sid):
            arrow.flow()

    def entered(self, ctx: Context, first: bool) -> None:
        """During the tour, the flow draws itself from top to bottom: the whole before the parts."""
        if not first or not motion_on(self):
            return
        flow = self.query_one("#flow")
        for i, child in enumerate(flow.children):
            child.styles.opacity = 0.0
            child.styles.animate("opacity", 1.0, duration=0.25, delay=0.07 * i)

    # ----- tab -----

    @staticmethod
    def token(ctx: Context) -> object:
        if ctx.map is None:
            return None
        ups = {u["id"]: (p.on_base if (p := ctx.progress.get(u["id"])) else None)
               for u in (upstream(ctx.stages, ctx.mine) if ctx.mine else [])}
        return json.dumps({"handoff": latest_handoff(ctx), "up": ups}, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def status(ctx: Context, seen: object) -> Status | None:
        if ctx.map is None or seen is None:
            return None
        now, before = json.loads(FlowView.token(ctx)), json.loads(seen)
        if now["handoff"] and now["handoff"] != before.get("handoff"):
            return Status(ctx.t("tab.handoff"), "act")
        old_up = before.get("up", {})
        if any(v and k in old_up and old_up[k] != v for k, v in now["up"].items()):
            return Status(ctx.t("tab.upstream"), "new")
        return None
