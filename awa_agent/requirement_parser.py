"""Requirement Parser: Turkce istegi yapilandirilmis gereksinimlere cevirir.

Cikti: hangi moduller, hangi pinler, hangi parametreler, eksik/ belirsiz bilgi.
Kullanicinin VERDIGI pin/parametre AYNEN korunur (varsayilana cevrilmez).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from . import boards as B
from . import knowledge_registry as KR

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")

_PIN_RE = re.compile(
    r"(?<![\w])gpio\s*(?P<gpio>-?\d{1,3})"
    r"|(?<![\w])(?P<analog>A\d{1,2})(?![\w])"
    r"|(?<![\w])D(?P<dnum>\d{1,3})(?![\w])"
    r"|(?<![\w])(?P<n1>-?\d{1,3})\s*(?:\.|'|’)?\s*(?:numaral[ıi]|nolu|no|nc[ıi])?\s*"
    r"(?:pindeki|pininde|pine|pini|pin|pinde|pinden)"
    r"|(?:pin\s*\(?\s*(?P<n2>-?\d{1,3}))"
    r"|(?<![\w])(?P<n3>-?\d{1,3})\s*(?:'|’)\s*(?:deki|daki|de|da)",
    re.IGNORECASE)

_LIST_RE = re.compile(
    r"(?<![\w])(?P<a>-?\d{1,3})\s*(?:,|ve)\s*(?P<b>-?\d{1,3})\s*"
    r"(?:numaral[ıi]|nolu|no)?\s*(?:pindeki|pinlerde|pinler|pine|pini|pin|pinde|pinden)",
    re.IGNORECASE)

# Wi-Fi kimlik bilgileri / URL (kullanicinin VERDIGI degerler AYNEN korunur)
_SSID_RE = re.compile(
    r"(?:[sS][sS][iI][dD]|[aA][gGğĞ]\s*[aA][dD][ıiİI])\s*[:=]?\s*['\"]?([^\s'\",;]+)")
_PW_RE = re.compile(
    r"(?:[sSşŞ][iI][fF][rR][eE]|[pP][aA][sS][sS][wW][oO][rR][dD]|[pP][aA][rR][oO][lL][aA])"
    r"\s*[:=]?\s*['\"]?([^\s'\",;]+)")
_URL_RE = re.compile(r"https?://[^\s'\"]+")


def _extract_url(text: str):
    m = _URL_RE.search(text)
    return m.group(0) if m else None


def _extract_wifi_creds(text: str):
    """(ssid, sifre) dondurur; degerler kullanicinin yazdigi haliyle korunur."""
    ssid_m = _SSID_RE.search(text)
    pw_m = _PW_RE.search(text)
    ssid = ssid_m.group(1).rstrip(".,;:") if ssid_m else None
    pw = pw_m.group(1).rstrip(".,;:") if pw_m else None
    return ssid, pw


def _norm(s: str) -> str:
    return s.translate(_TR).lower()


def _find_pins(text: str):
    """[(PinSpec, position), ...] dondurur (tekrarsiz, sirali)."""
    found = []
    for m in _PIN_RE.finditer(text):
        raw = None
        if m.group("gpio") is not None:
            raw = m.group("gpio")
        elif m.group("analog") is not None:
            raw = m.group("analog").upper()
        elif m.group("dnum") is not None:
            raw = m.group("dnum")
        elif m.group("n1") is not None:
            raw = m.group("n1")
        elif m.group("n2") is not None:
            raw = m.group("n2")
        elif m.group("n3") is not None:
            raw = m.group("n3")
        if raw is None:
            continue
        found.append((_raw_to_spec(raw), m.start()))
    for m in _LIST_RE.finditer(text):
        found.append((_raw_to_spec(m.group("a")), m.start("a")))
        found.append((_raw_to_spec(m.group("b")), m.start("b")))
    seen, out = set(), []
    for spec, pos in sorted(found, key=lambda x: x[1]):
        key = (spec.raw, pos)
        if key in seen:
            continue
        seen.add(key)
        out.append((spec, pos))
    return out


def _raw_to_spec(raw: str) -> B.PinSpec:
    r = raw.strip()
    if re.fullmatch(r"-?\d{1,3}", r):
        return B.PinSpec(r, "digital", int(r))
    if re.fullmatch(r"A\d{1,2}", r, re.IGNORECASE):
        up = r.upper()
        return B.PinSpec(up, "analog", None, int(up[1:]))
    return B.PinSpec(r, "digital", None)


_TR_NUM = {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5,
           "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}


def _interval_ms(ntext: str) -> Optional[int]:
    # milisaniye: "500 ms", "250 milisaniye"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:ms|milisaniye[a-z]*|mili\s*saniye[a-z]*)", ntext)
    if m:
        return int(float(m.group(1).replace(",", ".")))
    # "bir saniye", "yarim saniye" gibi Turkce sayi sozcukleri.
    # NOT: Turkce hal ekleri ("saniyede", "saniyelik") de kabul edilir; aksi halde
    # "5 saniyede bir" ifadesi 500 ms sanilirdi (bkz. tests/test_arduino_accuracy.py).
    m = re.search(rf"\b({'|'.join(_TR_NUM)}|yarim)\s*(?:saniye[a-z]*|sn)\b", ntext)
    if m:
        w = m.group(1)
        return 500 if w == "yarim" else _TR_NUM[w] * 1000
    # rakam + saniye: "5 saniye", "5 saniyede bir" -> 5000 (500 DEGIL)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:saniye[a-z]*|sn|s)\b", ntext)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1000)
    return None


@dataclass
class Action:
    module: str
    pins: dict = field(default_factory=dict)      # role -> PinSpec
    params: dict = field(default_factory=dict)
    pin_order_raw: list = field(default_factory=list)


@dataclass
class Requirements:
    text: str
    actions: list = field(default_factory=list)
    libraries: list = field(default_factory=list)
    unknown_modules: list = field(default_factory=list)
    unsupported_features: list = field(default_factory=list)  # or. "http_server"
    missing: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    user_pins: list = field(default_factory=list)   # kullanicinin actigi pinler (aynen korunmali)


# rol -> anahtar kelimeler (yakinlik icin)
_ROLE_KW = {
    "led": ["led"], "led1": ["led"], "led2": ["led"],
    "button": ["buton", "dugme", "switch", "anahtar"],
    "button1": ["buton", "dugme"], "button2": ["buton", "dugme"],
    "pot": ["potansiyometre", "analog", "ldr", "adc", "sensor"],
    "pwm_led": ["pwm", "parlaklik", "fade"],
    "servo": ["servo"],
    "trig": ["trig"], "echo": ["echo"],
    "buzzer": ["buzzer", "hoparlor"],
    "dht": ["dht", "sicaklik", "nem"],
}


def parse(text: str) -> Requirements:
    n = _norm(text)
    req = Requirements(text=text)
    pins = _find_pins(text)
    req.user_pins = [p for p, _ in pins]

    def take_near(role, count=1, window=45):
        kws = _ROLE_KW.get(role, [])
        chosen = []
        for p, pos in pins:
            if p in [c for c in chosen]:
                continue
            for kw in kws:
                for m in re.finditer(re.escape(kw), n):
                    if abs(m.start() - pos) <= window or abs(m.end() - pos) <= window:
                        chosen.append(p)
                        break
                else:
                    continue
                break
            if len(chosen) >= count:
                break
        return chosen

    def remaining_pins():
        used = set()
        for a in req.actions:
            used |= set(a.pins.values())
        return [p for p, _ in pins if p not in used]

    # --- modul tespiti ---
    has_led = "led" in n
    has_btn = any(w in n for w in ["buton", "dugme", "anahtar", "switch"])
    has_two = "iki" in n or "2 " in n or "2 adet" in n
    has_pot = any(w in n for w in ["potansiyometre", "ldr"])
    has_analog = "analog" in n or "adc" in n
    has_pwm = "pwm" in n or "parlaklik" in n or "fade" in n
    has_servo = "servo" in n
    has_us = any(w in n for w in ["ultrasonik", "hc-sr04", "hcsr04", "mesafe"])
    has_buzzer = any(w in n for w in ["buzzer", "hoparlor", "ton uret", "ses"])
    has_dht = any(w in n for w in ["dht", "sicaklik", "nem sensor"])
    has_lcd = "lcd" in n
    has_i2c = "i2c" in n
    has_wifi = any(w in n for w in ["wifi", "wi-fi"])
    has_http = any(w in n for w in ["http", "istek", "get", "post", "web", "url"])
    # HTTP SUNUCUSU (istemci degil): "sunucu"/"server"/"isteklere cevap veren"
    has_server = any(w in n for w in ["sunucu", "server", "cevap veren"])
    wants_scan = "tara" in n and "i2c" in n
    unknown_sensor = ("bilinmeyen" in n and ("sensor" in n or "modul" in n)) or \
                     ("tanimadigim" in n or "tanimiyorum" in n)

    interval = _interval_ms(n)

    if unknown_sensor:
        req.unknown_modules.append("bilinmeyen_sensor")
        req.notes.append("Istek, taninmayan bir sensor/modul iceriyor; API uydurulmaz.")
        return req

    # HTTP SUNUCUSU: registry'de sunucu modulu YOK -> istemci kodu sunucu olarak sunulmaz.
    if has_server:
        req.unsupported_features.append("http_server")
        req.notes.append("HTTP/web SUNUCUSU modulu bu sistemde yok; Wi-Fi istemcisi "
                         "(HTTPClient) kodu sunucu olarak SUNULMAZ.")
        return req

    if has_btn and has_led:
        a = Action("two_buttons_two_leds" if (has_two and n.count("led") >= 1 and has_two)
                   else "button_led")
        if a.module == "two_buttons_two_leds":
            bs = take_near("button1", 2)
            ls = take_near("led1", 2)
            if bs:
                a.pins["button1"] = bs[0]
            if len(bs) > 1:
                a.pins["button2"] = bs[1]
            if ls:
                a.pins["led1"] = ls[0]
            if len(ls) > 1:
                a.pins["led2"] = ls[1]
        else:
            b = take_near("button")
            l = take_near("led")
            if b:
                a.pins["button"] = b[0]
            if l:
                a.pins["led"] = l[0]
        a.params["debounce_ms"] = 50
        req.actions.append(a)
    elif has_led and not has_pwm:
        if any(w in n for w in ["yakip sondur", "yanip son", "blink", "aralik", "periyot"]) or interval:
            a = Action("led_blink")
            if interval:
                a.params["interval_ms"] = interval
            l = take_near("led")
            if l:
                a.pins["led"] = l[0]
        elif has_two:
            a = Action("two_leds")
            ls = take_near("led1", 2)
            if ls:
                a.pins["led1"] = ls[0]
            if len(ls) > 1:
                a.pins["led2"] = ls[1]
        elif "sondur" in n and "yak" not in n:
            a = Action("led_off")
            l = take_near("led")
            if l:
                a.pins["led"] = l[0]
        else:
            a = Action("led_on")
            l = take_near("led")
            if l:
                a.pins["led"] = l[0]
        req.actions.append(a)
    elif has_servo:
        a = Action("servo_sweep")
        p = take_near("servo")
        if p:
            a.pins["servo"] = p[0]
        req.actions.append(a)
    elif has_us:
        a = Action("ultrasonic_distance")
        t = take_near("trig")
        e = take_near("echo")
        rem = remaining_pins()
        if t:
            a.pins["trig"] = t[0]
        elif rem:
            a.pins["trig"] = rem[0]
        if e:
            a.pins["echo"] = e[0]
        elif len(rem) > 1:
            a.pins["echo"] = rem[1]
        if interval:
            a.params["interval_ms"] = interval
        req.actions.append(a)
    elif has_buzzer:
        a = Action("buzzer_tone")
        p = take_near("buzzer")
        if p:
            a.pins["buzzer"] = p[0]
        fq = re.search(r"(\d{2,5})\s*hz", n)
        if fq:
            a.params["freq"] = int(fq.group(1))
        req.actions.append(a)
    elif has_dht:
        a = Action("dht_read")
        p = take_near("dht")
        if p:
            a.pins["dht"] = p[0]
        if "dht22" in n:
            a.params["sensor_type"] = "DHT22"
        elif "dht11" in n:
            a.params["sensor_type"] = "DHT11"
        req.actions.append(a)
    elif has_lcd:
        a = Action("lcd_i2c_print")
        m = re.search(r"'([^']+)'|\"([^\"]+)\"", text)
        if m:
            a.params["text"] = m.group(1) or m.group(2)
        req.actions.append(a)
    elif has_i2c and wants_scan:
        req.actions.append(Action("i2c_scan"))
    elif has_wifi and has_http:
        a = Action("wifi_http_get")
        url = _extract_url(text)
        ssid, pw = _extract_wifi_creds(text)
        if url:
            a.params["url"] = url
        else:
            req.missing.append("HTTP istegi icin hedef URL belirtilmedi.")
        if ssid:
            a.params["ssid"] = ssid
        else:
            req.missing.append("Wi-Fi icin SSID belirtilmedi.")
        if pw:
            a.params["password"] = pw
        else:
            req.missing.append("Wi-Fi icin sifre belirtilmedi.")
        if "post" in n:
            req.notes.append("POST istendi; su an GET ornegi uretilir, POST icin govde gerekir.")
        req.actions.append(a)
    elif has_wifi:
        a = Action("wifi_connect")
        ssid, pw = _extract_wifi_creds(text)
        if ssid:
            a.params["ssid"] = ssid
        else:
            req.missing.append("Wi-Fi icin SSID belirtilmedi.")
        if pw:
            a.params["password"] = pw
        else:
            req.missing.append("Wi-Fi icin sifre belirtilmedi.")
        req.actions.append(a)
    elif has_pwm:
        a = Action("pwm_fade")
        p = take_near("pwm_led")
        # "degeri ver" -> pwm_write
        valm = re.search(r"(\d{1,3})\s*(?:deger|degeri|degerini|seviye)", n)
        if valm and "fade" not in n and "parlaklik" not in n:
            a = Action("pwm_write", a.pins, {"value": int(valm.group(1))})
        if p:
            a.pins["pwm_led"] = p[0]
        req.actions.append(a)
    elif has_pot or (has_analog and any(w in n for w in ["oku", "yazdir", "seri", "goster"])) \
            or (any(pp.kind == "analog" for pp, _ in pins)
                and any(w in n for w in ["oku", "olc", "yazdir", "goster", "seri"])):
        a = Action("analog_read_serial")
        p = take_near("pot")
        if not p and "a0" in n:
            p = [B.PinSpec("A0", "analog", None, 0)]
        if not p and pins:
            p = [pins[0][0]]
        if p:
            a.pins["pot"] = p[0]
        if interval:
            a.params["interval_ms"] = interval
        req.actions.append(a)
    elif has_analog:
        a = Action("analog_read_serial")
        p = take_near("pot")
        if p:
            a.pins["pot"] = p[0]
        req.actions.append(a)

    # kutuphaneler
    libs = []
    for a in req.actions:
        md = KR.get_module(a.module)
        if md:
            libs.extend(md.libraries)
    req.libraries = sorted(set(libs))

    if not req.actions and not req.unknown_modules:
        req.ambiguous.append("Istek yapilandirilamadi: hangi modul/eylem oldugu net degil.")
    return req
