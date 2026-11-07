from __future__ import annotations

from ...context import Context
from ...model import topo_order
from .base import MarkdownPanel


class MapPanel(MarkdownPanel):
    """Whole first: the goal and the flow. Then one short entry per stage."""

    key = "map"

    @staticmethod
    def markdown(ctx: Context) -> str:
        m = ctx.map
        by_id = ctx.stage_by_id
        order = topo_order(ctx.stages)
        linear = all(len(s["next"]) <= 1 for s in order)
        colon = ctx.t("punct.colon")
        lines = [f"**{m['title']}**{colon}{m['goal'].strip()}", ""]

        if linear and len(order) > 1:
            lines += ["**" + " → ".join(s["name"] for s in order) + "**", ""]

        for s in order:
            you = f"  {ctx.t('stage.you')}" if s["id"] == ctx.mine else ""
            lines.append(f"- **{s['name']}**{you}{colon}{s['does']}")
            lines.append(f"    - {s['input']} → {s['output']}")
            if not linear and s["next"]:
                names = ", ".join(by_id[n]["name"] for n in s["next"] if n in by_id)
                lines.append(f"    - {ctx.t('map.goes_to')}{colon}{names}")
        return "\n".join(lines)
