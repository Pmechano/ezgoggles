import subprocess

import ezgoggles.launch as launch
from ezgoggles.cli import cmd_init, cmd_open
from ezgoggles.launch import launchers, pidfile
from ezgoggles.paths import Paths
from ezgoggles.project import stage_from_branch
from ezgoggles.user import User, save_user


class FakeLauncher(launchers.Launcher):
    name = "fake"

    def available(self):
        return True

    def command(self, paths):
        return launchers.Command(["true"])


def test_init_is_idempotent(tmp_path, capsys):
    root = tmp_path / "p"
    root.mkdir()
    (root / "README.md").write_text("# Proj\n", encoding="utf-8")
    paths = Paths(root)
    cmd_init(paths)
    first = {f: (root / f).read_text(encoding="utf-8") for f in ("README.md", "AGENTS.md", "CLAUDE.md")}
    assert first["README.md"].startswith("# Proj\n")
    assert "agent-guide.md" in first["AGENTS.md"]
    assert first["CLAUDE.md"] == "@AGENTS.md\n"
    assert (root / "goggles-data/.gitignore").read_text(encoding="utf-8") == ".local/\n"
    cmd_init(paths)
    again = {f: (root / f).read_text(encoding="utf-8") for f in first}
    assert again == first
    assert "nothing to do" in capsys.readouterr().out


def test_stage_from_branch():
    ids = {"clean", "model"}
    assert stage_from_branch("alice/clean", "alice", ids) == "clean"
    assert stage_from_branch("bob/clean", "alice", ids) is None
    assert stage_from_branch("alice/ghost", "alice", ids) is None
    assert stage_from_branch("main", "alice", ids) is None


def test_open_reports_state(project, monkeypatch, capsys):
    monkeypatch.delenv("EZGOGGLES_NO_WINDOW", raising=False)
    monkeypatch.setattr(launch, "available_launchers", lambda: [])
    cmd_open(project)
    out = capsys.readouterr().out
    assert "could not open a window" in out
    assert "map: OK (3 stages, in map order: clean, model, report)" in out
    assert "setup is not finished" in out
    assert not project.pid.exists()

    save_user(project, User(name="alice", mode="learn"))
    subprocess.run(["git", "checkout", "-b", "alice/clean"], cwd=project.root, check=True, capture_output=True)
    monkeypatch.setattr(launch, "available_launchers", lambda: [FakeLauncher()])
    monkeypatch.setattr(launch, "spawn", lambda cmd: True)
    cmd_open(project)
    out = capsys.readouterr().out
    assert "started in a new window" in out
    assert "name=alice mode=learn" in out
    assert "stage: clean" in out
    # The launch marker makes a second open a no-op.
    cmd_open(project)
    assert "already running" in capsys.readouterr().out


def test_no_window_env(project, monkeypatch, capsys):
    monkeypatch.setenv("EZGOGGLES_NO_WINDOW", "1")
    cmd_open(project)
    out = capsys.readouterr().out
    assert "EZGOGGLES_NO_WINDOW" in out and "could not open" not in out
    assert "--root" in out and "&&" not in out
    assert not project.pid.exists()


def test_pid_lifecycle(project):
    assert not pidfile.tui_running(project)
    pidfile.claim(project)
    assert pidfile.tui_running(project)
    assert pidfile.other_tui_pid(project) is None  # it is this process
    pidfile.release(project)
    assert not project.pid.exists()


def _platform(monkeypatch, name, platform, wsl):
    monkeypatch.setattr(launchers.os, "name", name)
    monkeypatch.setattr(launchers.sys, "platform", platform)
    monkeypatch.setattr(launchers, "is_wsl", lambda: wsl)


def test_wsl_launch_targets_windows(project, monkeypatch):
    _platform(monkeypatch, "posix", "linux", True)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.setattr(launchers.shutil, "which", lambda n: f"/win/{n}" if n in ("wt.exe", "cmd.exe") else None)
    found = launchers.available_launchers()
    assert [ln.name for ln in found] == ["wsl-windows-terminal", "wsl-cmd"]
    argv = found[0].command(project).argv
    assert argv[0] == "/win/wt.exe"
    i = argv.index("wsl.exe")
    assert argv[i : i + 5] == ["wsl.exe", "-d", "Ubuntu", "--cd", str(project.root)]
    assert found[1].command(project).argv[:3] == ["cmd.exe", "/c", "start"]


def test_windows_prefers_windows_terminal(monkeypatch):
    _platform(monkeypatch, "nt", "win32", False)
    monkeypatch.setattr(launchers.shutil, "which", lambda n: "C:/wt.exe" if n == "wt" else None)
    assert [ln.name for ln in launchers.available_launchers()] == ["windows-terminal", "windows-console"]


def test_plain_linux_without_gnome_is_manual(monkeypatch):
    _platform(monkeypatch, "posix", "linux", False)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(launchers.shutil, "which", lambda n: None)
    assert launchers.available_launchers() == []


def test_check_includes_code_flow(project, capsys):
    from conftest import write_code

    from ezgoggles.cli import cmd_check

    write_code(project, {"model": {"time": "bad", "steps": []}})
    assert cmd_check(project) == 1
    assert "ERROR goggles-data/.local/code.json" in capsys.readouterr().out
