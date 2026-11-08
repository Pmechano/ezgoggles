"""The ezgoggles TUI. It shows files. It writes only the user's personal state."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingsMap
from textual.css.scalar import ScalarOffset
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static, Tree

from .. import i18n
from ..context import Context, Watcher
from ..launch import pidfile
from ..paths import Paths, read_json, write_json
from ..user import User, load_user, save_user
from . import sound
from .setup import SetupScreen
from .tabs import TabBar
from .theme import THEME, THEMES
from .views import HOME, VIEWS, View
from .views.base import esc
from .widgets import motion_on

NARROW = 72  # columns; below this, tabs show a symbol instead of their status
POLL = 1.0  # seconds
SLIDE = 4  # columns that a view slides in from
SLIDE_TIME = 0.2
SKIPPED = 99  # user.step when the tour was skipped


class MainScreen(Screen):
    """Shows the views of VIEWS as tabs. Knows nothing about what a view shows."""

    AUTO_FOCUS = ""  # _enter() gives focus to the open view; a hidden tree must not take it

    def __init__(self) -> None:
        super().__init__()
        self.ctx: Context | None = None
        self.views: list[type[View]] = [v for v in VIEWS if v.shown_for(self.gapp.user)]
        self.keys = [v.key for v in self.views]
        self.seen: dict = {}
        raw = read_json(self.gapp.paths.seen)
        if isinstance(raw, dict):
            self.seen = raw
        self.entered_once: set[str] = set()
        tour = self.tour
        self.active = tour[self.gapp.user.step - 1] if self.in_tour else (HOME if HOME in self.keys else self.keys[0])
        self._act_before: set[str] = set()

    @property
    def gapp(self) -> "GogglesApp":
        return self.app  # type: ignore[return-value]

    def t(self, key: str, **kw: str) -> str:
        return i18n.tr(self.gapp.user.language, key, **kw)

    # ----- layout -----

    def compose(self) -> ComposeResult:
        self._bind_keys()
        with Vertical(id="chrome"):
            with Horizontal(id="topbar"):
                yield Static("", id="brand")
                yield Static("", id="status")
            yield Static("", id="goal")
            yield TabBar([(k, self.t(f"view.{k}")) for k in self.keys], id="tabs")
        yield Static("", id="notice")
        with VerticalScroll(id="page", can_focus=False):
            with Vertical(id="views"):
                for v in self.views:
                    view = v(id=f"view-{v.key}")
                    view.display = v.key == self.active
                    yield view
        with Horizontal(id="tour"):
            yield Static("", id="tour-text")
            yield Button("", id="tour-next", classes="tour-btn primary", compact=True, flat=True)
            yield Button(self.t("tour.skip"), id="tour-skip", classes="tour-btn", compact=True, flat=True)
        yield Footer()

    def _bind_keys(self) -> None:
        """Footer labels in the user's language."""
        bindings = [
            # priority: the agent view's tree must not take left and right
            Binding("left", "tab(-1)", self.t("keys.tabs"), key_display="←→", priority=True),
            Binding("right", "tab(1)", "", show=False, priority=True),
            Binding("up", "move(-1)", "", show=False),
            Binding("down", "move(1)", "", show=False),
            Binding("s", "settings", self.t("keys.settings")),
            Binding("ctrl+q", "app.quit", self.t("keys.quit"), priority=True),
        ]
        bindings += [Binding(str(i + 1), f"go('{k}')", "", show=False) for i, k in enumerate(self.keys)]
        self._bindings = BindingsMap(bindings)
        self.refresh_bindings()

    def on_mount(self) -> None:
        self._layout(self.app.size.width)
        self.query_one(TabBar).activate(self.active)
        self._draw_tour()
        self.refresh_data(force=True)
        self._enter(self.active)
        self.set_interval(POLL, self.refresh_data)

    def on_resize(self, event) -> None:
        self._layout(event.size.width)

    def _layout(self, width: int) -> None:
        self.query_one(TabBar).set_narrow(width < NARROW)

    def view(self, key: str) -> View:
        return self.query_one(f"#view-{key}", View)

    # ----- data -----

    def refresh_data(self, force: bool = False) -> None:
        ctx = self.gapp.watcher.poll(self.gapp.user, force=force)
        if ctx is None:
            return
        self.ctx = ctx
        self._render_head(ctx)
        for key in self.keys:
            self.view(key).update_from(ctx)
        self._render_tabs(ctx)

    def _render_head(self, ctx: Context) -> None:
        title = ctx.map["title"] if ctx.map else self.gapp.paths.root.name
        self.query_one("#brand", Static).update(
            f"[$accent]◉[/] [b $accent]ezgoggles[/]  [$text-muted]│[/]  [b]{esc(title)}[/]")
        goal = self.query_one("#goal", Static)
        goal.display = ctx.map is not None
        goal.update(esc(ctx.map["goal"].strip()) if ctx.map else "")
        parts = [f"[b]{ctx.user.name}[/]", ctx.t(f"mode.{ctx.user.mode}")]
        if ctx.branch:
            parts.append(esc(ctx.branch))
        if ctx.changed:
            parts.append(ctx.t("status.changed", n=str(ctx.changed)))
        self.query_one("#status", Static).update("  [$text-muted]·[/]  ".join(parts))
        notice = self.query_one("#notice", Static)
        notice.display = ctx.translation in ("missing", "stale", "invalid")
        if notice.display:
            notice.update(ctx.t(f"translation.{ctx.translation}"))

    # ----- tab status -----

    def _mark_seen(self, key: str) -> None:
        """The user looks at a view when they open it and when they leave it."""
        if self.ctx is None:
            return
        token = self.view(key).token(self.ctx)
        if token is not None and self.seen.get(key) != token:
            self.seen[key] = token
            write_json(self.gapp.paths.seen, self.seen)

    def _render_tabs(self, ctx: Context) -> None:
        bar = self.query_one(TabBar)
        dirty = False
        act = set()
        for key in self.keys:
            view = self.view(key)
            token = view.token(ctx)
            if token is not None and key not in self.seen:
                self.seen[key] = token  # the first time, nothing is new
                dirty = True
            status = view.status(ctx, self.seen.get(key) if token is not None else None)
            bar.tab(key).set_status(status)
            if status is not None and status.level == "act":
                act.add(key)
        if dirty:
            write_json(self.gapp.paths.seen, self.seen)
        if "flow" in act - self._act_before:
            sound.cue(self.gapp, "handoff")
        self._act_before = act

    # ----- switching -----

    def action_tab(self, delta: int) -> None:
        i = (self.keys.index(self.active) + delta) % len(self.keys)
        self.switch(self.keys[i])

    def action_go(self, key: str) -> None:
        self.switch(key)

    def on_tab_picked(self, event) -> None:
        self.switch(event.key)

    def switch(self, key: str) -> None:
        if key == self.active or key not in self.keys:
            return
        old = self.active
        self._mark_seen(old)
        direction = 1 if self.keys.index(key) > self.keys.index(old) else -1
        self.view(old).display = False
        new = self.view(key)
        new.display = True
        self.active = key
        self.query_one(TabBar).activate(key)
        self.query_one("#page", VerticalScroll).scroll_home(animate=False)
        if motion_on(self):
            new.styles.offset = (SLIDE * direction, 0)
            new.styles.opacity = 0.4
            new.styles.animate("offset", ScalarOffset.from_offset((0, 0)), duration=SLIDE_TIME, easing="out_cubic")
            new.styles.animate("opacity", 1.0, duration=SLIDE_TIME, easing="out_cubic")
        self._enter(key)
        if self.ctx is not None:
            self._render_tabs(self.ctx)

    def _enter(self, key: str) -> None:
        self._mark_seen(key)
        first = self.in_tour and key == self.tour[self.gapp.user.step - 1] and key not in self.entered_once
        self.entered_once.add(key)
        view = self.view(key)
        if self.ctx is not None:
            view.entered(self.ctx, first)
        trees = view.query(Tree)
        if trees:
            trees.first().focus()
        else:
            self.set_focus(None)

    def action_move(self, delta: int) -> None:
        if not self.view(self.active).move(delta):
            page = self.query_one("#page", VerticalScroll)
            page.scroll_relative(y=delta * 2, animate=False)

    # ----- tour -----

    @property
    def tour(self) -> list[str]:
        return [v.key for v in self.views if v.tour]

    @property
    def in_tour(self) -> bool:
        return 1 <= self.gapp.user.step <= len(self.tour)

    def _draw_tour(self) -> None:
        bar = self.query_one("#tour")
        bar.display = self.in_tour
        if not self.in_tour:
            return
        step, total = self.gapp.user.step, len(self.tour)
        key = self.tour[step - 1]
        self.query_one("#tour-text", Static).update(
            f"[$accent]{self.t('tour.step', n=str(step), total=str(total))}[/]  {self.t(f'tour.{key}')}")
        last = step == total
        self.query_one("#tour-next", Button).label = self.t("tour.start" if last else "tour.next")
        self.query_one("#tour-skip").display = not last

    def on_button_pressed(self, event: Button.Pressed) -> None:
        user = self.gapp.user
        if event.button.id == "tour-next":
            if user.step < len(self.tour):
                user.step += 1
                nxt = self.tour[user.step - 1]
            else:
                user.step = len(self.tour) + 1
                nxt = HOME
                sound.cue(self.gapp, "tour_done")
        elif event.button.id == "tour-skip":
            user.step = SKIPPED
            nxt = HOME
        else:
            return
        save_user(self.gapp.paths, user)
        self._draw_tour()
        self.switch(nxt if nxt in self.keys else self.keys[0])

    def action_settings(self) -> None:
        self.gapp.open_setup(first=False)


