from __future__ import annotations

from rich.text import Text
from textual.theme import Theme
from textual.widgets import Static, Tree

from ...context import Context
from ...model import handoff_changed, topo_order
from .base import Panel


def stage_order(ctx: Context, activity: dict) -> list[str]:
    """Stages that have plans: the user's stage first, then data-flow order."""
    keys = [s["id"] for s in topo_order(ctx.stages) if s["id"] in activity]
    keys += [k for k in activity if k not in keys]
    if ctx.mine in keys:
        keys.remove(ctx.mine)
        keys.insert(0, ctx.mine)
    return keys


# Tree labels are Rich Text, which does not know theme variables, so the
# colours come from the active theme (`pal`). Agent text is never parsed as markup.


def palette(theme: Theme | None) -> dict[str, str]:
    t = theme or Theme(name="fallback", primary="#b8933a")
    return {
        "accent": t.accent or t.primary,
        "success": t.success or "green",
        "warning": t.warning or "yellow",
        "secondary": t.secondary or t.primary,
    }


def stage_label(ctx: Context, sid: str, pal: dict[str, str]) -> Text:
    s = ctx.stage_by_id.get(sid)
    t = Text(s["name"] if s else sid, style="bold")
    if sid == ctx.mine:
        t.append(f"  {ctx.t('stage.you')}", style=f"italic {pal['accent']}")
    return t


def plan_label(plan: dict, pal: dict[str, str]) -> Text:
    items = plan["items"]
    done = sum(1 for it in items if it["done"])
    t = Text(f"{plan['time'][5:16].replace('T', ' ')}  ", style="dim")
    t.append(plan["title"])
    t.append(f"  [{done}/{len(items)}]", style=pal["success"] if done == len(items) else pal["warning"])
    return t


def item_label(ctx: Context, item: dict, pal: dict[str, str]) -> Text:
    if item["done"]:
        t = Text("✓ ", style=pal["success"])
        t.append(item["text"], style="dim")
    else:
        t = Text("○ ", style="dim")
        t.append(item["text"])
    if item.get("byUser"):
        t.append(f"  ({ctx.t('activity.byuser')})", style=f"bold {pal['secondary']}")
    return t


def summary_label(ctx: Context, plan: dict) -> Text | None:
    if "summary" not in plan:
        return None
    t = Text(f"{ctx.t('activity.summary')}{ctx.t('punct.colon')}", style="bold")
    t.append(plan["summary"])
    return t


def handoff_label(ctx: Context, plan: dict, pal: dict[str, str]) -> Text | None:
    if "handoffChange" not in plan:
        return None
    head = f"{ctx.t('activity.handoff')}{ctx.t('punct.colon')}"
    if handoff_changed(plan):
        t = Text(f" {head}", style=f"bold reverse {pal['warning']}")
        t.append(f" {plan['handoffChange']}", style=f"bold {pal['warning']}")
        return t
    t = Text(head, style="bold")
    t.append(plan["handoffChange"], style="dim")
    return t


class ActivityPanel(Panel):
    key = "activity"
    side = True

    DEFAULT_CSS = """
    ActivityPanel #activity-msg { padding: 0 1; color: $text-muted; }
    ActivityPanel Tree { height: auto; max-height: 100%; background: transparent; padding: 0 1; }
    ActivityPanel Tree > .tree--guides { color: $foreground 25%; }
    """

    def compose(self):
        yield Static("", id="activity-msg")
        tree: Tree[None] = Tree("activity", id="activity")
        tree.show_root = False
        yield tree

    def update_from(self, ctx: Context) -> None:
        msg = self.query_one("#activity-msg", Static)
        tree = self.query_one("#activity", Tree)
        tree.clear()
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
        pal = palette(self.app.current_theme)
        for sid in stage_order(ctx, activity):
            snode = tree.root.add(stage_label(ctx, sid, pal), expand=(sid == ctx.mine or ctx.mine is None))
            for j, plan in enumerate(reversed(activity[sid])):
                pnode = snode.add(plan_label(plan, pal), expand=(j == 0))
                for it in plan["items"]:
                    pnode.add_leaf(item_label(ctx, it, pal))
                for extra in (summary_label(ctx, plan), handoff_label(ctx, plan, pal)):
                    if extra is not None:
                        pnode.add_leaf(extra)
