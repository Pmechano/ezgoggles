"""Command line entry: ezgoggles open | tui | check | init."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from .bootstrap import setup_project
from .check import Report, check_translations
from .context import load_context
from .model import fingerprint
from .launch import manual_command, open_tui
from .paths import DATA_DIR, PLUGIN_DIR, SCHEMA_DIR, Paths
from .project import current_branch, find_root
from .user import load_user


def print_report(paths: Paths, r: Report) -> None:
    rel = paths.rel(r.file)
    print(f"OK    {rel}" if r.ok else f"ERROR {rel}")
    for e in r.errors:
        print(f"  - {e}")
    for w in r.warnings:
        print(f"  warning: {w}")


def cmd_check(paths: Paths) -> int:
    ctx = load_context(paths, load_user(paths))
    reports = [ctx.map_report]
    if ctx.original_map:
        reports += check_translations(paths, ctx.original_map)
    reports.append(ctx.activity_report)
    for r in reports:
        print_report(paths, r)
    if ctx.original_map:
        print(f"map fingerprint: {fingerprint(ctx.original_map)} "
              "(a translation sets \"source\" to this value)")
    if all(r.ok for r in reports):
        return 0
    print(f"Schemas: {SCHEMA_DIR.as_posix()}")
    return 1


def translation_hint(ctx) -> str | None:
    """What the agent must do so the user can read the map in their language."""
    lang = ctx.user.language
    target = f"{DATA_DIR}/translations/map.{lang}.json"
    why = {
        "missing": f"there is no {lang} translation",
        "stale": f"the {lang} translation is out of date",
        "invalid": f"the {lang} translation has errors",
    }.get(ctx.translation)
    if why is None:
        return None
    return (f"translation: {why}. Translate {DATA_DIR}/map.json into {target}, "
            f"with \"language\": \"{lang}\" and \"source\": \"{fingerprint(ctx.original_map)}\". "
            "Then run `ezgoggles check`.")


def cmd_open(paths: Paths) -> int:
    result = open_tui(paths)
    manual = f"  {manual_command(paths)}"
    if result == "running":
        print("tui: already running.")
    elif result == "started":
        print("tui: started in a new window.")
    elif result == "disabled":
        print("tui: no window, because EZGOGGLES_NO_WINDOW is set. To start it by hand:")
        print(manual)
    else:
        print("tui: could not open a window. Ask the user to run this in a terminal:")
        print(manual)

    ctx = load_context(paths, load_user(paths), current_branch(paths))
    if ctx.map:
        order = [s["id"] for s in ctx.stages]
        print(f"map: OK ({len(order)} stages, in map order: {', '.join(order)}).")
        if hint := translation_hint(ctx):
            print(hint)
    elif not paths.map.exists():
        print(f"map: {DATA_DIR}/map.json does not exist. "
              f"If the user is the leader, read {paths.rel(PLUGIN_DIR)}/leader-guide.md.")
    else:
        print(f"map: {DATA_DIR}/map.json has errors. Run `ezgoggles check` and fix them.")

    user = ctx.user
    if user.ready:
        print(f"user: name={user.name} mode={user.mode} language={user.language}.")
    elif result in ("running", "started"):
        print("user: setup is not finished. Ask the user to finish the setup page "
              "in the TUI window, then run `ezgoggles open` again.")
    else:
        print("user: setup is not finished. The user must start the TUI with the "
              "command above and finish the setup page.")

    if ctx.branch is not None:
        if ctx.mine:
            print(f"branch: {ctx.branch} (stage: {ctx.mine}).")
        else:
            print(f"branch: {ctx.branch} (not a stage branch <name>/<stage-id>).")
    return 0


def cmd_init(paths: Paths) -> int:
    for line in setup_project(paths) or ["nothing to do: already set up."]:
        print(line)
    if not paths.map.exists():
        print(f"next: write {DATA_DIR}/map.json as {paths.rel(PLUGIN_DIR)}/leader-guide.md "
              "describes, then run `ezgoggles check`.")
    return 0


def cmd_tui(paths: Paths) -> int:
    from .tui.app import run  # Textual loads only for this command

    return run(paths)


COMMANDS: dict[str, tuple[Callable[[Paths], int], str]] = {
    "open": (cmd_open, "start the TUI in a new window if it is not running"),
    "tui": (cmd_tui, "run the TUI in this terminal"),
    "check": (cmd_check, "validate goggles-data/map.json and activity.json"),
    "init": (cmd_init, "leader setup: goggles-data/ and the entry line"),
}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="ezgoggles")
    p.add_argument("--root", help="group project root (default: found from the current dir)")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, (_, help_text) in COMMANDS.items():
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("--root", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    return COMMANDS[args.cmd][0](Paths(root))


if __name__ == "__main__":
    sys.exit(main())
