"""Personal settings of the user, stored in goggles-data/.local/user.json."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from . import i18n
from .paths import Paths, read_json, write_json

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,29}$")
MODES = ("learn", "deliver")
THEMES = ("dark", "light")


@dataclass
class User:
    name: str = ""
    mode: str = ""
    language: str = "zh"
    theme: str = "dark"
    step: int = 1  # how many panels of the progressive view are open

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
    if raw.get("language") in i18n.available():
        user.language = raw["language"]
    if raw.get("theme") in THEMES:
        user.theme = raw["theme"]
    step = raw.get("step")
    if isinstance(step, int) and step >= 1:
        user.step = step
    return user


def save_user(paths: Paths, user: User) -> None:
    write_json(paths.user, asdict(user))
