import subprocess

from conftest import write_activity

from ezgoggles.tui import render
from ezgoggles.tui.app import GogglesApp, MainScreen, SetupScreen
from ezgoggles.user import User, load_user, save_user
from conftest import MAP


def test_topo_order_and_chain():
    shuffled = dict(MAP, stages=[MAP["stages"][2], MAP["stages"][0], MAP["stages"][1]])
    assert [s["id"] for s in render.topo_order(shuffled["stages"])] == ["clean", "model", "report"]
    md = render.map_md("zh", shuffled, "model")
    assert "`clean` → `model` → `report`" in md
    assert "model · 需求预测  ← 你" in md


def test_stage_md_modes():
    learn = render.stage_md("zh", MAP, "clean", "alice/clean", "alice", "learn")
    deliver = render.stage_md("zh", MAP, "clean", "alice/clean", "alice", "deliver")
    assert "补齐缺失的时段" in learn and "补齐缺失的时段" not in deliver
    assert "（第一段）" in learn
    none = render.stage_md("en", MAP, None, "main", "alice", "learn")
    assert "`main`" in none and "`clean`" in none


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
        assert s.query_one("#p1").display and not s.query_one("#p2").display
        assert not s.query_one("#right").display
        for i in (1, 2, 3):
            s.query_one(f"#ack{i}").press()
            await pilot.pause()
        assert all(s.query_one(f"#p{i}").display for i in range(1, 5))
        assert s.query_one("#right").display
        assert load_user(project).step == 4


async def test_activity_tree_and_live_reload(project):
    save_user(project, User(name="alice", mode="learn", step=4))
    subprocess.run(["git", "checkout", "-b", "alice/clean"], cwd=project.root, check=True, capture_output=True)
    app = GogglesApp(project)
    async with app.run_test(size=(80, 40)) as pilot:
        s = app.screen
        assert s.query_one("#body").has_class("narrow")
        assert s.query_one("#activity-msg").display
        write_activity(project)
        s.refresh_data()
        s.refresh_data()
        await pilot.pause()
        tree = s.query_one("#activity")
        stage = tree.root.children[0]
        assert "clean" in str(stage.label) and "← 你" in str(stage.label)
        plan = stage.children[0]
        assert "[1/2]" in str(plan.label)
        assert "你来做" in str(plan.children[1].label)


async def test_language_switch(project):
    save_user(project, User(name="bob", mode="deliver", language="en"))
    app = GogglesApp(project)
    async with app.run_test(size=(140, 45)) as pilot:
        s = app.screen
        assert s.query_one("#p1").title == "1 · Requirements"
        await pilot.press("s")
        await pilot.pause()
        setup = app.screen
        setup.query_one("#language").query("RadioButton").first().value = True
        await pilot.pause()
        await pilot.click("#save")
        await pilot.pause()
        await pilot.pause()
        assert app.screen.query_one("#p1").title == "1 · 任务要求"
