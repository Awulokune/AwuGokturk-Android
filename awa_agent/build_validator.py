"""Build Validator: uretilen kodu mumkun oldugunca derler.

ONEMLI DURUSTLUK NOTU:
  Bu ortamda `arduino-cli`, `avr-gcc` veya `platformio` YOKTUR. Bu nedenle
  gercek AVR/ESP32 hedef derlemesi YAPILAMAZ. Yapilabilen tek sey, host
  uzerinde (`g++ -fsyntax-only`) Arduino/ESP32 API'sini taklit eden stub
  basliklarla SOZDIZIMI dogrulamasidir. Bu, gercek donanim derlemesi degildir
  ve yanitlarda boyle etiketlenir.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_STUBS = Path(__file__).resolve().parent / "stubs"


@dataclass
class BuildResult:
    ran: bool
    ok: bool
    tool: str
    kind: str                       # "host_syntax" | "none"
    returncode: int = None
    stderr: str = ""
    note: str = ""
    real_toolchain: bool = False


def toolchain_available() -> dict:
    return {
        "arduino-cli": shutil.which("arduino-cli") is not None,
        "avr-gcc": shutil.which("avr-gcc") is not None,
        "platformio": (shutil.which("platformio") is not None or shutil.which("pio") is not None),
        "g++": shutil.which("g++") is not None,
    }


def _include_dirs(board) -> list[str]:
    dirs = []
    if board is not None and getattr(board, "family", None) == "esp32":
        dirs.append(str(_STUBS / "esp32"))
    dirs.append(str(_STUBS / "arduino"))
    return dirs


def validate(code: str, board) -> BuildResult:
    tc = toolchain_available()
    if not tc["g++"]:
        return BuildResult(False, False, "yok", "none",
                           note="g++ bulunamadi; derleme yapilamadi.")

    with tempfile.TemporaryDirectory(prefix="awu_build_") as d:
        src = os.path.join(d, "sketch.cpp")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        cmd = ["g++", "-fsyntax-only", "-std=c++17"]
        for inc in _include_dirs(board):
            cmd += ["-I", inc]
        cmd.append(src)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except Exception as e:  # noqa: BLE001
            return BuildResult(False, False, "g++", "host_syntax", note=f"Calistirma hatasi: {e}")

    note = ("Host sozdizimi dogrulamasi (g++ -fsyntax-only, stub basliklar). "
            "GERCEK AVR/ESP32 derlemesi DEGILDIR; arduino-cli/avr-gcc bu ortamda yok.")
    if not tc["arduino-cli"]:
        note += " Gercek hedef derleme icin arduino-cli + kart cekirdegi gerekir."
    return BuildResult(ran=True, ok=(r.returncode == 0), tool="g++ (host)",
                       kind="host_syntax", returncode=r.returncode,
                       stderr=r.stderr.strip()[:2000], note=note, real_toolchain=False)
