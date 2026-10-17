"""Arduino Uno R3 (ATmega328P) kart profili."""

from __future__ import annotations

from .base import BoardProfile


def profile() -> BoardProfile:
    return BoardProfile(
        key="arduino_uno",
        display_name="Arduino Uno R3",
        mcu="ATmega328P",
        family="avr",
        voltage=5.0,
        framework_default="arduino",
        flash_kb=32,
        sram_kb=2,
        clock_mhz=16,
        digital_min=0,
        digital_max=13,
        pwm_pins={3, 5, 6, 9, 10, 11},
        interrupt_pins={2, 3},
        analog_labels={f"A{i}": 14 + i for i in range(6)},       # A0..A5 -> 14..19
        analog_numbers=set(range(14, 20)),
        input_only=set(),
        unusable_pins=set(),
        uart={"Serial": (0, 1)},
        i2c_default=(18, 19),                                     # A4=SDA, A5=SCL
        spi_default={"SS": 10, "MOSI": 11, "MISO": 12, "SCK": 13},
        adc_max=1023,
        features={"digital", "analog", "pwm", "interrupt", "i2c", "spi", "uart", "eeprom"},
        family_only_libs={"WiFi": {"esp32"}, "HTTPClient": {"esp32"}, "BLE": {"esp32"},
                          "BluetoothSerial": {"esp32"}},
        safe_outputs=[13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
        safe_inputs=[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        safe_analog=["A0", "A1", "A2", "A3", "A4", "A5"],
        notes=["Dijital 0/1 seri haberlesme (RX/TX) icindir; mumkunse kacinin.",
               "A4/A5 ayni zamanda I2C hattidir (SDA/SCL).",
               "PWM pinleri: 3, 5, 6, 9, 10, 11. Harici kesme: 2, 3."],
    )
