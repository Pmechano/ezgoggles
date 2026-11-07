from __future__ import annotations

from textual.widgets import Markdown, Static

from ...context import Context
from ...model import topo_order
from .base import MarkdownPanel, map_problem


def flow_markup(ctx: Context) -> str:
    """The pipeline as one line of chips. The user's stage stands out."""
    order = topo_order(ctx.stages)
    if len(order) < 2 or any(len(s["next"]) > 1 for s in order):
        return ""
    chips = []
    for s in order:
        name = s["name"].replace("[", r"\[")
        style = "b reverse $accent" if s["id"] == ctx.mine else "$foreground on $panel"
        chips.append(f"[{style}] {name} [/]")
    return " [$text-muted]→[/] ".join(chips)


class MapPanel(MarkdownPanel):
    """Whole first: the goal and the flow. Then one short entry per stage."""

    key = "map"

    DEFAULT_CSS = "MapPanel #flow { padding: 0 1 1 1; }"

    def compose(self):
        yield Markdown("", id="map-goal")
        yield Static("", id="flow")
        yield Markdown("", id="map-stages")

    def update_from(self, ctx: Context) -> None:
        problem = map_problem(ctx)
        flow = self.query_one("#flow", Static)
        if problem:
            self.query_one("#map-goal", Markdown).update(problem)
            self.query_one("#map-stages", Markdown).update("")
            flow.display = False
            return
        m = ctx.map
        self.query_one("#map-goal", Markdown).update(f"**{m['title']}**{ctx.t('punct.colon')}{m['goal'].strip()}")
        markup = flow_markup(ctx)
        flow.display = bool(markup)
        flow.update(markup)
        self.query_one("#map-stages", Markdown).update(self.markdown(ctx))

    @staticmethod
    def markdown(ctx: Context) -> str:
        """The stage list. The goal and the flow line are separate widgets."""
        by_id = ctx.stage_by_id
        order = topo_order(ctx.stages)
        linear = all(len(s["next"]) <= 1 for s in order)
        colon = ctx.t("punct.colon")
        lines = []
        for s in order:
            you = f"  {ctx.t('stage.you')}" if s["id"] == ctx.mine else ""
            lines.append(f"- **{s['name']}**{you}{colon}{s['does']}")
            lines.append(f"    - {s['input']} → {s['output']}")
            if not linear and s["next"]:
                names = ", ".join(by_id[n]["name"] for n in s["next"] if n in by_id)
                lines.append(f"    - {ctx.t('map.goes_to')}{colon}{names}")
        return "\n".join(lines)
