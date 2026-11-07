from __future__ import annotations

from ...context import Context
from ...model import stage_label, topo_order, upstream
from .base import MarkdownPanel


class StagePanel(MarkdownPanel):
    key = "stage"

    @staticmethod
    def markdown(ctx: Context) -> str:
        by_id = ctx.stage_by_id
        if ctx.mine is None:
            ids = ", ".join(f"`{s['id']}`" for s in topo_order(ctx.stages))
            return ctx.t("stage.none", branch=ctx.branch or "?", name=ctx.user.name or "<name>", ids=ids)

        s = by_id[ctx.mine]
        frm = ", ".join(stage_label(u) for u in upstream(ctx.stages, ctx.mine)) or ctx.t("stage.start")
        nxt = ", ".join(stage_label(by_id[n]) for n in s["next"] if n in by_id) or ctx.t("stage.end")
        lines = [
            f"### {stage_label(s)}",
            "",
            f"- {ctx.t('stage.path')}: `{s['path']}`",
            f"- {ctx.t('stage.from')}: {frm}",
            f"- {ctx.t('stage.input')}: {s['input']}",
            f"- {ctx.t('stage.output')}: {s['output']}",
            f"- {ctx.t('stage.next')}: {nxt}",
        ]
        if ctx.user.mode == "learn" and s.get("detail", "").strip():
            lines += ["", f"#### {ctx.t('stage.detail')}", "", s["detail"].strip()]
        return "\n".join(lines)
