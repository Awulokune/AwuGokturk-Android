"""Kart kayit defteri (registry).

Genisleme: yeni bir kart modulu ekleyip register() cagirin; cekirdek degismez.
Alias'lar Turkce/Ingilizce/kisa adlari destekler.
"""

from __future__ import annotations

from . import arduino_mega2560, arduino_uno, esp32
from .base import (BoardProfile, PinSpec, ROLE_ANALOG_IN, ROLE_ANY, ROLE_DIGITAL_IN,
                   ROLE_DIGITAL_OUT, ROLE_INTERRUPT, ROLE_PWM)

_REGISTRY: dict[str, BoardProfile] = {}


def register(profile: BoardProfile, aliases=()) -> None:
    _REGISTRY[profile.key] = profile
    for a in aliases:
        _REGISTRY[a] = profile


def get_board(key: str) -> BoardProfile | None:
    return _REGISTRY.get(key)


def list_boards() -> list[BoardProfile]:
    seen, out = set(), []
    for p in _REGISTRY.values():
        if p.key not in seen:
            seen.add(p.key)
            out.append(p)
    return out


register(arduino_uno.profile(), aliases=["uno", "arduino uno", "arduino_uno_r3"])
register(arduino_mega2560.profile(), aliases=["mega", "mega2560", "mega 2560",
                                              "arduino mega", "arduino_mega"])
register(esp32.profile(), aliases=["esp32", "esp32 klasik", "esp32-d0wd", "esp32 wroom",
                                   "esp-wroom-32"])

__all__ = ["BoardProfile", "PinSpec", "get_board", "list_boards", "register",
           "ROLE_ANALOG_IN", "ROLE_DIGITAL_IN", "ROLE_DIGITAL_OUT", "ROLE_PWM",
           "ROLE_INTERRUPT", "ROLE_ANY"]
