import json
import subprocess
import wave
from datetime import date

from conftest import MAP, MAP_EN, write_activity, write_code

from ezgoggles import i18n
from ezgoggles.context import load_context
from ezgoggles.model import fingerprint, used_for
from ezgoggles.paths import read_json
from ezgoggles.progress import Progress, stage_progress
from ezgoggles.tui import sound
from ezgoggles.tui.app import GogglesApp, MainScreen
from ezgoggles.tui.setup import SetupScreen
from ezgoggles.tui.views import VIEWS, View
from ezgoggles.tui.views.agent import AgentView
from ezgoggles.tui.views.flow import FlowView, goes_into, row_markup
from ezgoggles.tui.views.task import TaskView, deliverables, made_by
from ezgoggles.user import User, load_user, save_user

ALICE = User(name="alice", mode="learn", step=99)


def _git(project, *args):
    subprocess.run(["git", *args], cwd=project.root, check=True, capture_output=True)


def _commit(project, path, msg):
    f = project.root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(msg, encoding="utf-8")
    _git(project, "add", path)
    _git(project, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", msg)


# ---------- task layer <-> solution layer ----------


def test_used_for_follows_the_flow():
    clean = [(d["text"], via) for d, via in used_for(MAP, "clean")]
    assert clean == [("PDF 报告", "model"), ("预测代码", None), ("答辩", "model")]
    assert [(d["text"], via) for d, via in used_for(MAP, "report")] == [("PDF 报告", None), ("答辩", None)]


def test_task_view(project):
    ctx = load_context(project, ALICE, "alice/report")
    rows = [(d["text"], mine) for d, mine in deliverables(ctx)]
    assert rows == [("PDF 报告", True), ("预测代码", False), ("答辩", True)]  # by deadline
    assert made_by(ctx, MAP["requirements"]["deliver"][1]) == "数据清洗 · 需求预测"  # data-flow order
    st = TaskView.status(ctx, TaskView.token(ctx), today=date(2026, 12, 18))
    assert (st.text, st.level) == ("还有 2 天", "quiet")
    assert TaskView.status(ctx, "older requirements").level == "act"


def test_flow_card(project):
    shuffled = dict(MAP, stages=[MAP["stages"][2], MAP["stages"][0], MAP["stages"][1]])
    project.map.write_text(json.dumps(shuffled, ensure_ascii=False), encoding="utf-8")
    ctx = load_context(project, ALICE, "alice/clean")
    assert goes_into(ctx, "clean") == "PDF 报告[$text-muted]（经 需求预测）[/] · 预测代码 · 答辩[$text-muted]（经 需求预测）[/]"
    s = ctx.stage_by_id["clean"]
    line = row_markup(ctx, s, selected=False)
    assert "数据清洗" in line and "← 你" in line and "\n" not in line  # one line when not selected
    card = row_markup(ctx, s, selected=True)
    assert "用于" in card and "代码在 src/clean/" in card
    deliver = load_context(project, User(name="alice", mode="deliver"), "alice/clean")
    assert "src/" not in row_markup(deliver, s, selected=True)  # paths are for learning mode


def test_flow_status_handoff_and_upstream(project):
    ctx = load_context(project, ALICE, "alice/model", progress={"clean": Progress("a1")})
    seen = FlowView.token(ctx)
    assert FlowView.status(ctx, seen) is None
    write_activity(project, {"model": [{
        "time": "2026-11-08T11:00", "title": "换模型", "items": [{"text": "试 GBDT", "done": True}],
        "handoffChange": "预测值多了一列置信区间"}]})
    changed = load_context(project, ALICE, "alice/model", progress={"clean": Progress("a1")})
    st = FlowView.status(changed, seen)
    assert (st.text, st.level) == ("交接变了", "act")
    assert "预测值多了一列置信区间" in row_markup(changed, changed.stage_by_id["model"], selected=True)
    project.activity.unlink()
    up = load_context(project, ALICE, "alice/model", progress={"clean": Progress("b2")})
    assert FlowView.status(up, seen).text == "上游有更新"


def test_progress_comes_from_git(project):
    _commit(project, "src/clean/fill.py", "clean")
    _git(project, "checkout", "-q", "-b", "bob/model")
    _commit(project, "src/model/train.py", "model")
    _git(project, "checkout", "-q", "main")
    p = stage_progress(project, MAP["stages"])
    assert {k: v.state for k, v in p.items()} == {"clean": "merged", "model": "working", "report": "none"}


# ---------- views ----------


def test_code_view_is_for_learning_only():
    learn = [v.key for v in VIEWS if v.shown_for(User(mode="learn"))]
    deliver = [v.key for v in VIEWS if v.shown_for(User(mode="deliver"))]
    assert learn == ["task", "flow", "code", "agent"]
    assert deliver == ["task", "flow", "agent"]


def test_agent_status(project):
    ctx = load_context(project, ALICE, "alice/clean")
    assert AgentView.status(ctx, None).text == "空闲"
    write_activity(project)
    ctx = load_context(project, ALICE, "alice/clean")
    st = AgentView.status(ctx, None)
    assert (st.text, st.level) == ("等你来做", "act")


def test_translation_is_used_when_fresh(project):
    user = User(name="a", mode="learn", language="en")
    assert load_context(project, user).translation == "missing"
    project.translations.mkdir()
    fresh = dict(MAP_EN, source=fingerprint(MAP))
    project.translation("en").write_text(json.dumps(fresh), encoding="utf-8")
    ctx = load_context(project, user)
    assert ctx.translation == "ok" and ctx.map["title"] == "Bike demand forecast"
    project.translation("en").write_text(json.dumps(dict(fresh, source="old")), encoding="utf-8")
    ctx = load_context(project, user)
    assert ctx.translation == "stale" and ctx.map["title"] == "共享单车需求预测"
    moved = json.loads(json.dumps(fresh))
    moved["requirements"]["deliver"][0]["from"] = ["model"]
    project.translation("en").write_text(json.dumps(moved), encoding="utf-8")
    assert load_context(project, user).translation == "invalid"  # links are not translated
    assert load_context(project, User(name="a", mode="learn")).translation == "native"


def test_locales_are_discovered_and_complete():
    assert i18n.available()[:2] == ("zh", "en")
    en = set(i18n._table("en"))
    assert set(i18n._raw("zh")) - {"meta.name", "meta.order"} == en - {"meta.name", "meta.order"}
    for view in VIEWS:
        assert f"view.{view.key}" in en and f"tour.{view.key}" in en


# ---------- the app ----------


async def test_first_start_setup_then_tour(project):
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        assert isinstance(app.screen, SetupScreen)
        await pilot.click("#name")
        await pilot.press(*"Alice")
        await pilot.click("#save")
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)  # mode not chosen yet
        app.screen.query_one("#mode").query("RadioButton").first().value = True
        await pilot.pause(0.3)  # a button ignores clicks during its press animation
        await pilot.click("#save")
        await pilot.pause()
        s = app.screen
        assert isinstance(s, MainScreen)
        u = load_user(project)
        assert (u.name, u.mode, u.step, u.motion, u.sound) == ("alice", "learn", 1, True, False)
        assert s.active == "task" and s.query_one("#tour").display
        for expected in ("flow", "code", "agent"):
            s.query_one("#tour-next").press()
            await pilot.pause(0.2)
            assert s.active == expected
        s.query_one("#tour-next").press()
        await pilot.pause(0.2)
        assert s.active == "flow" and not s.query_one("#tour").display
        assert load_user(project).step == 5
        assert "task" in read_json(project.seen)


