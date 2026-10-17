"""Knowledge / Library Registry.

Dogrulanabilir bilgi kaynagi:
  * MODULES: desteklenen modullerin metadata'si (roller, parametreler, kutuphaneler).
  * LIBRARIES: kutuphane API bilgisi ve hangi kart ailelerinde gecerli oldugu.

Kod uretim sablonlari code_generator.py icindedir; bu kayit yalnizca NE
destekledigimizi ve hangi API'lerin gecerli oldugunu tanimlar. Bilinmeyen
moduller icin giris YOKTUR; bu yuzden uydurma API uretilmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# pin rol tipleri
T_DIGITAL_OUT = "digital_out"
T_DIGITAL_IN = "digital_in"
T_ANALOG_IN = "analog_in"
T_PWM = "pwm"


@dataclass
class RoleReq:
    role_type: str
    label_tr: str
    required: bool = True
    default: Optional[str] = None      # pin belirtilmezse onerilecek isaret (None=otomatik)


@dataclass
class ParamDef:
    name: str
    label_tr: str
    kind: str = "int"                  # "int" | "float" | "str"
    required: bool = False
    default: object = None
    unit: str = ""


@dataclass
class ModuleDef:
    key: str
    name_tr: str
    category: str
    families: set
    roles: dict
    params: dict = field(default_factory=dict)
    libraries: list = field(default_factory=list)
    descr: str = ""


FAM_AVR = {"avr"}
FAM_ESP = {"esp32"}
FAM_ALL = {"avr", "esp32"}

MODULES: dict[str, ModuleDef] = {}


def _m(defn: ModuleDef):
    MODULES[defn.key] = defn
    return defn


_m(ModuleDef("led_on", "LED yakma (sabit)", "digital", FAM_ALL,
             {"led": RoleReq(T_DIGITAL_OUT, "LED pini")},
             descr="Belirtilen dijital pini surekli HIGH yapar."))
_m(ModuleDef("led_off", "LED sondurme (sabit)", "digital", FAM_ALL,
             {"led": RoleReq(T_DIGITAL_OUT, "LED pini")},
             descr="Belirtilen dijital pini surekli LOW yapar."))
_m(ModuleDef("led_blink", "LED yakip sondurme (blink)", "digital", FAM_ALL,
             {"led": RoleReq(T_DIGITAL_OUT, "LED pini")},
             {"interval_ms": ParamDef("interval_ms", "Yanip sonme araligi", "int", False, 500, "ms")},
             descr="LED'i verilen araliklarla yakip sondurur."))
_m(ModuleDef("button_led", "Buton ile LED kontrolu (debounce)", "digital", FAM_ALL,
             {"button": RoleReq(T_DIGITAL_IN, "Buton pini"),
              "led": RoleReq(T_DIGITAL_OUT, "LED pini")},
             {"debounce_ms": ParamDef("debounce_ms", "Debounce suresi", "int", False, 50, "ms")},
             descr="Butona basildiginda LED'i yakar (yazilimsal debounce ile)."))
_m(ModuleDef("two_buttons_two_leds", "Iki buton ile iki LED", "digital", FAM_ALL,
             {"button1": RoleReq(T_DIGITAL_IN, "1. buton pini"),
              "button2": RoleReq(T_DIGITAL_IN, "2. buton pini"),
              "led1": RoleReq(T_DIGITAL_OUT, "1. LED pini"),
              "led2": RoleReq(T_DIGITAL_OUT, "2. LED pini")},
             {"debounce_ms": ParamDef("debounce_ms", "Debounce suresi", "int", False, 50, "ms")},
             descr="Her buton kendi LED'ini kontrol eder."))
_m(ModuleDef("two_leds", "Iki LED yakma (sabit)", "digital", FAM_ALL,
             {"led1": RoleReq(T_DIGITAL_OUT, "1. LED pini"),
              "led2": RoleReq(T_DIGITAL_OUT, "2. LED pini")},
             descr="Iki LED'i surekli yakar."))
_m(ModuleDef("analog_read_serial", "Analog okuma -> seri port", "analog", FAM_ALL,
             {"pot": RoleReq(T_ANALOG_IN, "Analog giris pini")},
             {"baud": ParamDef("baud", "Seri hiz", "int", False, 9600, "bps"),
              "interval_ms": ParamDef("interval_ms", "Okuma araligi", "int", False, 200, "ms")},
             descr="Analog girişi okuyup seri porta yazdirir."))
_m(ModuleDef("pwm_fade", "PWM ile parlaklik (fade)", "pwm", FAM_ALL,
             {"pwm_led": RoleReq(T_PWM, "PWM pini")},
             {"step": ParamDef("step", "Adim", "int", False, 5, "")},
             descr="PWM pininde parlakligi kademeli artirip azaltir."))
_m(ModuleDef("pwm_write", "PWM degeri yazma", "pwm", FAM_ALL,
             {"pwm_led": RoleReq(T_PWM, "PWM pini")},
             {"value": ParamDef("value", "PWM degeri", "int", True, None, "0-255 (ESP32 LEDC 0-255)")},
             descr="PWM pinine sabit bir gorev dongusu degeri yazar."))
_m(ModuleDef("servo_sweep", "Servo motor supurme", "motor", FAM_ALL,
             {"servo": RoleReq(T_PWM, "Servo sinyal pini")},
             {"min_angle": ParamDef("min_angle", "Alt aci", "int", False, 0, "derece"),
              "max_angle": ParamDef("max_angle", "Ust aci", "int", False, 180, "derece"),
              "step_delay": ParamDef("step_delay", "Adim gecikmesi", "int", False, 15, "ms")},
             libraries=["Servo"], descr="Servo motoru 0-180 derece arasinda supurur."))
_m(ModuleDef("ultrasonic_distance", "HC-SR04 ultrasonik mesafe", "sensor", FAM_ALL,
             {"trig": RoleReq(T_DIGITAL_OUT, "TRIG pini"),
              "echo": RoleReq(T_DIGITAL_IN, "ECHO pini")},
             {"interval_ms": ParamDef("interval_ms", "Olcum araligi", "int", False, 200, "ms")},
             descr="HC-SR04 ile mesafe olcup seri porta yazdirir (pulseIn)."))
_m(ModuleDef("buzzer_tone", "Buzzer ile ton uretme", "sound", FAM_ALL,
             {"buzzer": RoleReq(T_DIGITAL_OUT, "Buzzer pini")},
             {"freq": ParamDef("freq", "Frekans", "int", False, 1000, "Hz")},
             descr="Buzzer'da tone() ile ses uretir."))
_m(ModuleDef("dht_read", "DHT11/DHT22 sicaklik-nem", "sensor", FAM_ALL,
             {"dht": RoleReq(T_DIGITAL_IN, "DHT veri pini")},
             {"sensor_type": ParamDef("sensor_type", "Sensor tipi", "str", False, "DHT11"),
              "interval_ms": ParamDef("interval_ms", "Olcum araligi", "int", False, 2000, "ms")},
             libraries=["DHT"], descr="DHT sensorunden sicaklik ve nem okur."))
_m(ModuleDef("lcd_i2c_print", "I2C LCD metin yazdirma", "display", FAM_ALL,
             {}, {"address": ParamDef("address", "I2C adresi", "str", False, "0x27"),
                  "cols": ParamDef("cols", "Sutun", "int", False, 16),
                  "rows": ParamDef("rows", "Satir", "int", False, 2),
                  "text": ParamDef("text", "Yazilacak metin", "str", False, "Merhaba")},
             libraries=["Wire", "LiquidCrystal_I2C"], descr="I2C LCD'ye metin yazdirir."))
_m(ModuleDef("i2c_scan", "I2C tarayici", "protocol", FAM_ALL,
             {}, libraries=["Wire"], descr="I2C hattindaki cihazlari tarar."))
_m(ModuleDef("wifi_connect", "Wi-Fi baglantisi (ESP32)", "network", FAM_ESP,
             {}, {"ssid": ParamDef("ssid", "Ag adi (SSID)", "str", True, None),
                  "password": ParamDef("password", "Sifre", "str", True, None)},
             libraries=["WiFi"], descr="ESP32'yi bir Wi-Fi agina baglar."))
_m(ModuleDef("wifi_http_get", "HTTP GET istegi (ESP32)", "network", FAM_ESP,
             {}, {"url": ParamDef("url", "Istek URL'i", "str", True, None),
                  "interval_ms": ParamDef("interval_ms", "Istek araligi", "int", False, 10000, "ms")},
             libraries=["WiFi", "HTTPClient"], descr="ESP32 ile bir URL'e HTTP GET istegi yapar."))


# ---------------------------------------------------------------------------
# Kutuphane API bilgisi (dogrulanmis kullanim icin referans)
# ---------------------------------------------------------------------------
LIBRARIES: dict[str, dict] = {
    "Servo": {"headers": ["Servo.h"], "families": {"avr", "esp32"},
              "api": ["Servo", "attach", "write", "writeMicroseconds", "detach", "read"],
              "notes": "ESP32'de Servo kutuphanesi vardir ancak ayni anda cok servo "
                       "LEDC kanali kullanir; pin secimi dikkatli yapilmalidir."},
    "DHT": {"headers": ["DHT.h"], "families": {"avr", "esp32"},
            "api": ["DHT", "begin", "readTemperature", "readHumidity"], "notes": ""},
    "Wire": {"headers": ["Wire.h"], "families": {"avr", "esp32"},
             "api": ["Wire", "begin", "beginTransmission", "endTransmission", "requestFrom",
                     "write", "read", "available"], "notes": ""},
    "SPI": {"headers": ["SPI.h"], "families": {"avr", "esp32"}, "api": ["SPI", "begin"], "notes": ""},
    "EEPROM": {"headers": ["EEPROM.h"], "families": {"avr"}, "api": ["EEPROM", "read", "write"],
               "notes": "Sadece AVR kartlarda dahili EEPROM kutuphanesi boyle adlandirilir."},
    "LiquidCrystal_I2C": {"headers": ["LiquidCrystal_I2C.h", "Wire.h"],
                          "families": {"avr", "esp32"},
                          "api": ["LiquidCrystal_I2C", "init", "backlight", "setCursor", "print",
                                  "clear"], "notes": ""},
    "WiFi": {"headers": ["WiFi.h"], "families": {"esp32"},
             "api": ["WiFi", "begin", "status", "localIP", "WL_CONNECTED"],
             "notes": "Yalnizca ESP32. Uno/Mega icin Wi-Fi kalkan (shield) gerekir; desteklenmiyor."},
    "HTTPClient": {"headers": ["HTTPClient.h", "WiFi.h"], "families": {"esp32"},
                   "api": ["HTTPClient", "begin", "GET", "POST", "getString", "end", "addHeader"],
                   "notes": "Yalnizca ESP32."},
}


def get_module(key: str) -> ModuleDef | None:
    return MODULES.get(key)


def module_keys() -> list[str]:
    return list(MODULES)


def library_info(name: str) -> dict | None:
    return LIBRARIES.get(name)


def support_matrix() -> list[dict]:
    """Kart x modul destek/uygunluk tablosu (raporda kullanilir)."""
    from . import boards as B

    rows = []
    for b in B.list_boards():
        for key, mod in MODULES.items():
            ok = b.family in mod.families
            lib_ok = all(b.supports_library(l) for l in mod.libraries)
            rows.append({"board": b.display_name, "module": key, "name": mod.name_tr,
                         "supported": bool(ok and lib_ok),
                         "reason": None if (ok and lib_ok) else
                         ("kart ailesi desteklenmiyor" if not ok else "kutuphane uyumsuz")})
    return rows
