"""The ezgoggles TUI. It shows files. It writes only the user's personal settings."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Footer, Static

from .. import i18n
from ..context import Context, Watcher
from ..launch import pidfile
from ..paths import Paths
from ..user import User, load_user, save_user
from .panels import PANELS, Panel
from .setup import THEME, SetupScreen

NARROW = 110  # columns; below this the two columns stack into one
POLL = 1.0  # seconds


class MainScreen(Screen):
    """Shows the panels of PANELS, opened one by one. Knows nothing about what a panel shows."""

    BINDINGS = [
        Binding("s", "settings", "Settings / 设置"),
        Binding("ctrl+q", "app.quit", "Quit / 退出"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.ctx: Context | None = None

    @property
    def gapp(self) -> "GogglesApp":
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        user = self.gapp.user
        yield Static("", id="status")
        yield Static("", id="notice")
        with Horizontal(id="body"):
            for column, side in (("main", False), ("side", True)):
                with VerticalScroll(id=column, classes="col"):
                    for i, panel in enumerate(PANELS):
                        if panel.side == side:
                            yield self._section(i, panel, user)
        yield Footer()

    def _section(self, i: int, panel: type[Panel], user: User) -> Collapsible:
        title = f"{i + 1} · {i18n.tr(user.language, f'panel.{panel.key}')}"
        ack = Button(i18n.tr(user.language, "panel.ack"), id=f"ack-{i}", classes="ack")
        return Collapsible(panel(id=f"panel-{panel.key}"), ack, title=title, collapsed=False, id=f"sec-{i}")

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
        parts = [ctx.user.name, ctx.t(f"mode.{ctx.user.mode}")]
        if ctx.branch:
            parts.append(f"{ctx.t('status.branch')}: {ctx.branch}")
        if ctx.changed is not None:
            parts.append(f"{ctx.t('status.changed')}: {ctx.changed}")
        self.query_one("#status", Static).update("  ·  ".join(parts))
        notice = self.query_one("#notice", Static)
        notice.display = ctx.translation in ("missing", "stale", "invalid")
        if notice.display:
            notice.update(ctx.t(f"translation.{ctx.translation}"))

    # ----- progressive view -----

    def _step(self) -> int:
        return max(1, min(self.gapp.user.step, len(PANELS)))

    def _apply_step(self) -> None:
        step = self._step()
        for i, panel in enumerate(PANELS):
            self.query_one(f"#sec-{i}").display = i < step
            self.query_one(f"#ack-{i}").display = i == step - 1 and i < len(PANELS) - 1
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
    CSS = """
    #status { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    #notice { padding: 0 1; background: $warning-muted; color: $text; }
    #body { height: 1fr; }
    .col { width: 1fr; height: 100%; padding: 0 1; }
    #body.narrow { layout: vertical; overflow-y: auto; }
    #body.narrow > .col { width: 100%; height: auto; overflow-y: hidden; }
    Collapsible { margin-bottom: 1; }
    Markdown { height: auto; margin: 0; padding: 0 1; }
    .ack { margin: 1 0 0 1; }
    """

    def __init__(self, paths: Paths) -> None:
        super().__init__()
        self.paths = paths
        self.user = load_user(paths)
        self.watcher = Watcher(paths)
        self.title = f"ezgoggles - {paths.root.name}"

    def on_mount(self) -> None:
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
