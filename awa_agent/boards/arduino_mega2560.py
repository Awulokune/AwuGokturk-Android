"""Arduino Mega 2560 (ATmega2560) kart profili.

Uno'nun pin sinirlari buraya UYGULANMAZ: Mega'da 54 dijital pin, A0-A15 analog
giris ve ek donanim UART'lar vardir.
"""

from __future__ import annotations

from .base import BoardProfile


def profile() -> BoardProfile:
    return BoardProfile(
        key="arduino_mega2560",
        display_name="Arduino Mega 2560",
        mcu="ATmega2560",
        family="avr",
        voltage=5.0,
        framework_default="arduino",
        flash_kb=256,
        sram_kb=8,
        clock_mhz=16,
        digital_min=0,
        digital_max=53,
        pwm_pins=set(range(2, 14)) | {44, 45, 46},
        interrupt_pins={2, 3, 18, 19, 20, 21},
        analog_labels={f"A{i}": 54 + i for i in range(16)},      # A0..A15 -> 54..69
        analog_numbers=set(range(54, 70)),
        input_only=set(),
        unusable_pins=set(),
        uart={"Serial": (0, 1), "Serial1": (19, 18), "Serial2": (17, 16), "Serial3": (15, 14)},
        i2c_default=(20, 21),
        spi_default={"SS": 53, "MOSI": 51, "MISO": 50, "SCK": 52},
        adc_max=1023,
        features={"digital", "analog", "pwm", "interrupt", "i2c", "spi", "uart", "eeprom"},
        family_only_libs={"WiFi": {"esp32"}, "HTTPClient": {"esp32"}, "BLE": {"esp32"},
                          "BluetoothSerial": {"esp32"}},
        safe_outputs=[13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] + list(range(22, 54)),
        safe_inputs=[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13] + list(range(22, 54)),
        safe_analog=[f"A{i}" for i in range(16)],
        notes=["Mega analog girisler A0-A15 (54-69) olarak da adreslenir; Uno'nun "
               "A0=14 eslemesi Mega icin gecerli DEGILDIR.",
               "PWM pinleri: 2-13, 44, 45, 46. Harici kesme: 2, 3, 18, 19, 20, 21.",
               "Ek donanim UART: Serial1(18/19), Serial2(16/17), Serial3(14/15).",
               "I2C: 20 (SDA), 21 (SCL). SPI: 50-53.",
               "Dijital 0/1 seri haberlesme icindir."],
    )
