"""`ezgoggles init`: leader setup. It only adds text. It never deletes or replaces text."""

from __future__ import annotations

from .paths import DATA_DIR, PLUGIN_DIR, Paths


def entry_line(plugin: str) -> str:
    guide = f"{plugin}/agent-guide.md"
    return (
        f"> **If you are an agent:** before any work, read `{guide}` and follow it. "
        f"If `{plugin}/` is empty, run `git submodule update --init` first.\n"
        f">\n"
        f"> **如果你是 Agent：** 开工前先阅读并遵循 `{guide}`。"
        f"如果 `{plugin}/` 是空的，先运行 `git submodule update --init`。\n"
    )


def _append(path, text: str, marker: str) -> str | None:
    """Append text unless marker is already in the file. Return what was done."""
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in old:
        return None
    if not old or old.endswith("\n\n"):
        sep = ""
    elif old.endswith("\n"):
        sep = "\n"
    else:
        sep = "\n\n"
    path.write_text(old + sep + text, encoding="utf-8")
    return f"added to {path.name}" if old else f"created {path.name}"


def setup_project(paths: Paths) -> list[str]:
    """Return a list of the changes made."""
    plugin = paths.rel(PLUGIN_DIR)
    done: list[str] = []

    paths.data.mkdir(exist_ok=True)
    gi = paths.data / ".gitignore"
    if not gi.exists():
        gi.write_text(".local/\n", encoding="utf-8")
        done.append(f"created {DATA_DIR}/.gitignore")

    entry = entry_line(plugin)
    marker = f"{plugin}/agent-guide.md"
    for name in ("README.md", "AGENTS.md"):
        if msg := _append(paths.root / name, entry, marker):
            done.append(msg)

    claude = paths.root / "CLAUDE.md"
    old = claude.read_text(encoding="utf-8") if claude.exists() else ""
    if "@AGENTS.md" not in old:
        sep = "" if not old or old.endswith("\n") else "\n"
        claude.write_text(old + sep + "@AGENTS.md\n", encoding="utf-8")
        done.append("added @AGENTS.md to CLAUDE.md" if old else "created CLAUDE.md")
    return done
