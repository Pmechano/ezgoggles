"""What the user's agent is doing: its plans, by stage.

Every line wraps. A wrapped line stays under its own text, so long items
read as one block. Click a plan's header to fold or open it.
"""

from __future__ import annotations

from textual.containers import HorizontalGroup, VerticalGroup
from textual.events import Click
from textual.message import Message
from textual.widgets import Static

from ...context import Context
from ...model import handoff_changed, topo_order
from ..widgets import motion_on
from .base import Status, View, esc

FLASH = 0.8  # seconds that a just-done item stays bright
DONE, TODO = esc("[x]"), esc("[ ]")


def stage_order(ctx: Context, activity: dict) -> list[str]:
    """Stages that have plans: the user's stage first, then data-flow order."""
    keys = [s["id"] for s in topo_order(ctx.stages) if s["id"] in activity]
    keys += [k for k in activity if k not in keys]
    if ctx.mine in keys:
        keys.remove(ctx.mine)
        keys.insert(0, ctx.mine)
    return keys


def latest_plan(ctx: Context) -> dict | None:
    """The newest plan of the user's stage, or the newest plan of all if no stage is picked."""
    activity = ctx.activity or {}
    if ctx.mine:
        plans = activity.get(ctx.mine) or []
        return plans[-1] if plans else None
    plans = [p for ps in activity.values() for p in ps]
    return max(plans, key=lambda p: p["time"]) if plans else None


def done_keys(ctx: Context) -> set[tuple]:
    return {(sid, p["time"], i)
            for sid, plans in (ctx.activity or {}).items()
            for p in plans for i, it in enumerate(p["items"]) if it["done"]}


def line(mark: str, text: str, classes: str = "") -> HorizontalGroup:
    """A mark in its own column, so the text wraps under itself."""
    return HorizontalGroup(Static(mark, classes="mark"), Static(text, classes="text"), classes=f"line {classes}")


def item_line(ctx: Context, item: dict, flash: bool) -> HorizontalGroup:
    you = f"  [b $secondary]({ctx.t('activity.byuser')})[/]" if item.get("byUser") else ""
    if item["done"] and flash:
        return line(f"[b $background on $accent]{DONE}[/]", f"[b $accent]{esc(item['text'])}[/]{you}")
    if item["done"]:
        return line(DONE, f"[$text-muted]{esc(item['text'])}[/]{you}")
    return line(f"[$text-muted]{TODO}[/]", f"{esc(item['text'])}{you}")


def extra_lines(ctx: Context, plan: dict) -> list[HorizontalGroup]:
    colon = ctx.t("punct.colon")
    out = []
    if "summary" in plan:
        out.append(line("", f"[b]{ctx.t('activity.summary')}{colon}[/]{esc(plan['summary'])}"))
    if "handoffChange" in plan:
        head = f"{ctx.t('activity.handoff')}{colon}"
        if handoff_changed(plan):
            out.append(line("", f"[b $warning]{head}{esc(plan['handoffChange'])}[/]"))
        else:
            out.append(line("", f"[b]{head}[/][$text-muted]{esc(plan['handoffChange'])}[/]"))
    if out:
        out[0].add_class("gap")  # a blank line between the items and the closing notes
    return out


class PlanHead(Static):
    class Toggled(Message):
        def __init__(self, key: tuple) -> None:
            super().__init__()
            self.key = key

    def __init__(self, text: str, key: tuple) -> None:
        super().__init__(text, classes="plan-head")
        self.key = key

    def on_click(self, event: Click) -> None:
        self.post_message(self.Toggled(self.key))