class GogglesApp(App):
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen { background: $background; }

    #chrome { height: auto; background: $panel; }
    #topbar { height: 1; padding: 0 2; }
    #brand { width: auto; }
    #status { width: 1fr; text-align: right; color: $text; margin-left: 4; }
    #goal { padding: 0 2; color: $text-muted; height: auto; }
    #tabs { margin-top: 1; }
    #notice { padding: 0 2; margin: 1 2 0 2; border-left: thick $warning; background: $warning 10%; }

    #page { height: 1fr; align-horizontal: center; scrollbar-size-vertical: 1; }
    #views { width: 100%; max-width: 96; height: auto; padding: 1 2; }

    #tour { height: auto; background: $panel; padding: 0 2; }
    #tour-text { width: 1fr; padding: 0 1 0 0; }
    .tour-btn {
        width: auto; min-width: 0; height: 1; margin: 0 0 0 2; padding: 0 2;
        border: none; color: $text-muted; background: transparent;
    }
    .tour-btn.primary { color: $success; background: $success 15%; text-style: bold; }
    .tour-btn:hover, .tour-btn:focus { background: $boost; }
    .tour-btn.primary:hover, .tour-btn.primary:focus { background: $success 30%; }
    """

    def __init__(self, paths: Paths) -> None:
        super().__init__()
        self.paths = paths
        self.user = load_user(paths)
        self.watcher = Watcher(paths)
        self.title = f"ezgoggles - {paths.root.name}"
        self._apply_motion()

    def _apply_motion(self) -> None:
        self.animation_level = "full" if self.user.motion else "none"

    def on_mount(self) -> None:
        for theme in THEMES:
            self.register_theme(theme)
        self.theme = THEME[self.user.theme]
        if self.user.ready:
            self.push_screen(MainScreen())
        else:
            self.open_setup(first=True)

    def open_setup(self, first: bool) -> None:
        def done(result: User | None) -> None:
            if result is None:
                return
            self.user = result
            save_user(self.paths, result)
            self.theme = THEME[result.theme]
            self._apply_motion()
            self.call_later(self._show_main)

        self.push_screen(SetupScreen(self.user, first), done)

    async def _show_main(self) -> None:
        """A new MainScreen: the language, the mode and so the tabs may have changed."""
        if isinstance(self.screen, MainScreen):
            await self.switch_screen(MainScreen())
        else:
            await self.push_screen(MainScreen())


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
