"""The code layer, for learning mode only: the files that the data of the user's stage goes through."""

from __future__ import annotations

import json

from textual.containers import VerticalGroup
from textual.widgets import Static

from ...context import Context
from ..widgets import DOT_TIME, Arrow
from .base import Status, View, esc, map_problem


def entry(ctx: Context) -> dict | None:
    return ctx.code.get(ctx.mine) if ctx.mine else None


class CodeView(View):
    key = "code"
    modes = ("learn",)

    DEFAULT_CSS = """
    CodeView #code-msg { color: $text-muted; }
    CodeView #code { height: auto; }
    CodeView .end { padding: 0 1; color: $text-muted; }
    CodeView .step { padding: 0 1; }
    CodeView Arrow { padding: 0 0 0 3; }
    CodeView #code-time { color: $text-muted; margin-top: 1; padding: 0 1; }
    """

    def compose(self):
        yield Static("", id="code-msg")
        yield VerticalGroup(id="code")
        yield Static("", id="code-time")

    def update_from(self, ctx: Context) -> None:
        msg = self.query_one("#code-msg", Static)
        flow = self.query_one("#code", VerticalGroup)
        stamp = self.query_one("#code-time", Static)
        flow.remove_children()
        stamp.update("")
        e = entry(ctx)
        if (problem := map_problem(ctx)) or ctx.mine is None:
            text = problem or ctx.t("code.no_stage")
        elif ctx.code_report is not None and not ctx.code_report.ok:
            text = ctx.t("code.invalid")
        elif e is None:
            text = ctx.t("code.missing")
        else:
            text = ""
        msg.update(text)
        msg.display = bool(text)
        if text:
            return
        s = ctx.stage_by_id[ctx.mine]
        colon = ctx.t("punct.colon")
        widgets: list = [Static(f"{ctx.t('code.start')}{colon}{esc(s['input'])}", classes="end"), Arrow()]
        for i, step in enumerate(e["steps"]):
            widgets.append(Static(f"[b $accent]{esc(step['file'])}[/]\n[$foreground]{esc(step['does'])}[/]",
                                  classes="step"))
            widgets.append(Arrow())
        widgets.append(Static(f"{ctx.t('code.end')}{colon}[b]{esc(s['output'])}[/]", classes="end"))
        flow.mount_all(widgets)
        stamp.update(ctx.t("code.time", time=e["time"][:16].replace("T", " ")))

    def entered(self, ctx: Context, first: bool) -> None:
        """One dot goes from the input through every file to the output."""
        for i, arrow in enumerate(self.query(Arrow)):
            arrow.flow(delay=i * DOT_TIME)

    @staticmethod
    def token(ctx: Context) -> object:
        e = entry(ctx)
        return json.dumps(e, ensure_ascii=False, sort_keys=True) if e else None

    @staticmethod
    def status(ctx: Context, seen: object) -> Status | None:
        if ctx.map is None or ctx.mine is None:
            return None
        e = entry(ctx)
        if e is None:
            return Status(ctx.t("tab.code_none"))
        if seen is not None and seen != CodeView.token(ctx):
            return Status(ctx.t("tab.code_new"), "new")
        return None
