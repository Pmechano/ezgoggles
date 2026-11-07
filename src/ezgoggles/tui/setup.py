"""The setup page: language, name, mode and theme."""

from __future__ import annotations

from dataclasses import replace

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from .. import i18n
from ..user import MODES, NAME_RE, THEMES, User
from .theme import THEME



class SetupScreen(Screen[User]):
    """Shown on first start, and when the user presses 's'. Dismisses with the new User or None."""

    BINDINGS = [Binding("escape", "cancel", show=False)]

    DEFAULT_CSS = """
    SetupScreen { align: center middle; }
    #setup {
        width: 76; max-width: 100%; height: auto; max-height: 100%;
        padding: 1 3; border: double $accent; background: transparent;
    }
    #setup .title { margin-bottom: 0; }
    #setup .subtitle { color: $text-muted; margin-bottom: 1; }
    #setup .field { margin-top: 1; text-style: bold; color: $text-muted; }
    #setup .hint { color: $text-muted; }
    #setup RadioSet { width: 100%; border: none; background: transparent; padding: 0; }
    #setup RadioSet:focus { background: $boost; }
    #setup RadioSet.row { layout: horizontal; }
    #setup RadioSet.row RadioButton { width: auto; margin-right: 3; }
    #setup Input { margin: 0; }
    #setup #error { color: $error; height: auto; margin-top: 1; }
    #setup #save { margin-top: 1; width: auto; min-width: 0; padding: 0 4; text-style: bold; }
    """

    def __init__(self, user: User, first: bool) -> None:
        super().__init__()
        self.draft = replace(user)
        self.original_theme = user.theme
        self.first = first
        self.languages = i18n.available()

    def t(self, key: str) -> str:
        return i18n.tr(self.draft.language, key)

    def compose(self) -> ComposeResult:
        d = self.draft
        with VerticalScroll(id="setup"):
            yield Static(f"[$accent]⚙[/] [b $accent]ezgoggles[/]  [$text-muted]│[/]  [b]{self.t('setup.title')}[/]", classes="title")
            yield Static(self.t("setup.subtitle"), classes="subtitle")
            yield Label(self.t("setup.language"), classes="field")
            with RadioSet(id="language", classes="row"):
                for code in self.languages:
                    yield RadioButton(i18n.language_name(code), value=d.language == code)
            yield Label(self.t("setup.name"), classes="field")
            yield Input(value=d.name, placeholder="alice", id="name")
            yield Static(self.t("setup.name_hint"), classes="hint")
            yield Label(self.t("setup.mode"), classes="field")
            with RadioSet(id="mode"):
                for mode in MODES:
                    yield RadioButton(self.t(f"setup.mode_{mode}"), value=d.mode == mode)
            yield Label(self.t("setup.theme"), classes="field")
            with RadioSet(id="theme", classes="row"):
                for theme in THEMES:
                    yield RadioButton(self.t(f"setup.theme_{theme}"), value=d.theme == theme)
            yield Static("", id="error")
            yield Button(self.t("setup.save"), variant="primary", id="save", compact=True)

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        group = event.radio_set.id
        if group == "language":
            lang = self.languages[event.index]
            if lang != self.draft.language:
                self.draft.language = lang
                await self.recompose()
        elif group == "mode":
            self.draft.mode = MODES[event.index]
        elif group == "theme":
            self.draft.theme = THEMES[event.index]
            self.app.theme = THEME[self.draft.theme]

    def on_input_changed(self, event: Input.Changed) -> None:
        self.draft.name = event.value.strip().lower()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save":
            return
        error = self.query_one("#error", Static)
        if not NAME_RE.match(self.draft.name):
            error.update(self.t("setup.name_bad"))
            return
        if self.draft.mode not in MODES:
            error.update(self.t("setup.mode_bad"))
            return
        self.dismiss(self.draft)

    def action_cancel(self) -> None:
        if not self.first:
            self.app.theme = THEME[self.original_theme]
            self.dismiss(None)
