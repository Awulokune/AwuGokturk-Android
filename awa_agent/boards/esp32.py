"""ESP32 (klasik, ESP32-D0WD / WROOM-32) kart profili.

ONEMLI: Bu profil *klasik* ESP32 icindir. ESP32-S2/S3/C3/S1 gibi varyantlar
farkli GPIO/ADC/PWM ozelliklerine sahiptir ve burada DESTEKLENMEZ; istek
gelirse kullaniciya sorulur. ESP32 destegi "ESP32 icin kod uretimi"dir;
modelin ESP32 uzerinde CALISTIRILMASI degildir.

GPIO kisitlari (klasik ESP32):
- 6..11: dahili SPI flash'e bagli -> kullanilamaz.
- 34..39: yalnizca giris (input-only), dahili pull-up yok.
- ADC1: GPIO 32..39; ADC2: GPIO 0,2,4,12,13,14,15,25,26,27 (Wi-Fi ile cakismaz
  degil: ADC2 Wi-Fi/Bluetooth aktifken KULLANILAMAZ).
- DAC: GPIO 25, 26.
- Strapping: 0, 2, 4, 5, 12, 15.
"""

from __future__ import annotations

from .base import BoardProfile

_ADC1 = set(range(32, 40))
_ADC2 = {0, 2, 4, 12, 13, 14, 15, 25, 26, 27}
_INPUT_ONLY = {34, 35, 36, 37, 38, 39}
_UNUSABLE = set(range(6, 12))            # 6..11 flash
_ALL_GPIO = set(range(0, 40))
_OUTPUT_CAPABLE = _ALL_GPIO - _UNUSABLE - _INPUT_ONLY


def profile() -> BoardProfile:
    return BoardProfile(
        key="esp32",
        display_name="ESP32 (klasik, ESP32-D0WD/WROOM-32)",
        mcu="ESP32-D0WD",
        family="esp32",
        voltage=3.3,
        framework_default="arduino-esp32",
        flash_kb=4096,
        sram_kb=520,
        clock_mhz=240,
        digital_min=0,
        digital_max=39,
        pwm_pins=set(_OUTPUT_CAPABLE),           # LEDC: tum cikis yetenekli GPIO
        interrupt_pins=set(_ALL_GPIO - _UNUSABLE),
        analog_labels={},                         # ESP32'de "A0" yok; GPIO numarasi kullanilir
        analog_numbers=set(_ADC1 | _ADC2),
        input_only=set(_INPUT_ONLY),
        unusable_pins=set(_UNUSABLE),
        strapping={0, 2, 4, 5, 12, 15},
        dac_pins={25, 26},
        adc2_pins=set(_ADC2),
        uart={"Serial": (1, 3), "Serial2": (17, 16)},
        i2c_default=(21, 22),
        spi_default={"SCK": 18, "MISO": 19, "MOSI": 23, "SS": 5},
        adc_max=4095,
        features={"digital", "analog", "pwm", "interrupt", "i2c", "spi", "uart",
                  "wifi", "ble", "dac", "touch"},
        family_only_libs={},
        safe_outputs=[18, 19, 21, 22, 23, 5, 17, 16, 25, 26, 27, 32, 33, 4, 13, 12],
        safe_inputs=[18, 19, 21, 22, 23, 5, 17, 16, 32, 33, 34, 35, 25, 26, 27, 13, 12, 4],
        safe_analog=[32, 33, 34, 35, 36, 39, 25, 26, 27],
        notes=["3,3 V lojik; 5 V'a toleransli DEGILDIR (seviye cevirici gerekebilir).",
               "GPIO 6-11 flash'e baglidir, kullanilamaz; GPIO 34-39 yalnizca giristir.",
               "ADC2 pinleri (0,2,4,12-15,25-27) Wi-Fi/Bluetooth aktifken kullanilamaz.",
               "Varsayilan I2C: 21 (SDA), 22 (SCL). Varsayilan SPI: 5,18,19,23.",
               "Klasik ESP32 varsayildi; varyant (S2/S3/C3) ise belirtin."],
    )
