"""Personal settings of the user, stored in goggles-data/.local/user.json."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .paths import Paths, read_json, write_json

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,29}$")
MODES = ("learn", "deliver")
LANGUAGES = ("zh", "en")
THEMES = ("dark", "light")

# Steps of the progressive view: 1 requirements, 2 map, 3 my stage, 4 activity.
LAST_STEP = 4


@dataclass
class User:
    name: str = ""
    mode: str = ""
    language: str = "zh"
    theme: str = "dark"
    step: int = 1

    @property
    def ready(self) -> bool:
        return bool(NAME_RE.match(self.name)) and self.mode in MODES


def load_user(paths: Paths) -> User:
    raw = read_json(paths.user)
    user = User()
    if not isinstance(raw, dict):
        return user
    name = raw.get("name")
    if isinstance(name, str) and NAME_RE.match(name):
        user.name = name
    if raw.get("mode") in MODES:
        user.mode = raw["mode"]
    if raw.get("language") in LANGUAGES:
        user.language = raw["language"]
    if raw.get("theme") in THEMES:
        user.theme = raw["theme"]
    step = raw.get("step")
    if isinstance(step, int) and 1 <= step <= LAST_STEP:
        user.step = step
    return user


def save_user(paths: Paths, user: User) -> None:
    write_json(paths.user, asdict(user))
