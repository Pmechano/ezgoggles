"""The View extension point.

A view is one tab of the main screen. The main screen shows one view at a
time. Each tab shows the view's name and a short status, so the user can
see if a view is worth a look without opening it.

To add a view:
  1. Subclass View in a new module in this package.
  2. Set `key`. The tab name is the locale string `view.<key>`, and the
     tour hint is `tour.<key>`.
  3. Implement `update_from(ctx)`.
  4. Optional: `modes` (the modes that show it), `tour` (part of the
     first-start tour), `token` and `status` (the tab status), `entered`
     (runs when the user opens the tab) and `move` (the up/down keys).
  5. Add the class to VIEWS in views/__init__.py. The order of VIEWS is
     the order of the tabs and of the tour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual.containers import VerticalGroup
from textual.markup import escape

from ...context import Context
from ...user import User

LEVELS = ("quiet", "new", "act")


@dataclass(frozen=True)
class Status:
    """The short text on a tab.

    level: quiet (plain information), new (changed since the user last
    looked), act (the user must do something). Only `act` takes a strong
    colour, so that it stands out.
    """

    text: str
    level: str = "quiet"


class View(VerticalGroup):
    key: ClassVar[str] = ""
    modes: ClassVar[tuple[str, ...] | None] = None  # None: all modes
    tour: ClassVar[bool] = True

    DEFAULT_CSS = "View { height: auto; }"

    @classmethod
    def shown_for(cls, user: User) -> bool:
        return cls.modes is None or user.mode in cls.modes

    def update_from(self, ctx: Context) -> None:
        raise NotImplementedError

    @staticmethod
    def token(ctx: Context) -> object:
        """What the user saw on this view, as JSON data. None: the view does not track it.

        The main screen keeps the token of the last visit. `status` gets it
        as `seen`, and can tell the user that something changed.
        """
        return None

    @staticmethod
    def status(ctx: Context, seen: object) -> Status | None:
        return None

    def entered(self, ctx: Context, first: bool) -> None:
        """The user opened this tab. `first`: during the tour, for the first time."""

    def move(self, delta: int) -> bool:
        """Up/down keys. Return False to let the page scroll instead."""
        return False


def map_problem(ctx: Context) -> str | None:
    """The message to show instead of map content, or None if the map is fine."""
    if ctx.map is not None:
        return None
    return ctx.t("map.missing") if not ctx.paths.map.exists() else ctx.t("map.invalid")


def esc(text: str) -> str:
    """Agent text is shown as text, never as markup."""
    return escape(text)
