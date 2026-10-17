"""Board Resolver: hedef karti, varyanti ve framework'u belirler.

Kart bilgisi yoksa ve gorev kart gerektiriyorsa kullaniciya SORAR (tahmin etmez).
ESP32 varyantlari (S2/S3/C3/S1) desteklenmez; belirtilirse durustce bildirilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import boards as B

_ESP_VARIANTS = {
    "s2": "ESP32-S2", "s3": "ESP32-S3", "c3": "ESP32-C3", "c2": "ESP32-C2",
    "c6": "ESP32-C6", "h2": "ESP32-H2", "s1": "ESP32-S1", "p4": "ESP32-P4",
}


@dataclass
class BoardResolution:
    board: object | None
    key: str | None
    framework: str | None
    needs_board: bool
    question: str | None = None
    assumed: list | None = None
    unsupported: str | None = None
    notes: list | None = None


def resolve(text: str, need_board: bool) -> BoardResolution:
    n = text.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")).lower()
    notes: list[str] = []
    assumed: list[str] = []

    if "esp8266" in n or "d1 mini" in n:
        return BoardResolution(None, None, None, True, unsupported=
                               "ESP8266 desteklenmiyor. Desteklenen kartlar: Arduino Uno, "
                               "Arduino Mega 2560, klasik ESP32.")
    if "rp2040" in n or "pico" in n:
        return BoardResolution(None, None, None, True, unsupported=
                               "RP2040/Pico su an kapsam disi (mimari genisletilebilir, "
                               "ancak profil eklenmedi).")
    if "esp-idf" in n or "esp idf" in n:
        return BoardResolution(None, None, None, True, unsupported=
                               "ESP-IDF framework'u ilk asamada desteklenmiyor; yalnizca "
                               "Arduino-ESP32 desteklenir.")

    # ESP32 varyant kontrolu
    if "esp32" in n:
        if re.search(r"esp32[\s\-]*(s2|s3|c3|c2|c6|h2|s1|p4|s2|c3)\b", n):
            m = re.search(r"esp32[\s\-]*(s2|s3|c3|c2|c6|h2|s1|p4)\b", n)
            v = _ESP_VARIANTS.get(m.group(1), m.group(1).upper())
            return BoardResolution(None, None, None, True, unsupported=
                                   f"{v} varyanti desteklenmiyor; su an yalnizca KLASIK ESP32 "
                                   f"(ESP32-D0WD/WROOM-32) profili var. Lutfen klasik ESP32 ile "
                                   f"devam edin veya varyant GPIO/ADC/PWM bilgilerini paylasin.")
        board = B.get_board("esp32")
        assumed.append("Kart/varyant belirtilmedi: KLASIK ESP32 (ESP32-D0WD/WROOM-32) varsayildi. "
                       "Farkli bir varyant (S2/S3/C3) ise belirtin.")
        fw = "arduino-esp32"
        if "arduino" in n:
            fw = "arduino-esp32"
        return BoardResolution(board, board.key, fw, False, assumed=assumed, notes=notes)

    if "mega" in n or "2560" in n:
        board = B.get_board("arduino_mega2560")
        return BoardResolution(board, board.key, "arduino", False, notes=notes)
    if "uno" in n:
        board = B.get_board("arduino_uno")
        return BoardResolution(board, board.key, "arduino", False, notes=notes)

    if "arduino" in n:  # model belirtilmemis
        return BoardResolution(None, None, None, True,
                               question="Hangi Arduino kartini hedefliyorsunuz? "
                                        "(Arduino Uno R3 / Arduino Mega 2560). "
                                        "Pinler ve donanim ozellikleri karta gore degisir.")

    if need_board:
        return BoardResolution(None, None, None, True,
                               question="Hedef karti belirtir misiniz? "
                                        "Desteklenen kartlar: Arduino Uno R3, Arduino Mega 2560, "
                                        "klasik ESP32. Pin/GPIO ve donanim gereksinimleri karta "
                                        "gore belirlenir.")
    return BoardResolution(None, None, None, False, notes=notes)