async def test_tabs_keys_and_status(project):
    save_user(project, ALICE)
    _git(project, "checkout", "-q", "-b", "alice/clean")
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        s = app.screen
        assert s.active == "flow"
        assert s.query_one("#view-flow").display and not s.query_one("#view-task").display
        await pilot.press("left")
        assert s.active == "task"
        await pilot.press("4")
        assert s.active == "agent"
        await pilot.press("right")  # the tree has focus, but left and right still switch tabs
        assert s.active == "task"
        write_activity(project)
        s.refresh_data(force=True)
        await pilot.pause()
        tab = s.query_one("#tab-agent")
        assert "等你来做" in str(tab.render())
        await pilot.click("#tab-agent")
        tree = s.query_one("#view-agent").query_one("Tree")
        stage = tree.root.children[0]
        assert "数据清洗" in str(stage.label) and "← 你" in str(stage.label)
        assert "[1/2]" in str(stage.children[0].label)


async def test_flow_selection_with_keys_and_mouse(project):
    save_user(project, ALICE)
    _git(project, "checkout", "-q", "-b", "alice/model")
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        flow = app.screen.query_one(FlowView)
        assert flow.selected == "model"  # the user's stage first
        await pilot.press("down")
        assert flow.selected == "report"
        await pilot.press("down")
        assert flow.selected == "report"  # stops at the end
        await pilot.click(".stage")
        assert flow.selected == "clean"


