"""The ezgoggles TUI. It reads files and shows them. It never edits project content."""

from __future__ import annotations

import os
from dataclasses import replace

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Input,
    Label,
    Markdown,
    RadioButton,
    RadioSet,
    Static,
    Tree,
)

from ..check import check_activity, check_map
from ..opener import claim_pid, pid_alive, release_pid
from ..paths import Paths, read_json
from ..project import changed_files, current_branch, stage_from_branch
from ..user import LANGUAGES, LAST_STEP, MODES, NAME_RE, THEMES, User, load_user, save_user
from . import render
from .i18n import tr

THEME = {"dark": "textual-dark", "light": "textual-light"}
NARROW = 110  # columns; below this the panels stack in one column
POLL = 1.0  # seconds


class SetupScreen(Screen[User]):
    """Language, name, mode and theme. Shown on first start and on 's'."""

    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, user: User, first: bool) -> None:
        super().__init__()
        self.draft = replace(user)
        self.first = first

    def t(self, key: str) -> str:
        return tr(self.draft.language, key)

    def compose(self) -> ComposeResult:
        d = self.draft
        with VerticalScroll(id="setup"):
            yield Label(self.t("setup.title"), classes="title")
            yield Label(self.t("setup.language"), classes="field")
            with RadioSet(id="language"):
                yield RadioButton("中文", value=d.language == "zh")
                yield RadioButton("English", value=d.language == "en")
            yield Label(self.t("setup.name"), classes="field")
            yield Input(value=d.name, placeholder="alice", id="name")
            yield Static(self.t("setup.name.hint"), classes="hint")
            yield Label(self.t("setup.mode"), classes="field")
            with RadioSet(id="mode"):
                yield RadioButton(self.t("setup.mode.learn"), value=d.mode == "learn")
                yield RadioButton(self.t("setup.mode.deliver"), value=d.mode == "deliver")
            yield Label(self.t("setup.theme"), classes="field")
            with RadioSet(id="theme"):
                yield RadioButton(self.t("setup.theme.dark"), value=d.theme == "dark")
                yield RadioButton(self.t("setup.theme.light"), value=d.theme == "light")
            yield Static("", id="error")
            yield Button(self.t("setup.save"), variant="primary", id="save")

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        group = event.radio_set.id
        if group == "language":
            lang = LANGUAGES[event.index]
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
            error.update(self.t("setup.name.bad"))
            return
        if self.draft.mode not in MODES:
            error.update(self.t("setup.mode.bad"))
            return
        self.dismiss(self.draft)

    def action_cancel(self) -> None:
        if not self.first:
            self.app.theme = THEME[self.app.user.theme]  # type: ignore[attr-defined]
            self.dismiss(None)