class AgentView(View):
    key = "agent"

    DEFAULT_CSS = """
    AgentView #activity-msg { padding: 0 1; color: $text-muted; }
    AgentView #plans { height: auto; }
    AgentView .stage-head { padding: 0 1; margin-top: 1; text-style: bold; }
    AgentView .stage-head.first { margin-top: 0; }
    AgentView .plan-head { padding: 0 1 0 3; }
    AgentView .plan-head:hover { background: $panel; }
    AgentView .plan-body { height: auto; padding: 0 1 0 5; }
    AgentView .line { height: auto; }
    AgentView .line .mark { width: 4; }
    AgentView .line .text { width: 1fr; }
    AgentView .line.gap { margin-top: 1; }
    """

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.ctx: Context | None = None
        self.flash: set[tuple] = set()
        self.open: set[tuple] | None = None  # (stage id, plan time) of the open plans

    def compose(self):
        yield Static("", id="activity-msg")
        yield VerticalGroup(id="plans")

    def update_from(self, ctx: Context) -> None:
        old, self.ctx = self.ctx, ctx
        if old is not None and motion_on(self):
            self.flash = done_keys(ctx) - done_keys(old)
            if self.flash:
                self.set_timer(FLASH, self._end_flash)
        self._build(ctx)

    def _end_flash(self) -> None:
        self.flash = set()
        if self.ctx is not None:
            self._build(self.ctx)

    def _default_open(self, ctx: Context, activity: dict) -> set[tuple]:
        """The newest plan of the user's stage, or of every stage when none is picked."""
        out = set()
        for sid, plans in activity.items():
            if plans and (sid == ctx.mine or ctx.mine is None):
                out.add((sid, plans[-1]["time"]))
        return out

    def _build(self, ctx: Context) -> None:
        msg = self.query_one("#activity-msg", Static)
        box = self.query_one("#plans", VerticalGroup)
        box.remove_children()
        if not ctx.activity_report.ok:
            msg.update(ctx.t("activity.invalid"))
            msg.display = True
            return
        activity = ctx.activity or {}
        if not any(activity.values()):
            msg.update(ctx.t("activity.empty"))
            msg.display = True
            return
        msg.display = False
        if self.open is None:
            self.open = self._default_open(ctx, activity)
        widgets: list = []
        for n, sid in enumerate(stage_order(ctx, activity)):
            s = ctx.stage_by_id.get(sid)
            you = f"  [b $accent]{esc(ctx.t('activity.you'))}[/]" if sid == ctx.mine else ""
            widgets.append(Static(f"{esc(s['name'] if s else sid)}{you}",
                                  classes="stage-head first" if n == 0 else "stage-head"))
            for plan in reversed(activity[sid]):
                key = (sid, plan["time"])
                is_open = key in self.open
                items = plan["items"]
                done = sum(it["done"] for it in items)
                colour = "$success" if done == len(items) else "$warning"
                fold = esc("[-]" if is_open else "[+]")
                widgets.append(PlanHead(
                    f"[$frame]{fold}[/] [$text-muted]{plan['time'][5:16].replace('T', ' ')}[/]  {esc(plan['title'])}"
                    f"  [{colour}]{done}/{len(items)}[/]", key))
                if is_open:
                    lines = [item_line(ctx, it, (sid, plan["time"], i) in self.flash) for i, it in enumerate(items)]
                    widgets.append(VerticalGroup(*lines, *extra_lines(ctx, plan), classes="plan-body"))
        box.mount_all(widgets)

    def on_plan_head_toggled(self, event: PlanHead.Toggled) -> None:
        if self.open is None or self.ctx is None:
            return
        self.open ^= {event.key}
        self._build(self.ctx)

    @staticmethod
    def status(ctx: Context, seen: object) -> Status | None:
        plan = latest_plan(ctx)
        if plan is None:
            return Status(ctx.t("tab.agent_idle"))
        items = plan["items"]
        if any(it.get("byUser") and not it["done"] for it in items):
            return Status(ctx.t("tab.agent_you"), "act")
        done = sum(it["done"] for it in items)
        if done == len(items):
            return Status(ctx.t("tab.agent_done"))
        return Status(ctx.t("tab.agent_progress", done=str(done), total=str(len(items))))
