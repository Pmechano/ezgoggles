import subprocess

from ezgoggles import opener
from ezgoggles.cli import cmd_init, cmd_open
from ezgoggles.paths import Paths
from ezgoggles.project import stage_from_branch
from ezgoggles.user import User, save_user


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
    monkeypatch.setattr(opener, "launch_commands", lambda p: [])
    cmd_open(project)
    out = capsys.readouterr().out
    assert "could not open a window" in out
    assert "map: OK (3 stages, in map order: clean, model, report)" in out
    assert "setup is not finished" in out

    save_user(project, User(name="alice", mode="learn"))
    subprocess.run(["git", "checkout", "-b", "alice/clean"], cwd=project.root, check=True, capture_output=True)
    monkeypatch.setattr(opener, "launch_commands", lambda p: [(["true"], {})])
    monkeypatch.setattr(opener, "_spawn", lambda a, k: True)
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
    assert not opener.tui_running(project)
    opener.claim_pid(project)
    assert opener.tui_running(project)
    opener.release_pid(project)
    assert not project.pid.exists()


def test_wsl_launch_targets_windows(project, monkeypatch):
    monkeypatch.setattr(opener.os, "name", "posix")
    monkeypatch.setattr(opener.sys, "platform", "linux")
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    monkeypatch.setattr(opener.shutil, "which", lambda n: f"/win/{n}" if n in ("wt.exe", "cmd.exe") else None)
    cmds = opener.launch_commands(project)
    argv = cmds[0][0]
    assert argv[0] == "/win/wt.exe"
    i = argv.index("wsl.exe")
    assert argv[i : i + 5] == ["wsl.exe", "-d", "Ubuntu", "--cd", str(project.root)]
    assert cmds[1][0][:3] == ["cmd.exe", "/c", "start"]


def test_plain_linux_without_gnome_is_manual(project, monkeypatch):
    monkeypatch.setattr(opener.os, "name", "posix")
    monkeypatch.setattr(opener.sys, "platform", "linux")
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(opener, "is_wsl", lambda: False)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(opener.shutil, "which", lambda n: None)
    assert opener.launch_commands(project) == []
