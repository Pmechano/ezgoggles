from __future__ import annotations

from ...context import Context
from ...model import stage_label, topo_order
from .base import MarkdownPanel


class MapPanel(MarkdownPanel):
    key = "map"

    @staticmethod
    def markdown(ctx: Context) -> str:
        m = ctx.map
        by_id = ctx.stage_by_id
        order = topo_order(ctx.stages)
        lines = [f"**{m['title']}**", "", m["goal"].strip(), ""]

        if len(order) > 1 and all(len(s["next"]) <= 1 for s in order):
            chain = " → ".join(f"`{s['id']}`" for s in order)
            lines += [f"{ctx.t('map.flow')}: {chain}", ""]

        for s in order:
            you = f"  {ctx.t('stage.you')}" if s["id"] == ctx.mine else ""
            nxt = ", ".join(stage_label(by_id[n]) for n in s["next"] if n in by_id) or ctx.t("stage.end")
            lines += [
                f"#### {stage_label(s)}{you}",
                "",
                f"- {ctx.t('stage.path')}: `{s['path']}`",
                f"- {ctx.t('stage.input')}: {s['input']}",
                f"- {ctx.t('stage.output')}: {s['output']}",
                f"- {ctx.t('stage.next')}: {nxt}",
                "",
            ]
        return "\n".join(lines).rstrip()
