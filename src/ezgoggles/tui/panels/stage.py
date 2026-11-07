from __future__ import annotations

from textual.widgets import Collapsible, Markdown

from ...context import Context
from ...model import topo_order, upstream
from .base import MarkdownPanel, map_problem


class StagePanel(MarkdownPanel):
    """What I do, what I get and from whom, what I give and to whom. Inner detail is folded."""

    key = "stage"

    def compose(self):
        yield Markdown("", id="stage-md")
        with Collapsible(title="", collapsed=True, id="stage-detail"):
            yield Markdown("", id="stage-detail-md")

    def update_from(self, ctx: Context) -> None:
        self.query_one("#stage-md", Markdown).update(map_problem(ctx) or self.markdown(ctx))
        detail = self.query_one("#stage-detail", Collapsible)
        text = self.detail(ctx)
        detail.display = bool(text)
        if text:
            detail.title = ctx.t("stage.detail")
            self.query_one("#stage-detail-md", Markdown).update(text)

    @staticmethod
    def detail(ctx: Context) -> str:
        if ctx.map is None or ctx.mine is None or ctx.user.mode != "learn":
            return ""
        return ctx.stage_by_id[ctx.mine].get("detail", "").strip()

    @staticmethod
    def markdown(ctx: Context) -> str:
        if ctx.mine is None:
            names = ", ".join(s["name"] for s in topo_order(ctx.stages))
            return ctx.t("stage.none", names=names)

        s = ctx.stage_by_id[ctx.mine]
        ups = upstream(ctx.stages, ctx.mine)
        downs = [ctx.stage_by_id[n] for n in s["next"] if n in ctx.stage_by_id]
        if ups:
            got = ctx.t("stage.from", who=", ".join(u["name"] for u in ups), what=s["input"])
        else:
            got = ctx.t("stage.first", what=s["input"])
        if downs:
            give = ctx.t("stage.to", who=", ".join(d["name"] for d in downs), what=s["output"])
        else:
            give = ctx.t("stage.last", what=s["output"])
        return "\n".join([
            ctx.t("stage.take", name=s["name"], does=s["does"]),
            "",
            f"- {got}",
            f"- {give}",
            "",
            f"*{ctx.t('stage.where', path=s['path'])}*",
        ])
