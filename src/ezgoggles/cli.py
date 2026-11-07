"""Command line entry: ezgoggles open | tui | check | init."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .check import check_map, run_check
from .opener import manual_command, open_tui
from .paths import DATA_DIR, PLUGIN_DIR, Paths, find_root
from .project import current_branch, stage_from_branch
from .user import load_user


def _paths(args: argparse.Namespace) -> Paths:
    root = Path(args.root).resolve() if args.root else find_root()
    return Paths(root)


def _plugin_rel(paths: Paths) -> str:
    try:
        return PLUGIN_DIR.relative_to(paths.root).as_posix()
    except ValueError:
        return PLUGIN_DIR.as_posix()


def cmd_open(paths: Paths) -> int:
    plugin = _plugin_rel(paths)
    result = open_tui(paths)
    if result == "running":
        print("tui: already running.")
    elif result == "started":
        print("tui: started in a new window.")
    elif result == "disabled":
        print("tui: no window, because EZGOGGLES_NO_WINDOW is set. To start it by hand:")
        print(f"  {manual_command(paths)}")
    else:
        print("tui: could not open a window. Ask the user to run this in a terminal:")
        print(f"  {manual_command(paths)}")

    m = check_map(paths)
    ids: set[str] = set()
    if m.data:
        order = [s["id"] for s in m.data["stages"]]
        ids = set(order)
        print(f"map: OK ({len(order)} stages, in map order: {', '.join(order)}).")
    elif not paths.map.exists():
        print(f"map: {DATA_DIR}/map.json does not exist. "
              f"If the user is the leader, read {plugin}/leader-guide.md.")
    else:
        print(f"map: {DATA_DIR}/map.json has errors. Run `ezgoggles check` and fix them.")

    user = load_user(paths)
    if user.ready:
        print(f"user: name={user.name} mode={user.mode} language={user.language}.")
    elif result in ("running", "started"):
        print("user: setup is not finished. Ask the user to finish the setup page "
              "in the TUI window, then run `ezgoggles open` again.")
    else:
        print("user: setup is not finished. The user must start the TUI with the "
              "command above and finish the setup page.")

    branch = current_branch(paths)
    if branch is not None:
        sid = stage_from_branch(branch, user.name, ids) if user.ready else None
        if sid:
            print(f"branch: {branch} (stage: {sid}).")
        else:
            print(f"branch: {branch} (not a stage branch <name>/<stage-id>).")
    return 0


def cmd_init(paths: Paths) -> int:
    """Leader setup: add goggles-data/ and the entry line. Never overwrites."""
    plugin = _plugin_rel(paths)
    guide = f"{plugin}/agent-guide.md"
    entry = (
        f"> **If you are an agent:** before any work, read `{guide}` and follow it. "
        f"If `{plugin}/` is empty, run `git submodule update --init` first.\n"
        f">\n"
        f"> **如果你是 Agent：** 开工前先阅读并遵循 `{guide}`。"
        f"如果 `{plugin}/` 是空的，先运行 `git submodule update --init`。\n"
    )
    done: list[str] = []

    paths.data.mkdir(exist_ok=True)
    gi = paths.data / ".gitignore"
    if not gi.exists():
        gi.write_text(".local/\n", encoding="utf-8")
        done.append(f"created {DATA_DIR}/.gitignore")

    for name in ("README.md", "AGENTS.md"):
        f = paths.root / name
        text = f.read_text(encoding="utf-8") if f.exists() else ""
        if guide in text:
            continue
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        f.write_text(text + sep + entry, encoding="utf-8")
        done.append(f"{'added the entry line to' if text else 'created'} {name}")

    claude = paths.root / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8") if claude.exists() else ""
    if "@AGENTS.md" not in text:
        sep = "" if not text or text.endswith("\n") else "\n"
        claude.write_text(text + sep + "@AGENTS.md\n", encoding="utf-8")
        done.append(f"{'added @AGENTS.md to' if text else 'created'} CLAUDE.md")

    for line in done or ["nothing to do: already set up."]:
        print(line)
    if not paths.map.exists():
        print(f"next: write {DATA_DIR}/map.json as {plugin}/leader-guide.md describes, "
              "then run `ezgoggles check`.")
    return 0


def cmd_tui(paths: Paths) -> int:
    from .tui.app import run

    return run(paths)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="ezgoggles")
    p.add_argument("--root", help="group project root (default: found from the current dir)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open", help="start the TUI in a new window if it is not running")
    sub.add_parser("tui", help="run the TUI in this terminal")
    sub.add_parser("check", help="validate goggles-data/map.json and activity.json")
    sub.add_parser("init", help="leader setup: goggles-data/ and the entry line")
    for sp in sub.choices.values():
        sp.add_argument("--root", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    paths = _paths(args)
    return {
        "open": cmd_open,
        "tui": cmd_tui,
        "check": lambda ps: run_check(ps),
        "init": cmd_init,
    }[args.cmd](paths)


if __name__ == "__main__":
    sys.exit(main())