class MainScreen(Screen):
    BINDINGS = [
        Binding("s", "settings", "Settings / 设置"),
        Binding("ctrl+q", "app.quit", "Quit / 退出"),
    ]

    PANELS = ("requirements", "map", "stage", "activity")

    def __init__(self) -> None:
        super().__init__()
        self._sig: tuple | None = None
        self._tick = 0
        self._branch: str | None = None
        self._changed: int | None = None

    @property
    def gapp(self) -> "GogglesApp":
        return self.app  # type: ignore[return-value]

    def t(self, key: str, **kw: str) -> str:
        return tr(self.gapp.user.language, key, **kw)

    def compose(self) -> ComposeResult:
        yield Static("", id="status")
        with Horizontal(id="body"):
            with VerticalScroll(id="left", classes="col"):
                for i, key in enumerate(self.PANELS[:3], start=1):
                    with Collapsible(title=self.t(f"panel.{key}"), collapsed=False, id=f"p{i}"):
                        yield Markdown("", id=f"md{i}")
                        yield Button(self.t("ack"), id=f"ack{i}", classes="ack")
            with VerticalScroll(id="right", classes="col"):
                with Collapsible(title=self.t("panel.activity"), collapsed=False, id="p4"):
                    yield Static("", id="activity-msg")
                    tree: Tree[None] = Tree("activity", id="activity")
                    tree.show_root = False
                    yield tree
        yield Footer()

    def on_mount(self) -> None:
        self._layout(self.app.size.width)
        self.refresh_data(force=True)
        self.set_interval(POLL, self.refresh_data)

    def on_resize(self, event) -> None:
        self._layout(event.size.width)

    def _layout(self, width: int) -> None:
        self.query_one("#body").set_class(width < NARROW, "narrow")

    # ----- data -----

    def _signature(self) -> tuple:
        p = self.gapp.paths
        def mtime(f):
            try:
                return f.stat().st_mtime_ns
            except OSError:
                return None
        # git is slower than stat, so ask it every other tick.
        if self._tick % 2 == 0:
            self._branch = current_branch(p)
            self._changed = changed_files(p)
        self._tick += 1
        return (mtime(p.map), mtime(p.activity), self._branch, self._changed)

    def refresh_data(self, force: bool = False) -> None:
        sig = self._signature()
        if not force and sig == self._sig:
            return
        self._sig = sig
        self.render_all()

    def render_all(self) -> None:
        user = self.gapp.user
        lang = user.language
        p = self.gapp.paths

        mr = check_map(p)
        m = mr.data if isinstance(mr.data, dict) else None
        ids = {s["id"] for s in m["stages"]} if m else set()
        mine = stage_from_branch(self._branch, user.name, ids)

        status = [user.name, self.t(f"mode.{user.mode}")]
        if self._branch:
            status.append(f"{self.t('status.branch')}: {self._branch}")
        if self._changed is not None:
            status.append(f"{self.t('status.changed')}: {self._changed}")
        self.query_one("#status", Static).update("  ·  ".join(status))

        if m is None:
            msg = self.t("map.missing") if not p.map.exists() else self.t("map.invalid")
            texts = [msg, msg, msg]
        else:
            texts = [
                render.requirements_md(lang, m),
                render.map_md(lang, m, mine),
                render.stage_md(lang, m, mine, self._branch, user.name, user.mode),
            ]
        for i, text in enumerate(texts, start=1):
            self.query_one(f"#md{i}", Markdown).update(text)

        self._render_activity(p, m, ids, mine, lang)
        self._apply_step()

    def _render_activity(self, p: Paths, m: dict | None, ids: set[str], mine: str | None, lang: str) -> None:
        ar = check_activity(p, ids if m else None)
        msg = self.query_one("#activity-msg", Static)
        tree = self.query_one("#activity", Tree)
        tree.clear()
        if not ar.ok:
            msg.update(self.t("activity.invalid"))
            msg.display = True
            return
        activity: dict = ar.data or {}
        if not any(activity.values()):
            msg.update(self.t("activity.empty"))
            msg.display = True
            return
        msg.display = False
        stages = m["stages"] if m else []
        for sid in render.stage_order_for_activity(activity, stages, mine):
            plans = activity[sid]
            snode = tree.root.add(render.stage_label(sid, stages, mine, lang), expand=(sid == mine or mine is None))
            for j, plan in enumerate(reversed(plans)):
                pnode = snode.add(render.plan_label(plan), expand=(j == 0))
                for it in plan["items"]:
                    pnode.add_leaf(render.item_label(it, lang))
                for extra in (render.summary_label(plan, lang), render.handoff_label(plan, lang)):
                    if extra is not None:
                        pnode.add_leaf(extra)

    # ----- progressive view -----

    def _apply_step(self) -> None:
        step = self.gapp.user.step
        for i in range(1, LAST_STEP + 1):
            self.query_one(f"#p{i}").display = i <= step
        for i in range(1, LAST_STEP):
            self.query_one(f"#ack{i}").display = i == step
        self.query_one("#right").display = step >= LAST_STEP

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if not bid.startswith("ack"):
            return
        user = self.gapp.user
        if int(bid[3:]) == user.step and user.step < LAST_STEP:
            user.step += 1
            save_user(self.gapp.paths, user)
            self._apply_step()
            nxt = self.query_one(f"#p{user.step}", Collapsible)
            nxt.collapsed = False
            self.call_after_refresh(nxt.scroll_visible)

    # ----- settings -----

    def action_settings(self) -> None:
        self.gapp.open_setup(first=False)


class GogglesApp(App):
    CSS = """
    #status { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    #body { height: 1fr; }
    .col { width: 1fr; height: 100%; padding: 0 1; }
    #body.narrow { layout: vertical; overflow-y: auto; }
    #body.narrow > .col { width: 100%; height: auto; overflow-y: hidden; }
    Collapsible { margin-bottom: 1; }
    Markdown { height: auto; margin: 0; padding: 0 1; }
    .ack { margin: 1 0 0 1; }
    #activity { height: auto; max-height: 100%; }
    #activity-msg { padding: 0 1; color: $text-muted; }
    #setup { width: 100%; max-width: 90; padding: 1 2; }
    #setup .title { text-style: bold; margin-bottom: 1; }
    #setup .field { margin-top: 1; text-style: bold; }
    #setup .hint { color: $text-muted; }
    #setup RadioSet { width: 100%; }
    #setup #error { color: $error; margin: 1 0; }
    SetupScreen { align: center top; }
    """

    def __init__(self, paths: Paths) -> None:
        super().__init__()
        self.paths = paths
        self.user = load_user(paths)
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
    info = read_json(paths.pid)
    if isinstance(info, dict):
        pid = info.get("pid")
        if isinstance(pid, int) and pid != os.getpid() and pid_alive(pid):
            print("ezgoggles: the TUI is already running for this project.")
            return 0
    claim_pid(paths)
    try:
        GogglesApp(paths).run()
    finally:
        release_pid(paths)
    return 0
