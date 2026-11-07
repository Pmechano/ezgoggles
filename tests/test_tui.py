import json
import subprocess

from conftest import MAP, MAP_EN, write_activity

from ezgoggles import i18n
from ezgoggles.context import load_context
from ezgoggles.model import fingerprint
from ezgoggles.tui.panels.requirements import RequirementsPanel
from ezgoggles.tui.app import GogglesApp, MainScreen
from ezgoggles.tui.panels import PANELS
from ezgoggles.tui.panels.project_map import MapPanel, flow_markup
from ezgoggles.tui.panels.stage import StagePanel
from ezgoggles.tui.setup import SetupScreen
from ezgoggles.user import User, load_user, save_user


def _branch(project, name):
    subprocess.run(["git", "checkout", "-b", name], cwd=project.root, check=True, capture_output=True)


def test_map_markdown_whole_first(project):
    shuffled = dict(MAP, stages=[MAP["stages"][2], MAP["stages"][0], MAP["stages"][1]])
    project.map.write_text(json.dumps(shuffled, ensure_ascii=False), encoding="utf-8")
    ctx = load_context(project, User(name="alice", mode="learn"), "alice/model")
    flow = flow_markup(ctx)
    assert flow.index("数据清洗") < flow.index("需求预测") < flow.index("报告")
    assert "[b reverse $accent] 需求预测 [/]" in flow  # the user's stage stands out
    md = MapPanel.markdown(ctx)
    assert md.splitlines()[0] == "- **数据清洗**：去掉异常记录，补齐缺失时段"
    assert "- **需求预测**  ← 你：训练模型，预测下周需求" in md
    assert "src/" not in md  # paths are for agents


def test_stage_markdown(project):
    ctx = load_context(project, User(name="alice", mode="learn"), "alice/model")
    md = StagePanel.markdown(ctx)
    assert md.splitlines()[0] == "你负责 **需求预测**：训练模型，预测下周需求"
    assert "从 **数据清洗** 拿到：汇总表" in md
    assert "交给 **报告**：预测值" in md
    learn = load_context(project, User(name="alice", mode="learn"), "alice/clean")
    deliver = load_context(project, User(name="alice", mode="deliver"), "alice/clean")
    assert "前后均值" in StagePanel.detail(learn)
    assert StagePanel.detail(deliver) == ""
    none = StagePanel.markdown(load_context(project, User(name="alice", mode="learn", language="en"), "main"))
    assert "数据清洗, 需求预测, 报告" in none


def test_requirements_markdown_order(project):
    md = RequirementsPanel.markdown(load_context(project, User(name="a", mode="learn")))
    heads = [line for line in md.splitlines() if line.startswith("**")]
    assert heads == ["**交什么**", "**截止**", "**怎么评分**"]


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
    assert load_context(project, User(name="a", mode="learn")).translation == "native"


def test_locales_are_discovered_and_complete():
    assert i18n.available()[:2] == ("zh", "en")
    en = set(i18n._table("en"))
    assert set(i18n._raw("zh")) - {"meta.name", "meta.order"} == en - {"meta.name", "meta.order"}
    for panel in PANELS:
        assert f"panel.{panel.key}" in en


async def test_first_start_shows_setup_then_steps(project):
    app = GogglesApp(project)
    async with app.run_test(size=(140, 45)) as pilot:
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
        assert isinstance(app.screen, MainScreen)
        u = load_user(project)
        assert (u.name, u.mode, u.step) == ("alice", "learn", 1)

        s = app.screen
        assert s.query_one("#sec-0").display and not s.query_one("#sec-1").display
        assert s.query_one("#nameplate").display  # wide screen: the side column holds the nameplate
        assert not s.query_one(f"#sec-{len(PANELS) - 1}").display
        for i in range(len(PANELS) - 1):
            s.query_one(f"#ack-{i}").press()
            await pilot.pause()
        assert all(s.query_one(f"#sec-{i}").display for i in range(len(PANELS)))
        assert s.query_one("#side").display
        assert not any(s.query_one(f"#ack-{i}").display for i in range(len(PANELS)))
        assert load_user(project).step == len(PANELS)


async def test_activity_tree_and_live_reload(project):
    save_user(project, User(name="alice", mode="learn", step=4))
    _branch(project, "alice/clean")
    app = GogglesApp(project)
    async with app.run_test(size=(80, 40)) as pilot:
        s = app.screen
        assert s.query_one("#body").has_class("narrow")
        assert not s.query_one("#nameplate").display
        assert s.query_one("#activity-msg").display
        write_activity(project)
        s.refresh_data()
        await pilot.pause()
        tree = s.query_one("#activity")
        stage = tree.root.children[0]
        assert "数据清洗" in str(stage.label) and "← 你" in str(stage.label)
        plan = stage.children[0]
        assert "[1/2]" in str(plan.label)
        assert "你来做" in str(plan.children[1].label)


async def test_language_switch(project):
    save_user(project, User(name="bob", mode="deliver", language="en"))
    app = GogglesApp(project)
    async with app.run_test(size=(140, 45)) as pilot:
        assert app.screen.query_one("#sec-0").title == "1  Requirements"
        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#language").query("RadioButton").first().value = True
        await pilot.pause(0.3)  # let the setup page recompose in the new language
        await pilot.click("#save")
        await pilot.pause()
        await pilot.pause()
        assert app.screen.query_one("#sec-0").title == "1  任务要求"


async def test_missing_map_message(project):
    project.map.unlink()
    save_user(project, User(name="bob", mode="deliver", step=2))
    app = GogglesApp(project)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        md = app.screen.query_one("#panel-map").query_one("Markdown")
        assert "leader-guide.md" in md.source


async def test_a_new_panel_needs_only_registration(project, monkeypatch):
    from ezgoggles.tui import app as app_module
    from ezgoggles.tui.panels import MarkdownPanel

    class NotesPanel(MarkdownPanel):
        key = "notes"

        @staticmethod
        def markdown(ctx):
            return f"{len(ctx.stages)} stages"

    monkeypatch.setattr(app_module, "PANELS", [*PANELS, NotesPanel])
    save_user(project, User(name="bob", mode="deliver", step=len(PANELS) + 1))
    app = GogglesApp(project)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause()
        s = app.screen
        assert s.query_one(f"#sec-{len(PANELS)}").display
        assert s.query_one("#panel-notes").query_one("Markdown").source == "3 stages"


def test_locale_with_base_overrides_some_keys(tmp_path, monkeypatch):
    for f in i18n.LOCALE_DIR.glob("*.toml"):
        (tmp_path / f.name).write_bytes(f.read_bytes())
    (tmp_path / "zh-scp.toml").write_text(
        '[meta]\nname = "SCP"\norder = 3\nbase = "zh"\n\n[panel]\nack = "已刻印模因"\n', encoding="utf-8"
    )
    monkeypatch.setattr(i18n, "LOCALE_DIR", tmp_path)
    for fn in (i18n._raw, i18n._table, i18n.available):
        fn.cache_clear()
    try:
        assert i18n.available() == ("zh", "en", "zh-scp")
        assert i18n.tr("zh-scp", "panel.ack") == "已刻印模因"
        assert i18n.tr("zh-scp", "panel.map") == "项目地图"
    finally:
        monkeypatch.undo()
        for fn in (i18n._raw, i18n._table, i18n.available):
            fn.cache_clear()
