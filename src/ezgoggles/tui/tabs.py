"""Browser-style tabs. Each tab shows a view's name and its short status."""

from __future__ import annotations

from textual.containers import HorizontalGroup
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from .views.base import Status, esc
from .widgets import motion_on

COLOUR = {"quiet": "$text-muted", "new": "$accent", "act": "$warning"}
SYMBOL = {"quiet": "", "new": "•", "act": "!"}  # narrow screens show only these
GLINT_TIME = 0.5


class Tab(Static):
    """When the status changes, a glint goes over it once."""

    glint: reactive[float] = reactive(-1.0)

    class Picked(Message):
        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key

    def __init__(self, key: str, name: str) -> None:
        super().__init__("", id=f"tab-{key}", classes="tab")
        self.key = key
        self.label = name
        self.state: Status | None = None
        self.narrow = False
        self.shown = False  # no glint for the first status

    def on_mount(self) -> None:
        self._draw()

    def set_status(self, status: Status | None) -> None:
        changed = status != self.state and status is not None
        first, self.shown = not self.shown, True
        self.state = status
        self._draw()
        if changed and not first and motion_on(self):
            self.glint = 0.0
            self.animate("glint", float(len(status.text) + 2), duration=GLINT_TIME,
                         easing="in_out_sine", on_complete=self._end_glint)

    def _end_glint(self) -> None:
        self.glint = -1.0

    def watch_glint(self) -> None:
        self._draw()

    def _status_markup(self) -> str:
        s = self.state
        if s is None:
            return ""
        colour = COLOUR.get(s.level, COLOUR["quiet"])
        if self.narrow:
            sym = SYMBOL.get(s.level, "")
            return f" [b {colour}]{sym}[/]" if sym else ""
        if self.glint < 0:
            return f"  [{colour}]{esc(s.text)}[/]"
        out = []
        for i, ch in enumerate(s.text):
            bright = abs(i - self.glint) < 1.5
            out.append(f"[b reverse {colour}]{esc(ch)}[/]" if bright else f"[{colour}]{esc(ch)}[/]")
        return "  " + "".join(out)

    def _draw(self) -> None:
        self.update(f"{esc(self.label)}{self._status_markup()}")

    def on_click(self, event: Click) -> None:
        self.post_message(self.Picked(self.key))


class TabBar(HorizontalGroup):
    DEFAULT_CSS = """
    TabBar { height: 1; background: $panel; padding: 0 1; }
    TabBar .tab { width: auto; padding: 0 2; color: $text-muted; }
    TabBar .tab:hover { color: $foreground; background: $boost; }
    TabBar .tab.active { background: $background; color: $accent; text-style: bold; }
    """

    def __init__(self, tabs: list[tuple[str, str]], **kw) -> None:
        super().__init__(*(Tab(key, name) for key, name in tabs), **kw)

    def tab(self, key: str) -> Tab:
        return self.query_one(f"#tab-{key}", Tab)

    def activate(self, key: str) -> None:
        for t in self.query(Tab):
            t.set_class(t.key == key, "active")

    def set_narrow(self, narrow: bool) -> None:
        for t in self.query(Tab):
            if t.narrow != narrow:
                t.narrow = narrow
                t._draw()
