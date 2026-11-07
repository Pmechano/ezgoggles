"""The Panel extension point.

A panel is one section of the main screen. The main screen wraps each panel
in a collapsible section with a number, a title and an "I have read this"
button, and opens the panels one by one in the order of PANELS.

To add a panel:
  1. Subclass Panel (or MarkdownPanel) in a new module in this package.
  2. Set `key`; the title is the locale string `panel.<key>`.
  3. Implement `update_from(ctx)` (or `markdown(ctx)` for a MarkdownPanel).
  4. Add the class to PANELS in panels/__init__.py.
"""

from __future__ import annotations

from typing import ClassVar

from textual.containers import Vertical
from textual.widgets import Markdown

from ...context import Context


class Panel(Vertical):
    key: ClassVar[str] = ""
    side: ClassVar[bool] = False  # wide screens show side panels in the right column

    DEFAULT_CSS = "Panel { height: auto; }"

    def update_from(self, ctx: Context) -> None:
        raise NotImplementedError


def map_problem(ctx: Context) -> str | None:
    """The message to show instead of map content, or None if the map is fine."""
    if ctx.map is not None:
        return None
    return ctx.t("map.missing") if not ctx.paths.map.exists() else ctx.t("map.invalid")


class MarkdownPanel(Panel):
    """A panel that shows Markdown built from the map."""

    def compose(self):
        yield Markdown("")

    def update_from(self, ctx: Context) -> None:
        self.query_one(Markdown).update(map_problem(ctx) or self.markdown(ctx))

    @staticmethod
    def markdown(ctx: Context) -> str:
        """Called only when ctx.map is valid."""
        raise NotImplementedError
