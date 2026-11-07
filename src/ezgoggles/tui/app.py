"""The ezgoggles TUI. It shows files. It writes only the user's personal settings."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Footer, Static

from .. import i18n
from ..context import Context, Watcher
from ..launch import pidfile
from ..paths import Paths
from ..user import User, load_user, save_user
from .panels import PANELS, Panel
from .setup import SetupScreen
from .theme import THEME, THEMES

NARROW = 110  # columns; below this the two columns stack into one
POLL = 1.0  # seconds


class MainScreen(Screen):
    """Shows the panels of PANELS, opened one by one. Knows nothing about what a panel shows."""

    def __init__(self) -> None:
        super().__init__()
        self.ctx: Context | None = None

    @property
    def gapp(self) -> "GogglesApp":
        return self.app  # type: ignore[return-value]

    def t(self, key: str, **kw: str) -> str:
        return i18n.tr(self.gapp.user.language, key, **kw)

    def compose(self) -> ComposeResult:
        self._bind_keys()
        with Horizontal(id="topbar"):
            yield Static(f"[$accent]⚙[/] [b $accent]ezgoggles[/]  [$text-muted]│[/]  [b]{self.gapp.paths.root.name}[/]", id="brand")
            yield Static("", id="status")
        yield Static("", id="notice")
        with Horizontal(id="body"):
            for column, side in (("main", False), ("side", True)):
                with VerticalScroll(id=column, classes="col"):
                    for i, panel in enumerate(PANELS):
                        if panel.side == side:
                            yield self._section(i, panel)
        yield Footer()

    def _bind_keys(self) -> None:
        """Footer labels in the user's language."""
        self._bindings = BindingsMap([
            Binding("s", "settings", self.t("keys.settings")),
            Binding("ctrl+q", "app.quit", self.t("keys.quit")),
        ])
        self.refresh_bindings()

    def _section(self, i: int, panel: type[Panel]) -> Collapsible:
        title = f"{i + 1}  {self.t(f'panel.{panel.key}')}"
        ack = Button(f"✓ {self.t('panel.ack')}", id=f"ack-{i}", classes="ack", compact=True, flat=True)
        return Collapsible(
            panel(id=f"panel-{panel.key}"), ack, title=title, collapsed=False, id=f"sec-{i}",
            collapsed_symbol="▸", expanded_symbol="▾",
        )

    def on_mount(self) -> None:
        self._layout(self.app.size.width)
        self.refresh_data(force=True)
        self.set_interval(POLL, self.refresh_data)

    def on_resize(self, event) -> None:
        self._layout(event.size.width)

    def _layout(self, width: int) -> None:
        self.query_one("#body").set_class(width < NARROW, "narrow")

    # ----- data -----

    def refresh_data(self, force: bool = False) -> None:
        ctx = self.gapp.watcher.poll(self.gapp.user, force=force)
        if ctx is None:
            return
        self.ctx = ctx
        self._render_status(ctx)
        for panel in self.query(Panel):
            panel.update_from(ctx)
        self._apply_step()

    def _render_status(self, ctx: Context) -> None:
        parts = [f"[b]{ctx.user.name}[/]", ctx.t(f"mode.{ctx.user.mode}")]
        if ctx.branch:
            parts.append(f"{ctx.t('status.branch')} {ctx.branch}")
        if ctx.changed:
            parts.append(ctx.t("status.changed", n=str(ctx.changed)))
        self.query_one("#status", Static).update("  [$text-muted]·[/]  ".join(parts))
        notice = self.query_one("#notice", Static)
        notice.display = ctx.translation in ("missing", "stale", "invalid")
        if notice.display:
            notice.update(ctx.t(f"translation.{ctx.translation}"))

    # ----- progressive view -----

    def _step(self) -> int:
        return max(1, min(self.gapp.user.step, len(PANELS)))

    def _apply_step(self) -> None:
        step = self._step()
        last = len(PANELS) - 1
        for i in range(len(PANELS)):
            current = i == step - 1 and i < last
            self.query_one(f"#sec-{i}").display = i < step
            self.query_one(f"#sec-{i}").set_class(current, "current")
            self.query_one(f"#ack-{i}").display = current
        for column, side in (("#main", False), ("#side", True)):
            self.query_one(column).display = any(p.side == side for p in PANELS[:step])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if not bid.startswith("ack-"):
            return
        user = self.gapp.user
        step = self._step()
        if int(bid[4:]) == step - 1 and step < len(PANELS):
            user.step = step + 1
            save_user(self.gapp.paths, user)
            self._apply_step()
            nxt = self.query_one(f"#sec-{step}", Collapsible)
            nxt.collapsed = False
            self.call_after_refresh(nxt.scroll_visible)

    def action_settings(self) -> None:
        self.gapp.open_setup(first=False)


class GogglesApp(App):
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen { background: $background; }

    #topbar { height: 2; padding: 0 2; background: $panel; border-bottom: double $primary 45%; }
    #brand { width: auto; }
    #status { width: 1fr; text-align: right; color: $text; margin-left: 4; }
    #notice { padding: 0 2; margin: 1 2 0 2; border-left: thick $warning; background: $warning 10%; }

    #body { height: 1fr; padding: 1 1 0 1; }
    .col { width: 1fr; height: 100%; padding: 0 1; scrollbar-size-vertical: 1; }
    #body.narrow { layout: vertical; overflow-y: auto; scrollbar-size-vertical: 1; }
    #body.narrow > .col { width: 100%; height: auto; overflow-y: hidden; }

    Collapsible {
        background: transparent;
        border: round $primary 35%;
        padding: 0 1 0 0;
        margin: 0 0 1 0;
    }
    Collapsible.current { border: double $accent; }
    Collapsible > CollapsibleTitle { text-style: bold; padding: 0 1; color: $primary; }
    Collapsible.current > CollapsibleTitle { color: $accent; }
    Collapsible > CollapsibleTitle:hover { background: $primary 15%; color: $accent; }
    Collapsible > Contents { padding: 1 0 0 1; }

    Markdown { height: auto; margin: 0; padding: 0 1; background: transparent; }
    Button.ack {
        width: auto; min-width: 0; height: 1; margin: 1 0 1 1; padding: 0 2;
        border: none; color: $success; background: $success 15%; text-style: bold;
    }
    Button.ack:hover, Button.ack:focus { background: $success 30%; text-style: bold; }
    """

    def __init__(self, paths: Paths) -> None:
        super().__init__()
        self.paths = paths
        self.user = load_user(paths)
        self.watcher = Watcher(paths)
        self.title = f"ezgoggles - {paths.root.name}"

    def on_mount(self) -> None:
        for theme in THEMES:
            self.register_theme(theme)
        self.theme = THEME[self.user.theme]
        self.push_screen(MainScreen())
        if not self.user.ready:
            self.open_setup(first=True)

    def open_setup(self, first: bool) -> None:
        def done(result: User | None) -> None:
            if result is None:
                return
            self.user = result
            save_user(self.paths, result)
            self.theme = THEME[result.theme]
            self.call_later(self._rebuild_main)

        self.push_screen(SetupScreen(self.user, first), done)

    async def _rebuild_main(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            await screen.recompose()
            screen._layout(self.size.width)
            screen.refresh_data(force=True)


def run(paths: Paths) -> int:
    if pidfile.other_tui_pid(paths):
        print("ezgoggles: the TUI is already running for this project.")
        return 0
    pidfile.claim(paths)
    try:
        GogglesApp(paths).run()
    finally:
        pidfile.release(paths)
    return 0
