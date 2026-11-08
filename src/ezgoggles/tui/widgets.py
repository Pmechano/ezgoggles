"""Small widgets that more than one view uses."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from .views.base import esc

DOT_TIME = 0.35  # seconds for the dot to go down one arrow
FILL_TIME = 0.5


def motion_on(widget) -> bool:
    return widget.is_attached and widget.app.animation_level != "none"


class Arrow(Static):
    """The link between two steps of a flow, with the thing that goes through it.

        │  what goes through
        ▼

    `flow()` sends one dot down the arrow: it shows the direction of the
    data. `fill()` lights the arrow from top to bottom: something arrived.
    With motion off, both end at once and show nothing.
    """

    DEFAULT_CSS = "Arrow { height: auto; color: $text-muted; }"

    dot: reactive[float] = reactive(-1.0)
    lit: reactive[float] = reactive(-1.0)

    def __init__(self, text: str = "", end: str = "", final: bool = False, **kw) -> None:
        super().__init__("", **kw)
        self.text = text  # beside the line
        self.end = end  # beside the arrow head, for example "goes to X"
        self.final = final  # a final product: one line, no head

    def set(self, text: str, end: str = "", final: bool = False) -> None:
        self.text, self.end, self.final = text, end, final
        self._draw()

    def on_mount(self) -> None:
        self._draw()

    def watch_dot(self) -> None:
        self._draw()

    def watch_lit(self) -> None:
        self._draw()

    def _glyph(self, row: int, glyph: str) -> str:
        if self.dot >= 0 and int(self.dot) == row:
            return "[b $accent]●[/]"
        if self.lit >= 0 and self.lit > row:
            return f"[b $accent]{glyph}[/]"
        return glyph

    def _draw(self) -> None:
        text = f"  {esc(self.text)}" if self.text else ""
        if self.final:
            self.update(f"{self._glyph(0, '⇒')}{'  [b $foreground]' + esc(self.text) + '[/]' if self.text else ''}")
            return
        end = f"  {esc(self.end)}" if self.end else ""
        self.update(f"{self._glyph(0, '│')}{text}\n{self._glyph(1, '▼')}{end}")

    def flow(self, delay: float = 0.0) -> None:
        if not motion_on(self):
            return
        if delay:
            self.set_timer(delay, self._start_dot)
        else:
            self._start_dot()

    def _start_dot(self) -> None:
        self.dot = 0.0
        self.animate("dot", 1.99, duration=DOT_TIME, easing="in_out_cubic", on_complete=self._clear_dot)

    def _clear_dot(self) -> None:
        self.dot = -1.0

    def fill(self) -> None:
        if not motion_on(self):
            return
        self.lit = 0.0
        self.animate("lit", 2.0, duration=FILL_TIME, easing="out_cubic", on_complete=self._unlight)

    def _unlight(self) -> None:
        self.set_timer(0.6, self._clear_lit)

    def _clear_lit(self) -> None:
        self.lit = -1.0
