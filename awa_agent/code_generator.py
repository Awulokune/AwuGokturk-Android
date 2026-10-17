"""Code Generator: yapilandirilmis gereksinimden kart profiline uygun tam kod uretir.

Kullanicinin verdigi pinler AYNEN kullanilir. Pin belirtilmemis ve guvenli bir
varsayilan varsa varsayilan atanir (ve rapora 'varsayilan' olarak islenir).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import boards as B
from . import knowledge_registry as KR

# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------

def pin_str(spec: B.PinSpec) -> str:
    """Kod icinde kullanilacak pin ifadesi (GPIO18 -> 18; A0 -> A0)."""
    raw = (spec.raw or "").strip()
    m = re.fullmatch(r"(?i)gpio\s*(-?\d+)", raw)
    if m:
        return m.group(1)
    if re.fullmatch(r"(?i)-?\d+", raw):
        return raw
    if re.fullmatch(r"A\d{1,2}", raw, re.IGNORECASE):
        return raw.upper()
    return raw


@dataclass
class Part:
    includes: list = field(default_factory=list)
    globals: list = field(default_factory=list)
    setup: list = field(default_factory=list)
    loop: list = field(default_factory=list)
    wiring: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    libraries: list = field(default_factory=list)


@dataclass
class GenContext:
    esp32_channels: dict = field(default_factory=dict)

    def channel(self, pin: str) -> int:
        if pin not in self.esp32_channels:
            self.esp32_channels[pin] = len(self.esp32_channels)
        return self.esp32_channels[pin]


def _const(name, value, ctype="int"):
    return f"const {ctype} {name} = {value};"


# ---------------------------------------------------------------------------
# Varsayilan pin atama
# ---------------------------------------------------------------------------
def fill_defaults(board: B.BoardProfile, actions: list):
    """Eksik pinleri guvenli varsayilanlarla doldurur.

    Donen: (defaulted[(module,role,pin_str)], unresolved[(module,role)])
    """
    used = set()
    for a in actions:
        for sp in a.pins.values():
            if sp.number is not None:
                used.add(sp.number)
    defaulted, unresolved = [], []
    for a in actions:
        md = KR.get_module(a.module)
        if not md:
            continue
        for role, rq in md.roles.items():
            if role in a.pins:
                # Kullanici pini verilmis (gecersiz olsa bile) -> AYNEN korunur,
                # varsayilana CEVRILMEZ. Gecerlilik AwuGuard'da denetlenir.
                continue
            spec = _pick_default(board, rq.role_type, used)
            if spec is None:
                unresolved.append((a.module, role))
                continue
            if spec.number is not None:
                used.add(spec.number)
            a.pins[role] = spec
            defaulted.append((a.module, role, pin_str(spec)))
    return defaulted, unresolved


def _pick_default(board: B.BoardProfile, role_type: str, used: set):
    if role_type == KR.T_DIGITAL_OUT:
        pool = board.safe_outputs
    elif role_type == KR.T_DIGITAL_IN:
        pool = board.safe_inputs
    elif role_type == KR.T_ANALOG_IN:
        pool = board.safe_analog
    elif role_type == KR.T_PWM:
        pool = [p for p in board.safe_outputs if board.is_pwm(p)]
    else:
        pool = board.safe_outputs
    for p in pool:
        spec = board.resolve_pin(str(p))
        if spec is None:
            spec = B.PinSpec(str(p), "digital", int(p)) if str(p).isdigit() else None
        if spec is None:
            continue
        if spec.number is not None and spec.number in used:
            continue
        ok, _, _ = board.check_pin(spec, role_type)
        if ok:
            return spec
    return None


# ---------------------------------------------------------------------------
# Modul sablonlari
# ---------------------------------------------------------------------------
def render(a, board: B.BoardProfile, ctx: GenContext) -> Part:
    fn = _RENDER.get(a.module)
    if fn is None:
        raise KeyError(a.module)
    return fn(a, board, ctx)


def _r_led_on(a, board, ctx):
    p = pin_str(a.pins["led"])
    return Part(globals=[_const("LED_PIN", p)],
                setup=[f"pinMode(LED_PIN, OUTPUT);", f"digitalWrite(LED_PIN, HIGH);"],
                wiring=[f"LED_ANOT -> {p} (direnc ile), LED_KATOT -> GND"],
                notes=["LED akimini sinirlamak icin seri direnc (220-330 ohm) kullanin."])


def _r_led_off(a, board, ctx):
    p = pin_str(a.pins["led"])
    return Part(globals=[_const("LED_PIN", p)],
                setup=["pinMode(LED_PIN, OUTPUT);", "digitalWrite(LED_PIN, LOW);"],
                wiring=[f"LED_ANOT -> {p}, LED_KATOT -> GND"])


def _r_led_blink(a, board, ctx):
    p = pin_str(a.pins["led"])
    iv = int(a.params.get("interval_ms", 500))
    return Part(globals=[_const("LED_PIN", p), _const("INTERVAL_MS", iv, "unsigned long")],
                setup=["pinMode(LED_PIN, OUTPUT);"],
                loop=["digitalWrite(LED_PIN, HIGH);", "delay(INTERVAL_MS);",
                      "digitalWrite(LED_PIN, LOW);", "delay(INTERVAL_MS);"],
                wiring=[f"LED -> {p}"],
                notes=[f"Yanip sonme araligi: {iv} ms."])


def _r_button_led(a, board, ctx):
    bp, lp = pin_str(a.pins["button"]), pin_str(a.pins["led"])
    db = int(a.params.get("debounce_ms", 50))
    return Part(globals=[_const("BUTTON_PIN", bp), _const("LED_PIN", lp),
                         _const("DEBOUNCE_MS", db, "unsigned long"),
                         "int _lastReading = HIGH;", "int _stable = HIGH;",
                         "unsigned long _lastChange = 0;"],
                setup=["pinMode(BUTTON_PIN, INPUT_PULLUP);", "pinMode(LED_PIN, OUTPUT);"],
                loop=["int reading = digitalRead(BUTTON_PIN);",
                      "if (reading != _lastReading) { _lastChange = millis(); }",
                      "if (millis() - _lastChange > DEBOUNCE_MS) {",
                      "  if (reading != _stable) {",
                      "    _stable = reading;",
                      "    digitalWrite(LED_PIN, _stable == LOW ? HIGH : LOW);",
                      "  }",
                      "}",
                      "_lastReading = reading;"],
                wiring=[f"Buton -> {bp} ile GND arasi (INPUT_PULLUP; ikinci direnc gerekmez)",
                        f"LED -> {lp}"],
                notes=[f"Yazilimsal debounce: {db} ms."])


def _r_two_buttons_two_leds(a, board, ctx):
    b1, b2 = pin_str(a.pins["button1"]), pin_str(a.pins["button2"])
    l1, l2 = pin_str(a.pins["led1"]), pin_str(a.pins["led2"])
    db = int(a.params.get("debounce_ms", 50))
    return Part(globals=[_const("BTN1", b1), _const("BTN2", b2),
                         _const("LED1", l1), _const("LED2", l2),
                         _const("DEBOUNCE_MS", db, "unsigned long"),
                         "const int BTN_PINS[2] = {BTN1, BTN2};",
                         "const int LED_PINS[2] = {LED1, LED2};",
                         "int _lastReading[2] = {HIGH, HIGH};",
                         "int _stable[2] = {HIGH, HIGH};",
                         "unsigned long _lastChange[2] = {0, 0};"],
                setup=["for (int i = 0; i < 2; i++) {",
                       "  pinMode(BTN_PINS[i], INPUT_PULLUP);",
                       "  pinMode(LED_PINS[i], OUTPUT);",
                       "}"],
                loop=["for (int i = 0; i < 2; i++) {",
                      "  int reading = digitalRead(BTN_PINS[i]);",
                      "  if (reading != _lastReading[i]) { _lastChange[i] = millis(); }",
                      "  if (millis() - _lastChange[i] > DEBOUNCE_MS) {",
                      "    if (reading != _stable[i]) {",
                      "      _stable[i] = reading;",
                      "      digitalWrite(LED_PINS[i], _stable[i] == LOW ? HIGH : LOW);",
                      "    }",
                      "  }",
                      "  _lastReading[i] = reading;",
                      "}"],
                wiring=[f"Buton1 -> {b1}, LED1 -> {l1}", f"Buton2 -> {b2}, LED2 -> {l2}"],
                notes=[f"Her buton kendi LED'ini kontrol eder; debounce {db} ms."])


def _r_two_leds(a, board, ctx):
    l1, l2 = pin_str(a.pins["led1"]), pin_str(a.pins["led2"])
    return Part(globals=[_const("LED1_PIN", l1), _const("LED2_PIN", l2)],
                setup=["pinMode(LED1_PIN, OUTPUT);", "pinMode(LED2_PIN, OUTPUT);",
                       "digitalWrite(LED1_PIN, HIGH);", "digitalWrite(LED2_PIN, HIGH);"],
                wiring=[f"LED1 -> {l1}, LED2 -> {l2} (seri direnc ile)"],
                notes=["Iki LED surekli yanar."])


def _r_analog_read_serial(a, board, ctx):
    p = "A" + str(a.pins["pot"].channel) if a.pins["pot"].kind == "analog" else \
        pin_str(a.pins["pot"])
    baud = int(a.params.get("baud", 9600))
    iv = int(a.params.get("interval_ms", 200))
    part = Part(globals=[_const("SENSOR_PIN", p), _const("INTERVAL_MS", iv, "unsigned long")],
                setup=[f"Serial.begin({baud});"],
                loop=["int deger = analogRead(SENSOR_PIN);", 'Serial.print("Deger: ");',
                      "Serial.println(deger);", "delay(INTERVAL_MS);"],
                wiring=[f"Potansiyometre orta uc -> {p}, uclar -> 5V/GND" if board.family == "avr"
                        else f"Sensor cikisi -> GPIO {p} (3.3V uyumlu olmali)"])
    if board.family == "esp32":
        part.notes.append(f"ESP32 ADC 12 bit (0-{board.adc_max}); besleme 3.3V'u gecmemeli.")
    else:
        part.notes.append("AVR ADC 10 bit (0-1023).")
    return part


def _r_pwm_fade(a, board, ctx):
    p = pin_str(a.pins["pwm_led"])
    step = int(a.params.get("step", 5))
    if board.family == "esp32":
        ch = ctx.channel(p)
        return Part(globals=[_const("PWM_PIN", p), _const("PWM_CH", ch),
                             _const("PWM_FREQ", 5000), _const("PWM_RES", 8)],
                    setup=["ledcSetup(PWM_CH, PWM_FREQ, PWM_RES);",
                           "ledcAttachPin(PWM_PIN, PWM_CH);"],
                    loop=["for (int d = 0; d <= 255; d += %d) { ledcWrite(PWM_CH, d); delay(15); }" % step,
                          "for (int d = 255; d >= 0; d -= %d) { ledcWrite(PWM_CH, d); delay(15); }" % step],
                    wiring=[f"LED -> GPIO {p} (LEDC kanal {ch})"],
                    notes=[f"ESP32 LEDC (freq=5000Hz, 8 bit). Parlaklik adimi: {step}."])
    return Part(globals=[_const("PWM_PIN", p)],
                setup=["pinMode(PWM_PIN, OUTPUT);"],
                loop=["for (int d = 0; d <= 255; d += %d) { analogWrite(PWM_PIN, d); delay(15); }" % step,
                      "for (int d = 255; d >= 0; d -= %d) { analogWrite(PWM_PIN, d); delay(15); }" % step],
                wiring=[f"LED -> {p} (PWM)"],
                notes=[f"analogWrite 0-255. Parlaklik adimi: {step}."])


def _r_pwm_write(a, board, ctx):
    p = pin_str(a.pins["pwm_led"])
    val = int(a.params.get("value", 128))
    if board.family == "esp32":
        ch = ctx.channel(p)
        return Part(globals=[_const("PWM_PIN", p), _const("PWM_CH", ch)],
                    setup=["ledcSetup(PWM_CH, 5000, 8);", "ledcAttachPin(PWM_PIN, PWM_CH);"],
                    loop=[f"ledcWrite(PWM_CH, {val});", "delay(1000);"],
                    wiring=[f"LED -> GPIO {p}"],
                    notes=[f"PWM degeri {val} (0-255), LEDC kanal {ch}."])
    return Part(globals=[_const("PWM_PIN", p)],
                setup=["pinMode(PWM_PIN, OUTPUT);"],
                loop=[f"analogWrite(PWM_PIN, {val});", "delay(1000);"],
                wiring=[f"LED -> {p} (PWM)"],
                notes=[f"PWM degeri {val} (0-255)."])


def _r_servo_sweep(a, board, ctx):
    p = pin_str(a.pins["servo"])
    mn = int(a.params.get("min_angle", 0))
    mx = int(a.params.get("max_angle", 180))
    dl = int(a.params.get("step_delay", 15))
    return Part(includes=["#include <Servo.h>"], libraries=["Servo"],
                globals=[_const("SERVO_PIN", p), "Servo _servo;"],
                setup=["_servo.attach(SERVO_PIN);"],
                loop=[f"for (int a = {mn}; a <= {mx}; a++) {{ _servo.write(a); delay({dl}); }}",
                      f"for (int a = {mx}; a >= {mn}; a--) {{ _servo.write(a); delay({dl}); }}"],
                wiring=[f"Servo sinyal -> {p}; servo beslemesi ayri 5V (GND ortak)"],
                notes=["Servo akimi yuksektir; harici besleme onerilir."])


def _r_ultrasonic_distance(a, board, ctx):
    t = pin_str(a.pins["trig"])
    e = pin_str(a.pins["echo"])
    iv = int(a.params.get("interval_ms", 200))
    part = Part(globals=[_const("TRIG_PIN", t), _const("ECHO_PIN", e),
                         _const("INTERVAL_MS", iv, "unsigned long")],
                setup=["pinMode(TRIG_PIN, OUTPUT);", "pinMode(ECHO_PIN, INPUT);",
                       "Serial.begin(9600);"],
                loop=["digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);",
                      "digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);",
                      "digitalWrite(TRIG_PIN, LOW);",
                      "long sure = pulseIn(ECHO_PIN, HIGH);",
                      "long cm = sure / 58;",
                      'Serial.print("Mesafe: "); Serial.print(cm); Serial.println(" cm");',
                      "delay(INTERVAL_MS);"],
                wiring=[f"HC-SR04 TRIG -> {t}, ECHO -> {e}, VCC -> 5V, GND -> GND"])
    if board.family == "esp32":
        part.notes.append("HC-SR04 ECHO 5V uretir; ESP32 3.3V oldugu icin gerilim bolucu gerekir.")
    return part


def _r_buzzer_tone(a, board, ctx):
    p = pin_str(a.pins["buzzer"])
    fq = int(a.params.get("freq", 1000))
    return Part(globals=[_const("BUZZER_PIN", p), _const("FREQ", fq)],
                setup=["pinMode(BUZZER_PIN, OUTPUT);"],
                loop=["tone(BUZZER_PIN, FREQ);", "delay(500);", "noTone(BUZZER_PIN);", "delay(500);"],
                wiring=[f"Buzzer + -> {p}, - -> GND"],
                notes=[f"tone() frekansi: {fq} Hz."])


def _r_dht_read(a, board, ctx):
    p = pin_str(a.pins["dht"])
    st = str(a.params.get("sensor_type", "DHT11")).upper()
    iv = int(a.params.get("interval_ms", 2000))
    return Part(includes=["#include <DHT.h>"], libraries=["DHT"],
                globals=[_const("DHT_PIN", p), f"#define DHT_TYPE {st}", "DHT _dht(DHT_PIN, DHT_TYPE);"],
                setup=["Serial.begin(9600);", "_dht.begin();"],
                loop=["float nem = _dht.readHumidity();", "float sicaklik = _dht.readTemperature();",
                      'Serial.print("Sicaklik: "); Serial.print(sicaklik);',
                      'Serial.print(" C, Nem: "); Serial.print(nem); Serial.println(" %");',
                      "delay(%d);" % iv],
                wiring=[f"DHT veri -> {p} (10k pull-up onerilir), VCC/GND"],
                notes=[f"Sensor tipi: {st}. Ornekleme araligi >= 2000 ms onerilir."])


def _r_lcd_i2c_print(a, board, ctx):
    parts = Part(includes=["#include <Wire.h>", "#include <LiquidCrystal_I2C.h>"],
                 libraries=["Wire", "LiquidCrystal_I2C"])
    addr = str(a.params.get("address", "0x27"))
    cols = int(a.params.get("cols", 16))
    rows = int(a.params.get("rows", 2))
    txt = str(a.params.get("text", "Merhaba"))
    parts.globals = [f"LiquidCrystal_I2C _lcd({addr}, {cols}, {rows});"]
    parts.setup = ["_lcd.init();", "_lcd.backlight();", "_lcd.setCursor(0, 0);",
                   f'_lcd.print("{txt}");']
    parts.wiring = ["LCD SDA -> SDA, SCL -> SCL, VCC -> 5V, GND -> GND"]
    return parts


def _r_i2c_scan(a, board, ctx):
    return Part(includes=["#include <Wire.h>"], libraries=["Wire"],
                globals=[], setup=["Serial.begin(9600);", "Wire.begin();"],
                loop=["for (byte addr = 1; addr < 127; addr++) {",
                      "  Wire.beginTransmission(addr);",
                      "  if (Wire.endTransmission() == 0) {",
                      '    Serial.print("Bulundu: 0x"); Serial.println(addr, HEX);',
                      "  }",
                      "}",
                      "delay(5000);"],
                wiring=["I2C SDA/SCL pinleri karta gore belirlenmistir"])


def _r_wifi_connect(a, board, ctx):
    ssid = a.params.get("ssid")
    pw = a.params.get("password")
    ph = []
    if not ssid:
        ssid = "YOUR_SSID"; ph.append("SSID")
    if not pw:
        pw = "YOUR_PASSWORD"; ph.append("sifre")
    return Part(includes=["#include <WiFi.h>"], libraries=["WiFi"],
                globals=[f'const char* WIFI_SSID = "{ssid}";',
                         f'const char* WIFI_PASS = "{pw}";'],
                setup=["Serial.begin(115200);", "WiFi.begin(WIFI_SSID, WIFI_PASS);",
                       "while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print(\".\"); }",
                       'Serial.println(); Serial.print("Bagli. IP: "); Serial.println(WiFi.localIP());'],
                loop=["delay(1000);"],
                wiring=["ESP32 dahili Wi-Fi (harici modul gerekmez)"],
                notes=(["Eksik yapilandirma: " + ", ".join(ph) + " (placeholder olarak birakildi)."]
                       if ph else []))


def _r_wifi_http_get(a, board, ctx):
    ssid = a.params.get("ssid")
    pw = a.params.get("password")
    url = a.params.get("url")
    ph = []
    if not ssid:
        ssid = "YOUR_SSID"; ph.append("SSID")
    if not pw:
        pw = "YOUR_PASSWORD"; ph.append("sifre")
    if not url:
        url = "http://example.com/"; ph.append("URL")
    iv = int(a.params.get("interval_ms", 10000))
    return Part(includes=["#include <WiFi.h>", "#include <HTTPClient.h>"],
                libraries=["WiFi", "HTTPClient"],
                globals=[f'const char* WIFI_SSID = "{ssid}";',
                         f'const char* WIFI_PASS = "{pw}";',
                         f'const char* TARGET_URL = "{url}";',
                         _const("REQUEST_INTERVAL_MS", iv, "unsigned long")],
                setup=["Serial.begin(115200);", "WiFi.begin(WIFI_SSID, WIFI_PASS);",
                       "while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print(\".\"); }",
                       'Serial.println(); Serial.println("Wi-Fi bagli.");'],
                loop=["if (WiFi.status() == WL_CONNECTED) {",
                      "  HTTPClient http;",
                      "  http.begin(TARGET_URL);",
                      "  int code = http.GET();",
                      "  if (code > 0) {",
                      '    Serial.print("HTTP kodu: "); Serial.println(code);',
                      "    String payload = http.getString();",
                      "    Serial.println(payload);",
                      "  } else {",
                      '    Serial.print("Istek hatasi: "); Serial.println(code);',
                      "  }",
                      "  http.end();",
                      "}",
                      "delay(REQUEST_INTERVAL_MS);"],
                wiring=["ESP32 dahili Wi-Fi"],
                notes=(["Eksik yapilandirma: " + ", ".join(ph) + " (placeholder)."]
                       if ph else []))


_RENDER = {
    "led_on": _r_led_on, "led_off": _r_led_off, "led_blink": _r_led_blink,
    "two_leds": _r_two_leds,
    "button_led": _r_button_led, "two_buttons_two_leds": _r_two_buttons_two_leds,
    "analog_read_serial": _r_analog_read_serial, "pwm_fade": _r_pwm_fade,
    "pwm_write": _r_pwm_write, "servo_sweep": _r_servo_sweep,
    "ultrasonic_distance": _r_ultrasonic_distance, "buzzer_tone": _r_buzzer_tone,
    "dht_read": _r_dht_read, "lcd_i2c_print": _r_lcd_i2c_print, "i2c_scan": _r_i2c_scan,
    "wifi_connect": _r_wifi_connect, "wifi_http_get": _r_wifi_http_get,
}


def generate(board: B.BoardProfile, actions: list, ctx: GenContext | None = None):
    """(code_str, parts) dondurur."""
    ctx = ctx or GenContext()
    parts = [render(a, board, ctx) for a in actions]
    includes, seen = [], set()
    for p in parts:
        for inc in p.includes:
            if inc not in seen:
                seen.add(inc)
                includes.append(inc)
    if "#include <Arduino.h>" not in includes:
        includes.insert(0, "#include <Arduino.h>")

    def block(title, lines, sep="\n"):
        if not lines:
            return ""
        body = "\n".join("  " + ln for ln in lines)
        return f"{title}\n{body}\n"

    globals_lines = []
    for p in parts:
        globals_lines.extend(p.globals)
        globals_lines.append("")

    setup_lines, loop_lines = [], []
    for p in parts:
        setup_lines.extend(p.setup)
        loop_lines.extend(p.loop)

    code = "\n".join(includes) + "\n\n"
    if globals_lines:
        code += "\n".join(globals_lines).rstrip() + "\n\n"
    code += "void setup() {\n" + "\n".join("  " + l for l in setup_lines) + "\n}\n\n"
    code += "void loop() {\n" + "\n".join("  " + l for l in loop_lines) + "\n}\n"
    return code, parts
