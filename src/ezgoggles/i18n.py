"""Interface strings, loaded from locales/*.toml.

Extension point: drop a new <code>.toml file into locales/. It appears in
the setup page by itself. Set `base = "<code>"` under [meta] to start from
another locale and override only some keys (for example a playful style).
"""

from __future__ import annotations

import tomllib
from functools import lru_cache

from .paths import PACKAGE_DIR

LOCALE_DIR = PACKAGE_DIR / "locales"
FALLBACK = "en"


def _flatten(table: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in table.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


@lru_cache(maxsize=None)
def _raw(code: str) -> dict[str, str]:
    path = LOCALE_DIR / f"{code}.toml"
    try:
        with path.open("rb") as f:
            return _flatten(tomllib.load(f))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


@lru_cache(maxsize=None)
def _table(code: str, _seen: frozenset[str] = frozenset()) -> dict[str, str]:
    raw = _raw(code)
    base = raw.get("meta.base")
    if base and base not in _seen and base != code:
        merged = dict(_table(base, _seen | {code}))
    elif code != FALLBACK:
        merged = dict(_table(FALLBACK, _seen | {code}))
    else:
        merged = {}
    merged.update(raw)
    return merged


@lru_cache(maxsize=None)
def available() -> tuple[str, ...]:
    """Locale codes, in the order their files ask for."""
    codes = [p.stem for p in LOCALE_DIR.glob("*.toml") if _raw(p.stem)]
    return tuple(sorted(codes, key=lambda c: (int(_raw(c).get("meta.order", 99)), c)))


def language_name(code: str) -> str:
    return _raw(code).get("meta.name", code)


def tr(code: str, key: str, **kw: str) -> str:
    text = _table(code).get(key, key)
    return text.format(**kw) if kw else text
