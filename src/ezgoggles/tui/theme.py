"""Themes in the style of an old amber terminal.

One hue. Importance shows as brightness: dim for notes, plain for text,
bright for what is important now. Reverse video marks the one thing that is
selected. Regions are separated by ASCII frames, not by background fills,
so the screen stays calm.
"""

from __future__ import annotations

from textual.theme import Theme


def _vars(ink: str, dim: str, frame: str, bright: str, back: str) -> dict[str, str]:
    return {
        "text-muted": dim,
        "frame": frame,
        "footer-background": back,
        "footer-foreground": ink,
        "footer-key-foreground": bright,
        "footer-key-background": back,
        "footer-description-foreground": ink,
        "footer-description-background": back,
        "footer-item-background": back,
        "block-cursor-background": bright,
        "block-cursor-foreground": back,
        "scrollbar": frame,
        "scrollbar-hover": ink,
        "scrollbar-active": bright,
        "scrollbar-background": back,
        "scrollbar-background-hover": back,
        "scrollbar-background-active": back,
        "scrollbar-corner-color": back,
    }


AMBER_DARK = Theme(
    name="ezgoggles-amber-dark",
    dark=True,
    background="#0d0a06",  # phosphor black
    surface="#0d0a06",
    panel="#1a140b",
    foreground="#e9a83a",  # amber
    primary="#e9a83a",
    secondary="#e9a83a",
    accent="#ffd24d",  # bright amber: the highlight
    success="#e9a83a",
    warning="#ff8a2b",  # hot amber: needs the user
    error="#ff5a36",
    variables=_vars(ink="#e9a83a", dim="#8c6526", frame="#b07c26", bright="#ffd24d", back="#0d0a06"),
)

AMBER_LIGHT = Theme(
    name="ezgoggles-amber-light",
    dark=False,
    background="#f3ead7",  # paper
    surface="#f3ead7",
    panel="#e6d8bb",
    foreground="#5a3c12",  # sepia ink
    primary="#5a3c12",
    secondary="#5a3c12",
    accent="#9a5b00",
    success="#5a3c12",
    warning="#b8470c",
    error="#a32a12",
    variables=_vars(ink="#5a3c12", dim="#9c7f52", frame="#8f6a2e", bright="#9a5b00", back="#f3ead7"),
)

THEMES = (AMBER_DARK, AMBER_LIGHT)

# user.json theme -> Textual theme name
THEME = {"dark": AMBER_DARK.name, "light": AMBER_LIGHT.name}
