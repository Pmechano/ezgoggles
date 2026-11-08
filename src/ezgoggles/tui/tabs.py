r"""Tabs in the style of an old terminal: a number and a name. A dot marks a tab worth a look.

     1 任务  / 2 流程 \  3 代码   4 Agent ●
    ---------        ---------------------------------

The open tab is in reverse video and has no line under it: it opens into the
page. The status text is not on the tab. It is the tooltip of the tab, so the
bar stays short and every word on it has a clear meaning.
"""

from __future__ import annotations

from textual.containers import HorizontalGroup
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from ..model import width
from .views.base import Status, esc
from .widgets import motion_on

DOT = {"new": "$foreground", "act": "$warning"}  # quiet statuses show no dot
GLINT_TIME = 0.5


class Tab(Static):
    """When a dot appears, a glint goes over the tab name once."""

    glint: reactive[float] = reactive(-1.0)

    class Picked(Message):
        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key

    def __init__(self, key: str, name: str, number: int) -> None:
        super().__init__("", id=f"tab-{key}", classes="tab")
        self.active = False
        self.key = key
        self.label = name
        self.number = number
        self.state: Status | None = None
        self.shown = False  # no glint for the first status

    def on_mount(self) -> None:
        self._draw()

    def set_status(self, status: Status | None) -> None:
        before = self.dot_colour
        first, self.shown = not self.shown, True
        self.state = status
        self.tooltip = status.text if status else None
        self._draw()
        if self.dot_colour and self.dot_colour != before and not first and motion_on(self):
            self.glint = 0.0
            self.animate("glint", float(len(self.label) + 2), duration=GLINT_TIME,
                         easing="in_out_sine", on_complete=self._end_glint)

    @property
    def dot_colour(self) -> str | None:
        return DOT.get(self.state.level) if self.state else None

    def _end_glint(self) -> None:
        self.glint = -1.0

    def watch_glint(self) -> None:
        self._draw()

    def _label_markup(self) -> str:
        if self.glint < 0:
            return esc(self.label)
        return "".join(
            f"[reverse]{esc(ch)}[/]" if abs(i - self.glint) < 1.2 else esc(ch) for i, ch in enumerate(self.label)
        )

    def _draw(self) -> None:
        dot = f" [b {self.dot_colour}]●[/]" if self.dot_colour else ""
        core = f" {self.number} {self._label_markup()}{dot} "
        cells = width(f" {self.number} {self.label}{' ●' if dot else ''} ")
        if self.active:
            # the closing backslash ends the string: before "[/]" it would escape the tag
            line1 = f"[$frame]/[/][b $background on $accent]{core}[/][$frame]" + "\\"
            line2 = " " * (cells + 2)
        else:
            line1 = f" {core} "
            line2 = f"[$frame]{'-' * (cells + 2)}[/]"
        self.update(f"{line1}\n{line2}")

    def set_active(self, on: bool) -> None:
        self.active = on
        self.set_class(on, "active")
        self._draw()

    def on_click(self, event: Click) -> None:
        self.post_message(self.Picked(self.key))


class TabBar(HorizontalGroup):
    DEFAULT_CSS = """
    TabBar { height: 2; }
    TabBar .tab { width: auto; height: 2; color: $text-muted; }
    TabBar .tab:hover { color: $foreground; }
    TabBar .rule { width: 1fr; height: 2; color: $frame; text-wrap: nowrap; text-overflow: clip; }
    """

    def __init__(self, tabs: list[tuple[str, str]], **kw) -> None:
        super().__init__(
            *(Tab(key, name, i + 1) for i, (key, name) in enumerate(tabs)),
            Static("\n" + "-" * 400, classes="rule"),
            **kw,
        )

    def tab(self, key: str) -> Tab:
        return self.query_one(f"#tab-{key}", Tab)

    def activate(self, key: str) -> None:
        for t in self.query(Tab):
            t.set_active(t.key == key)
