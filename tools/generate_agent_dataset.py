"""AwuGokturk Embedded Agent - ornek veri seti ureteci (EGITIM YAPMAZ).

Ne yapar:
  * `data_agent/agent_{train,validation,test}.jsonl` + `summary.json` uretir.
  * Her kayit icin "beklenen" alanlari MEVCUT AJANIN ciktisindan DONDURUR
    (referans; egitim yapilmaz).
  * Ayni `instruction_tr` yalnizca tek split'e girer (sizinti yok).

Calistirma:
    cd embedded_agent && python3 tools/generate_agent_dataset.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from awa_agent.agent import AwuGokturkAgent                 # noqa: E402
from awa_agent import requirement_parser as RP              # noqa: E402

OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_agent")

# (category, board, instruction, [paraphrases], valid_pins, invalid_pins, notes)
SEEDS = [
    # ---- code_generation_valid ----
    ("code_generation_valid", "arduino_uno", "Arduino Uno'da 7. pindeki LED'i yak.",
     ["Uno'da 7 numaralı pini HIGH yap.", "Arduino Uno 7. pin LED'i sürekli yak."],
     ["7", "13"], ["-1", "20"], "Sabit dijital cikis."),
    ("code_generation_valid", "arduino_uno", "Arduino Uno'da 13. pindeki LED'i 500 ms aralıklarla yakıp söndür.",
     ["Uno'da 13. pin LED'i yarım saniyede bir yanıp sönsün.", "Arduino Uno 13 numaralı pin ile blink yaz."],
     ["13", "9"], ["-1", "14"], "Blink; aralik ms."),
    ("code_generation_valid", "arduino_uno", "Arduino Uno'da buton ile LED kontrolü yaz.",
     ["Uno'da bir butona basınca LED yansın.", "Arduino Uno buton-led uygulaması (debounce)."],
     ["2", "3", "13"], ["-1"], "Varsayilan pinler bildirilir."),
    ("code_generation_valid", "arduino_uno", "Arduino Uno'da A0 pinindeki potansiyometre değerini seri monitöre yazdır.",
     ["Uno'da A0 analog değerini seri porta bas.", "Arduino Uno potansiyometre oku ve yazdır."],
     ["A0", "A1"], ["A6", "-1"], "AVR ADC 0-1023."),
    ("code_generation_valid", "arduino_uno", "Arduino Uno'da 9. pinde PWM ile LED parlaklığını değiştir.",
     ["Uno'da 9. pin PWM fade yaz.", "Arduino Uno 9 numaralı pinde parlaklık artır azalt."],
     ["9", "10", "11"], ["7", "13"], "PWM pinleri 3,5,6,9,10,11."),
    ("code_generation_valid", "arduino_uno", "Arduino Uno'da 10. pinde servo motoru süpür.",
     ["Uno'da 10. pine servo bağla ve süpür."], ["10"], ["7"], "Servo kutuphanesi."),
    ("code_generation_valid", "arduino_mega2560", "Arduino Mega'da iki butonla iki LED'i kontrol et.",
     ["Mega'da 2 buton 2 LED uygulaması yaz."], ["2", "3", "13", "12"], ["-1", "70"],
     "Mega'da 54 dijital pin."),
    ("code_generation_valid", "arduino_mega2560", "Arduino Mega'da 44 numaralı pinde PWM ile LED parlaklığını değiştir.",
     ["Mega 44. pinde analogWrite ile fade."], ["44", "45", "46"], ["7", "13"],
     "44-46 Mega'ya ozgu PWM (Uno'da yok)."),
    ("code_generation_valid", "arduino_mega2560", "Arduino Mega'da A15 pinindeki sensör değerini seri monitöre yazdır.",
     ["Mega A15 analog oku ve yazdır."], ["A15"], ["A0_UNO"], "Mega A0-A15 (54-69)."),
    ("code_generation_valid", "esp32", "ESP32'de GPIO 18'deki LED'i 500 ms aralıklarla yakıp söndür.",
     ["ESP32 GPIO18 LED blink 500 ms."], ["18", "19", "21"], ["6", "34"],
     "Klasik ESP32 varsayimi."),
    ("code_generation_valid", "esp32", "ESP32'de GPIO 34'teki potansiyometre değerini seri monitöre yazdır.",
     ["ESP32 GPIO34 analog oku, seri porta yaz."], ["34", "35", "32"], ["6", "-1"],
     "ADC1, 12 bit, 0-4095."),
    ("code_generation_valid", "esp32", "ESP32'de GPIO 18'de PWM ile LED parlaklığını değiştir.",
     ["ESP32 GPIO18 LEDC ile fade."], ["18", "19", "23"], ["6", "34"],
     "LEDC; 3.3V lojik."),
    ("code_generation_valid", "esp32", "ESP32'de Wi-Fi ile http://ornek.com/veri adresine HTTP isteği yap, SSID ev_agi, sifre 12345678.",
     ["ESP32 http://ornek.com/veri adresine GET isteği gönder."], [], [],
     "Yalnizca ESP32; URL/SSID gerekir."),
    # ---- invalid_pin ----
    ("invalid_pin", "arduino_uno", "Arduino Uno'da -1 numaralı pindeki LED'i yak.",
     ["Uno'da eksi bir pindeki LED'i yak."], [], ["-1"], "Negatif pin reddedilir."),
    ("invalid_pin", "arduino_uno", "Arduino Uno'da 20 numaralı pindeki LED'i yak.",
     [], [], ["20"], "Uno yalnizca 0-13 dijital."),
    ("invalid_pin", "arduino_mega2560", "Arduino Mega'da 99 numaralı pindeki LED'i yak.",
     [], [], ["99"], "Mega 0-53 dijital."),
    ("invalid_pin", "esp32", "ESP32'de GPIO 6'daki LED'i yak.",
     [], [], ["6"], "GPIO 6-11 flash'e bagli."),
    ("invalid_pin", "esp32", "ESP32'de GPIO 34'teki LED'i yak.",
     [], [], ["34"], "GPIO 34-39 yalnizca giris."),
    ("invalid_pin", "esp32", "ESP32'de A0 pinindeki sensörü oku.",
     [], [], ["A0"], "ESP32'de A0 etiketi yok."),
    # ---- missing_info ----
    ("missing_info", None, "A0 pinindeki potansiyometre değerini seri monitöre yazdır.",
     ["Potansiyometre değerini seri monitörde göster."], [], [], "Kart belirtilmedi -> sor."),
    ("missing_info", None, "Arduino için bir LED yak.",
     ["Arduino LED uygulaması yaz."], [], [], "Arduino modeli belirtilmedi -> sor."),
    ("missing_info", "esp32", "ESP32'de Wi-Fi üzerinden HTTP isteği yap.",
     ["ESP32 ile HTTP GET yap."], [], [], "URL/SSID eksik -> sor."),
    ("missing_info", None, "Bu kodda pin çakışması var mı?",
     ["Bu kodda hata var mı?"], [], [], "Kod verilmedi -> iste."),
    # ---- unsupported_module ----
    ("unsupported_module", "arduino_uno", "Bilinmeyen bir sensörü oku.",
     ["Tanımadığım bir modülü kullan."], [], [], "API uydurulmaz."),
    # ---- unsupported_board ----
    ("unsupported_board", None, "ESP8266 için LED blink yaz.",
     ["NodeMCU için kod yaz."], [], [], "ESP8266 desteklenmiyor."),
    ("unsupported_board", None, "RP2040 için LED yak.",
     ["Raspberry Pi Pico için kod yaz."], [], [], "Kapsam disi."),
    ("unsupported_board", None, "ESP32-S3'te GPIO 5'teki LED'i yak.",
     ["ESP32-C3 için LED blink yaz."], [], [], "Varyant desteklenmiyor."),
    ("unsupported_board", "arduino_mega2560", "Arduino Mega'da Wi-Fi ile HTTP isteği yap.",
     [], [], [], "Mega'da Wi-Fi yok."),
    # ---- debug ----
    ("debug", "arduino_uno", "Arduino Uno'da bu kodda pin çakışması var mı?\n```\nvoid setup(){ pinMode(7, OUTPUT); pinMode(7, INPUT); }\n```",
     [], [], [], "OUTPUT/INPUT cakismasi."),
    ("debug", "arduino_uno", "Arduino Uno'da bu kodda sorun var mı?\n```\nvoid setup(){ pinMode(9, OUTPUT); }\nvoid loop(){ analogWrite(7, 128); }\n```",
     [], [], ["7"], "PWM olmayan pinde analogWrite."),
    # ---- concept ----
    ("concept", None, "pinMode nedir?", ["pinMode ne işe yarar?"], [], [], "Yerel bilgi tabani."),
    ("concept", None, "analogRead ne yapar?", ["ADC nasıl çalışır?"], [], [], "AVR/ESP32 farki."),
    ("concept", None, "PWM nedir?", ["PWM ne işe yarar?"], [], [], "Parlaklik/motor hizi."),
    ("concept", None, "I2C nedir?", ["I2C nasıl kullanılır?"], [], [], "SDA/SCL."),
    # ---- greeting ----
    ("greeting", None, "Merhaba.", ["Selam.", "Merhaba, neler yapabilirsin?"], [], [], "Selamlama."),
]

SPLIT_BY_CATEGORY = {
    "code_generation_valid": ("train", "validation", "test"),
    "invalid_pin": ("train", "validation", "test"),
    "missing_info": ("train", "validation", "test"),
    "unsupported_module": ("train", "validation", "test"),
    "unsupported_board": ("train", "validation", "test"),
    "debug": ("train", "validation", "test"),
    "concept": ("train", "validation", "test"),
    "greeting": ("train", "validation", "test"),
}


def _req_to_dict(req):
    return {
        "modules": [a.module for a in req.actions],
        "pins": [{"role": r, "pin": v.raw} for a in req.actions for r, v in a.pins.items()],
        "params": [{"module": a.module, "params": a.params} for a in req.actions],
        "libraries": req.libraries,
        "unknown_modules": req.unknown_modules,
        "missing": req.missing,
        "ambiguous": req.ambiguous,
    }


def build_records():
    ag = AwuGokturkAgent(use_classifier=False)
    records = []
    per_cat_counter: dict[str, int] = {}
    for cat, board, instr, para, valid, invalid, notes in SEEDS:
        n = per_cat_counter.get(cat, 0)
        per_cat_counter[cat] = n + 1
        rid = f"agent_{cat}_{n:03d}"
        # split secimi: kategori icinde round-robin (deterministik)
        order = SPLIT_BY_CATEGORY[cat]
        split = order[n % 3]
        r = ag.handle(instr)
        req = RP.parse(instr)
        records.append({
            "id": rid, "split": split, "category": cat,
            "instruction_tr": instr, "paraphrases": para,
            "board": board, "framework": (r.framework),
            "structured_requirements": _req_to_dict(req),
            "expected_status": r.status,
            "expected_code": r.code,
            "expected_libraries": r.libraries,
            "valid_pins": valid, "invalid_pins": invalid,
            "guard_expectations": [{"level": lvl, "message": m} for lvl, m in r.guard],
            "compile_expected": ("host_syntax_ok" if (r.build or {}).get("ok")
                                 else ("host_syntax_fail" if r.build else "not_applicable")),
            "notes": notes,
        })
    return records


def check_leakage(records):
    seen = {}
    leaks = []
    for r in records:
        for text in [r["instruction_tr"]] + r.get("paraphrases", []):
            key = text.strip().lower()
            if key in seen and seen[key] != r["split"]:
                leaks.append((key, seen[key], r["split"]))
            seen[key] = r["split"]
    return leaks


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    records = build_records()
    leaks = check_leakage(records)
    if leaks:
        print("UYARI: split sizintisi tespit edildi:")
        for l in leaks:
            print("  ", l)

    files = {}
    for split in ("train", "validation", "test"):
        subset = [r for r in records if r["split"] == split]
        path = os.path.join(OUTDIR, f"agent_{split}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in subset:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        files[split] = len(subset)

    cats = {}
    for r in records:
        cats[r["category"]] = cats.get(r["category"], 0) + 1

    summary = {
        "note": "Ornek/tohum veri seti. EGITIM YAPILMADI. Beklenen alanlar mevcut "
                "ajanin donmus ciktisidir.",
        "total": len(records), "splits": files, "categories": cats,
        "leakage": leaks,
        "toolchain": {"arduino_cli": False, "avr_gcc": False, "gpp_host_syntax": True},
    }
    with open(os.path.join(OUTDIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
