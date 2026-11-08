"""Where ezgoggles keeps its files, and small JSON helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = "goggles-data"
LOCAL_DIR = ".local"

PACKAGE_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = PACKAGE_DIR.parents[1]
SCHEMA_DIR = PACKAGE_DIR / "schema"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def data(self) -> Path:
        return self.root / DATA_DIR

    @property
    def local(self) -> Path:
        return self.data / LOCAL_DIR

    @property
    def map(self) -> Path:
        return self.data / "map.json"

    @property
    def translations(self) -> Path:
        return self.data / "translations"

    def translation(self, language: str) -> Path:
        return self.translations / f"map.{language}.json"

    @property
    def activity(self) -> Path:
        return self.local / "activity.json"

    @property
    def code(self) -> Path:
        return self.local / "code.json"

    @property
    def seen(self) -> Path:
        return self.local / "seen.json"

    @property
    def user(self) -> Path:
        return self.local / "user.json"

    @property
    def pid(self) -> Path:
        return self.local / "tui.pid"

    def rel(self, path: Path) -> str:
        """path relative to the project root, or absolute if it is outside."""
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()


def read_json(path: Path) -> object | None:
    """Return the parsed JSON, or None if the file is missing or broken."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
