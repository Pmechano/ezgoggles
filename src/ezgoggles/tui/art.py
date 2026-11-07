"""A hand-drawn pixel-art brass gear, shown with half blocks (two pixels per cell).

Light comes from the top left: edges that face it are polished brass,
edges that face away are copper, the rest is plain brass.
"""

from __future__ import annotations

from functools import lru_cache

from textual.containers import Horizontal, Vertical
from textual.widgets import Static

# 16 x 16 pixels. '#' is metal, '.' is empty.
# Eight teeth, a rim, four spokes, a hub ring and an axle hole.
GEAR = """
......####......
.##...####...##.
.##############.
..############..
..####.##.####..
.####..##..####.
####..####..####
#######..#######
#######..#######
####..####..####
.####..##..####.
..####.##.####..
..############..
.##############.
.##...####...##.
......####......
"""

EMPTY, BODY, LIGHT, SHADE = 0, 1, 2, 3


@lru_cache(maxsize=None)
def pixels(drawing: str = GEAR) -> tuple[tuple[int, ...], ...]:
    rows = [line for line in drawing.strip().splitlines()]
    h, w = len(rows), len(rows[0])
    solid = [[ch == "#" for ch in row] for row in rows]
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            if not solid[y][x]:
                row.append(EMPTY)
                continue
            # sum the directions in which the pixel is open
            nx = ny = 0
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if not (0 <= xx < w and 0 <= yy < h and solid[yy][xx]):
                    nx += dx
                    ny += dy
            facing = -(nx + ny)  # > 0: the open side faces the top left
            row.append(LIGHT if facing > 0 else SHADE if facing < 0 else BODY)
        out.append(tuple(row))
    return tuple(out)


def to_markup(px: tuple[tuple[int, ...], ...], colours: dict[int, str]) -> str:
    """Half-block Textual markup. colours maps BODY, LIGHT and SHADE to colours."""
    lines = []
    for y in range(0, len(px), 2):
        top = px[y]
        bottom = px[y + 1] if y + 1 < len(px) else tuple(EMPTY for _ in top)
        cells = []
        for t, b in zip(top, bottom):
            if t == EMPTY and b == EMPTY:
                cells.append(" ")
            elif b == EMPTY:
                cells.append(f"[{colours[t]}]▀[/]")
            elif t == EMPTY:
                cells.append(f"[{colours[b]}]▄[/]")
            elif t == b:
                cells.append(f"[{colours[t]}]█[/]")
            else:
                cells.append(f"[{colours[t]} on {colours[b]}]▀[/]")
        lines.append("".join(cells))
    return "\n".join(lines)


# ---------- widgets ----------

# Theme variables, so the gear follows the dark and light brass themes.
TONES = {BODY: "$primary", LIGHT: "$accent", SHADE: "$secondary"}


class Gear(Static):
    DEFAULT_CSS = "Gear { width: 16; height: 8; }"

    def on_mount(self) -> None:
        self.update(to_markup(pixels(), TONES))


class Nameplate(Horizontal):
    """The gear with the name beside it."""

    DEFAULT_CSS = """
    Nameplate { height: auto; width: 100%; padding: 1 0 1 1; }
    Nameplate > Vertical { width: 1fr; height: auto; padding: 1 0 0 3; }
    Nameplate .brand { text-style: bold; color: $accent; }
    Nameplate .line { color: $text; }
    Nameplate .muted { color: $text-muted; }
    """

    def __init__(self, *lines: tuple[str, str], **kw) -> None:
        super().__init__(**kw)
        self.lines = lines

    def compose(self):
        yield Gear()
        with Vertical():
            for text, cls in self.lines:
                yield Static(text, classes=cls)
