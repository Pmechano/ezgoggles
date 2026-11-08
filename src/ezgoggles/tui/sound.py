"""Sound cues. Off by default: members often work in shared rooms.

Only events that matter make a sound, and each sound is short and quiet.

Extension points:
  CUES    - event name -> notes (frequency in Hz, seconds). Add an event here,
            then call `cue(app, "<event>")` where it happens.
  PLAYERS - how to play a WAV file on this system. The first available
            player plays it. If none is available, the terminal bell rings.
"""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

from ..launch.launchers import is_wsl

CUES: dict[str, list[tuple[float, float]]] = {
    "handoff": [(784.0, 0.09), (587.3, 0.18)],  # down: look at this
    "tour_done": [(523.3, 0.07), (659.3, 0.07), (784.0, 0.16)],  # up: you are ready
}

RATE = 22050
VOLUME = 0.25


def _tone(freq: float, seconds: float) -> list[float]:
    """A soft metal tone: a few harmonics with a fast attack and a decay."""
    n = int(RATE * seconds)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.005) * math.exp(-t * 9)
        v = sum(a * math.sin(2 * math.pi * freq * h * t) for h, a in ((1, 1.0), (2, 0.4), (3, 0.15)))
        out.append(v * env / 1.55)
    return out


@lru_cache(maxsize=None)
def wav_for(event: str) -> Path:
    """Write the cue once into the temp directory."""
    folder = Path(tempfile.gettempdir()) / "ezgoggles-sounds"
    folder.mkdir(exist_ok=True)
    path = folder / f"{event}.wav"
    samples = [s for f, d in CUES[event] for s in _tone(f, d)]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s * VOLUME * 32767)) for s in samples))
    return path


def _spawn(argv: list[str]) -> None:
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


class Player:
    name = ""

    def available(self) -> bool:
        raise NotImplementedError

    def play(self, wav: Path) -> None:
        raise NotImplementedError


class WinSound(Player):
    name = "winsound"

    def available(self) -> bool:
        return sys.platform == "win32"

    def play(self, wav: Path) -> None:
        import winsound

        winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)


class Afplay(Player):
    name = "afplay"

    def available(self) -> bool:
        return sys.platform == "darwin" and bool(shutil.which("afplay"))

    def play(self, wav: Path) -> None:
        _spawn(["afplay", str(wav)])


class WslSoundPlayer(Player):
    """In WSL, the sound plays on the Windows side."""

    name = "wsl"

    def available(self) -> bool:
        return is_wsl() and bool(shutil.which("powershell.exe")) and bool(shutil.which("wslpath"))

    def play(self, wav: Path) -> None:
        win = subprocess.run(["wslpath", "-w", str(wav)], capture_output=True, text=True).stdout.strip()
        if win:
            _spawn(["powershell.exe", "-NoProfile", "-Command",
                    f"(New-Object Media.SoundPlayer '{win}').PlaySync()"])


class Paplay(Player):
    name = "paplay"

    def available(self) -> bool:
        return sys.platform.startswith("linux") and not is_wsl() and bool(shutil.which("paplay"))

    def play(self, wav: Path) -> None:
        _spawn(["paplay", str(wav)])


class Aplay(Paplay):
    name = "aplay"

    def available(self) -> bool:
        return sys.platform.startswith("linux") and not is_wsl() and bool(shutil.which("aplay"))

    def play(self, wav: Path) -> None:
        _spawn(["aplay", "-q", str(wav)])


PLAYERS: list[Player] = [WinSound(), Afplay(), WslSoundPlayer(), Paplay(), Aplay()]


@lru_cache(maxsize=1)
def player() -> Player | None:
    return next((p for p in PLAYERS if p.available()), None)


def cue(app, event: str) -> None:
    """Play a cue if the user turned sound on. Never raises."""
    user = getattr(app, "user", None)
    if user is None or not user.sound or event not in CUES:
        return
    try:
        p = player()
        if p is None:
            app.bell()
        else:
            p.play(wav_for(event))
    except Exception:  # a sound must never break the TUI
        pass