async def test_narrow_tabs_show_symbols(project):
    save_user(project, ALICE)
    write_activity(project)
    _git(project, "checkout", "-q", "-b", "alice/clean")
    app = GogglesApp(project)
    async with app.run_test(size=(60, 30)) as pilot:
        await pilot.pause()
        text = str(app.screen.query_one("#tab-agent").render())
        assert "!" in text and "等你来做" not in text


async def test_language_switch(project):
    save_user(project, User(name="bob", mode="deliver", language="en", step=99))
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        assert "Task" in str(app.screen.query_one("#tab-task").render())
        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#language").query("RadioButton").first().value = True
        await pilot.pause(0.3)  # let the setup page recompose in the new language
        await pilot.click("#save")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)
        assert "任务" in str(app.screen.query_one("#tab-task").render())
        assert len(app.screen_stack) == 2  # the old main screen was replaced, not stacked


async def test_motion_off(project):
    save_user(project, User(name="bob", mode="deliver", step=99, motion=False))
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.animation_level == "none"
        await pilot.press("left")
        task = app.screen.query_one("#view-task")
        assert task.styles.offset.x.value == 0 and task.styles.opacity == 1.0  # no slide, no fade


async def test_missing_map_message(project):
    project.map.unlink()
    save_user(project, User(name="bob", mode="deliver", step=99))
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert "leader-guide.md" in str(app.screen.query_one("#flow-msg").render())


async def test_code_view(project):
    save_user(project, ALICE)
    write_code(project)
    _git(project, "checkout", "-q", "-b", "alice/model")
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("3")
        await pilot.pause()
        code = app.screen.query_one("#view-code")
        text = " ".join(str(w.render()) for w in code.query("Static"))
        assert text.index("汇总表") < text.index("src/model/features.py") < text.index("train.py::fit") < text.index("预测值")


async def test_a_new_view_needs_only_registration(project, monkeypatch):
    from ezgoggles.tui import app as app_module
    from textual.widgets import Static

    class NotesView(View):
        key = "notes"

        def compose(self):
            yield Static("", id="notes")

        def update_from(self, ctx):
            self.query_one("#notes", Static).update(f"{len(ctx.stages)} stages")

    monkeypatch.setattr(app_module, "VIEWS", [*VIEWS, NotesView])
    save_user(project, User(name="bob", mode="deliver", step=99))
    app = GogglesApp(project)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("4")
        await pilot.pause()
        assert app.screen.active == "notes"
        assert str(app.screen.query_one("#notes").render()) == "3 stages"


# ---------- sound ----------


def test_sound_is_off_by_default_and_pluggable(monkeypatch):
    played = []

    class Fake(sound.Player):
        def available(self):
            return True

        def play(self, wav):
            played.append(wav)

    class App:
        user = User()
        bell = staticmethod(lambda: played.append("bell"))

    monkeypatch.setattr(sound, "PLAYERS", [Fake()])
    sound.player.cache_clear()
    try:
        sound.cue(App, "handoff")
        assert played == []
        App.user = User(sound=True)
        sound.cue(App, "handoff")
        with wave.open(str(played[0])) as w:
            assert w.getframerate() == sound.RATE and w.getnframes() > 0
    finally:
        sound.player.cache_clear()


def test_locale_with_base_overrides_some_keys(tmp_path, monkeypatch):
    for f in i18n.LOCALE_DIR.glob("*.toml"):
        (tmp_path / f.name).write_bytes(f.read_bytes())
    (tmp_path / "zh-scp.toml").write_text(
        '[meta]\nname = "SCP"\norder = 3\nbase = "zh"\n\n[view]\ntask = "收容协议"\n', encoding="utf-8"
    )
    monkeypatch.setattr(i18n, "LOCALE_DIR", tmp_path)
    for fn in (i18n._raw, i18n._table, i18n.available):
        fn.cache_clear()
    try:
        assert i18n.available() == ("zh", "en", "zh-scp")
        assert i18n.tr("zh-scp", "view.task") == "收容协议"
        assert i18n.tr("zh-scp", "view.flow") == "流程"
    finally:
        monkeypatch.undo()
        for fn in (i18n._raw, i18n._table, i18n.available):
            fn.cache_clear()
