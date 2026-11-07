"""Brass themes: warm metal accents on quiet backgrounds.

Colour goes only to frames, titles and highlights. Body text stays plain,
so the content keeps the reader's attention.
"""

from __future__ import annotations

from textual.theme import Theme

BRASS_DARK = Theme(
    name="ezgoggles-brass-dark",
    dark=True,
    background="#16120e",  # walnut black
    surface="#1d1813",
    panel="#29211a",
    foreground="#e6dac2",  # parchment
    primary="#b8933a",  # brass
    secondary="#b87333",  # copper
    accent="#d9b25f",  # polished brass
    success="#6fa596",  # verdigris
    warning="#d08c3a",  # amber
    error="#c0583f",  # rust
    variables={
        "footer-key-foreground": "#d9b25f",
        "block-cursor-background": "#b8933a",
        "block-cursor-foreground": "#16120e",
        "scrollbar": "#3a2f22",
        "scrollbar-hover": "#5a4630",
        "scrollbar-active": "#b8933a",
    },
)

BRASS_LIGHT = Theme(
    name="ezgoggles-brass-light",
    dark=False,
    background="#f2e9d6",  # aged paper
    surface="#ebe0c9",
    panel="#e0d1b2",
    foreground="#3a2e21",  # sepia ink
    primary="#8a6a1e",  # dark brass
    secondary="#8a4f24",  # copper
    accent="#9c7623",
    success="#3d7a6b",  # verdigris
    warning="#a3621b",
    error="#9a3a25",
    variables={
        "footer-key-foreground": "#8a6a1e",
        "block-cursor-background": "#8a6a1e",
        "block-cursor-foreground": "#f2e9d6",
        "scrollbar": "#d6c49f",
        "scrollbar-hover": "#bfa775",
        "scrollbar-active": "#8a6a1e",
    },
)

THEMES = (BRASS_DARK, BRASS_LIGHT)

# user.json theme -> Textual theme name
THEME = {"dark": BRASS_DARK.name, "light": BRASS_LIGHT.name}
