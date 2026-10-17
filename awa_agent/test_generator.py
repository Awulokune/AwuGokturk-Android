"""Test Generator: mantik testleri, derleme testi ve donanim dogrulama plani uretir.

Burada uretilenler *oneri/plan*dir; gercek donanimda calistirilmamistir. Derleme
testi Build Validator ile (host sozdizimi) yapilir.
"""

from __future__ import annotations


def build_tests(board, actions) -> list[dict]:
    return [{"type": "build", "tool": "g++ -fsyntax-only (host stub)",
             "expect": "sozdizimi hatasiz", "note": "gercek AVR/ESP32 derlemesi degil"}]


def logic_tests(board, actions) -> list[dict]:
    tests = []
    for a in actions:
        key = a.module
        if key == "led_blink":
            iv = a.params.get("interval_ms", 500)
            tests.append({"type": "logic", "module": key,
                          "expect": f"LED {iv} ms yanar, {iv} ms soner (dongu)."})
        elif key == "led_on":
            tests.append({"type": "logic", "module": key, "expect": "LED surekli yanar."})
        elif key == "led_off":
            tests.append({"type": "logic", "module": key, "expect": "LED surekli soner."})
        elif key == "button_led":
            tests.append({"type": "logic", "module": key,
                          "expect": "Butona basinca LED yanar; birakinca soner (debounce)."})
        elif key == "two_buttons_two_leds":
            tests.append({"type": "logic", "module": key,
                          "expect": "Her buton yalnizca kendi LED'ini etkiler."})
        elif key == "analog_read_serial":
            tests.append({"type": "logic", "module": key,
                          "expect": "Seri monitorde analog deger gorunur (AVR 0-1023 / ESP32 0-4095)."})
        elif key in ("pwm_fade", "pwm_write"):
            tests.append({"type": "logic", "module": key,
                          "expect": "PWM cikisi 0-255 araliginda degisir/ sabittir."})
        elif key == "servo_sweep":
            tests.append({"type": "logic", "module": key,
                          "expect": "Servo belirtilen aci araliginda supurur."})
        elif key == "ultrasonic_distance":
            tests.append({"type": "logic", "module": key,
                          "expect": "Mesafe seri monitorde cm cinsinden gorunur; engel yaklasinca azalir."})
        elif key == "buzzer_tone":
            tests.append({"type": "logic", "module": key, "expect": "Buzzer'dan ton duyulur."})
        elif key == "dht_read":
            tests.append({"type": "logic", "module": key,
                          "expect": "Sicaklik ve nem seri monitorde gorunur."})
        elif key == "wifi_connect":
            tests.append({"type": "logic", "module": key,
                          "expect": "Wi-Fi baglanir; IP adresi seri monitorde gorunur."})
        elif key == "wifi_http_get":
            tests.append({"type": "logic", "module": key,
                          "expect": "HTTP kodu ve govde seri monitorde gorunur."})
        elif key == "i2c_scan":
            tests.append({"type": "logic", "module": key,
                          "expect": "Bagli I2C cihaz adresleri listelenir."})
    return tests


def hardware_plan(board, actions) -> list[str]:
    steps = [f"Hedef kart: {board.display_name} ({board.mcu}), lojik {board.voltage} V."]
    if board.family == "esp32":
        steps.append("ESP32 3,3V'tur; 5V cikisli sensorler icin gerilim bolucu/seviye "
                     "cevirici kullanin.")
    steps.append("Baglantilari guc KAPALI iken yapin; kutup ve GND ortakligini kontrol edin.")
    for a in actions:
        if a.module == "ultrasonic_distance":
            steps.append("HC-SR04 VCC=5V; ECHO'yu ESP32'de bolucu ile 3,3V'a indirin.")
        if a.module == "servo_sweep":
            steps.append("Servo beslemesini harici 5V'tan verin (akim yuksek); GND ortak.")
        if a.module in ("lcd_i2c_print", "i2c_scan"):
            steps.append("I2C hatlarinda 4,7k pull-up oldugundan emin olun.")
    steps.append("Yukleme sonrasi seri monitoru dogru hizda acin ve beklenen davranisi gozleyin.")
    steps.append("NOT: Bu adimlar otomatik dogrulanmaz; gercek donanim testi kullaniciya aittir.")
    return steps
