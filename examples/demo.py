"""AwuGokturk Embedded Agent - kabul senaryolari demosu.

Her senaryo icin beklenen davranis, gercek sonuc ve basarisizlik nedeni raporlanir.
Cikti: ekrana ozet + `examples/demo_results.json`.

Calistirma:
    cd embedded_agent && python3 examples/demo.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from awa_agent.agent import AwuGokturkAgent          # noqa: E402
from awa_agent.build_validator import toolchain_available  # noqa: E402

# (id, prompt, beklenen_statusler, ek_kontrol_fn|None, aciklama)
SCENARIOS = [
    ("led_on_uno", "Arduino Uno'da 7. pindeki LED'i yak.",
     {"ok"}, lambda r: "LED_PIN = 7" in (r.code or ""),
     "Uno pin 7 korunmali ve kod derlenmeli."),
    ("neg_pin_reject", "Arduino Uno'da -1 numaralı pindeki LED'i yak.",
     {"error"}, lambda r: r.code is None,
     "Negatif pin reddedilmeli, varsayilana cevrilmemeli."),
    ("mega_two_btn", "Arduino Mega'da iki butonla iki LED'i kontrol et.",
     {"ok"}, lambda r: "Mega" in (r.board or ""),
     "Mega profili; varsayilan pinler bildirilmeli."),
    ("esp32_blink", "ESP32'de GPIO 18'deki LED'i 500 ms aralıklarla yakıp söndür.",
     {"ok"}, lambda r: "LED_PIN = 18" in (r.code or ""),
     "Klasik ESP32 varsayimi; GPIO 18 korunmali."),
    ("esp32_http", "ESP32'de Wi-Fi üzerinden HTTP isteği yap.",
     {"needs_info"}, lambda r: any("URL" in q for q in r.questions),
     "Eksik URL icin soru sorulmali; kod uydurulmamali."),
    ("a0_no_board", "A0 pinindeki potansiyometre değerini seri monitöre yazdır.",
     {"needs_info"}, lambda r: bool(r.questions),
     "Kart belirtilmedigi icin sorulmali."),
    ("pin_conflict_ask", "Bu kodda pin çakışması var mı?",
     {"needs_info"}, lambda r: bool(r.questions),
     "Kod verilmedigi icin istenmeli."),
    ("greeting", "Merhaba.",
     {"greeting"}, None, "Selamlama; yetenekler listelenmeli."),
    ("unknown_sensor", "Bilinmeyen bir sensörü oku.",
     {"unsupported"}, lambda r: r.code is None,
     "Taninmayan modul icin kod uretilmemeli."),
    # --- ek zorunlu test gruplari ---
    ("uno_pwm", "Arduino Uno'da 9. pinde PWM ile LED parlaklığını değiştir.",
     {"ok"}, lambda r: "PWM_PIN = 9" in (r.code or ""), "Uno PWM pini."),
    ("uno_analog", "Arduino Uno'da A0 pinindeki potansiyometre değerini seri monitöre yazdır.",
     {"ok"}, lambda r: "SENSOR_PIN = A0" in (r.code or ""), "Uno analog okuma."),
    ("mega_pwm_44", "Arduino Mega'da 44 numaralı pinde PWM ile LED parlaklığını değiştir.",
     {"ok"}, lambda r: "PWM_PIN = 44" in (r.code or ""),
     "Mega'ya ozgu PWM pini (Uno'da yok)."),
    ("mega_analog_a15", "Arduino Mega'da A15 pinindeki sensör değerini seri monitöre yazdır.",
     {"ok"}, lambda r: "SENSOR_PIN = A15" in (r.code or ""),
     "Mega A15 (Uno'da yok)."),
    ("esp32_adc", "ESP32'de GPIO 34'teki potansiyometre değerini seri monitöre yazdır.",
     {"ok"}, lambda r: "SENSOR_PIN = 34" in (r.code or ""), "ESP32 ADC1 (input-only pin)."),
    ("esp32_pwm", "ESP32'de GPIO 18'de PWM ile LED parlaklığını değiştir.",
     {"ok"}, lambda r: "ledcWrite" in (r.code or ""), "ESP32 LEDC PWM."),
    ("esp32_a0_invalid", "ESP32'de A0 pinindeki sensörü oku.",
     {"error"}, None, "ESP32'de A0 etiketi yok; hata verilmeli."),
    ("esp32_s3_unsupported", "ESP32-S3'te GPIO 5'teki LED'i yak.",
     {"unsupported"}, None, "Desteklenmeyen varyant."),
    ("mega_wifi_refused", "Arduino Mega'da Wi-Fi ile HTTP isteği yap.",
     {"error"}, lambda r: r.code is None, "Mega'da Wi-Fi yok; kod uretilmemeli."),
    ("debug_conflict", "Arduino Uno'da bu kodda pin çakışması var mı?\n```\n"
                       "void setup(){ pinMode(7, OUTPUT); digitalRead(7); }\n```",
     {"info"}, lambda r: any("cakismasi" in m or "kullaniliyor" in m for _, m in r.guard),
     "Mevcut kodda hata bulma."),
]


def main() -> int:
    ag = AwuGokturkAgent()
    tc = toolchain_available()
    print("Arac zinciri:", tc)
    print("NOT: arduino-cli/avr-gcc yoksa 'gercek derleme' YAPILAMAZ; yalnizca host "
          "sozdizimi dogrulamasi yapilir.\n")

    results = []
    passed = 0
    for sid, prompt, expect, extra, desc in SCENARIOS:
        r = ag.handle(prompt)
        ok = r.status in expect and (extra(r) if extra else True)
        passed += ok
        results.append({
            "id": sid, "prompt": prompt, "expected_status": sorted(expect),
            "actual_status": r.status, "passed": bool(ok),
            "board": r.board, "modules": r.modules,
            "build_ok": (r.build or {}).get("ok"),
            "build_note": (r.build or {}).get("note", "")[:120],
            "guard": r.guard, "questions": r.questions,
            "description": desc,
        })
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {sid:22s} status={r.status:11s} board={r.board}")
        if not ok:
            print(f"        beklenen={sorted(expect)} gercek={r.status} "
                  f"guard={r.guard} sorular={r.questions}")

    total = len(SCENARIOS)
    print(f"\nSonuc: {passed}/{total} senaryo gecti.")

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(outdir, "demo_results.json"), "w", encoding="utf-8") as f:
        json.dump({"toolchain": tc, "passed": passed, "total": total,
                   "results": results}, f, ensure_ascii=False, indent=2)
    print("Ayrinti: examples/demo_results.json")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
