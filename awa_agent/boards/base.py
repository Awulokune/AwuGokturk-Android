"""Kart profili temel altyapisi ve pin dogrulama.

Yeni kart eklemek icin: BoardProfile donduren bir modul yazip
boards/__init__.py icindeki register() ile kaydedin. Cekirdek degismez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Pin rolleri
ROLE_DIGITAL_OUT = "digital_out"
ROLE_DIGITAL_IN = "digital_in"
ROLE_ANALOG_IN = "analog_in"
ROLE_PWM = "pwm"
ROLE_INTERRUPT = "interrupt"
ROLE_ANY = "any"


@dataclass(frozen=True)
class PinSpec:
    """Kullanicidan gelen pin ifadesinin cozumlenmis hali."""

    raw: str
    kind: str              # "digital" | "analog" | "gpio"
    number: Optional[int]  # kanonik numara (dijital/gpio), analog icin de sayi
    channel: Optional[int] = None  # analog kanal (0..15)

    def __str__(self) -> str:  # pragma: no cover - temsil
        return self.raw


@dataclass
class BoardProfile:
    key: str
    display_name: str
    mcu: str
    family: str                      # "avr" | "esp32"
    voltage: float
    framework_default: str           # "arduino" (Uno/Mega), "arduino-esp32" (ESP32)
    flash_kb: int = 0
    sram_kb: int = 0
    clock_mhz: int = 0

    digital_min: int = 0
    digital_max: int = -1
    pwm_pins: set = field(default_factory=set)
    interrupt_pins: set = field(default_factory=set)
    analog_labels: dict = field(default_factory=dict)   # "A0" -> kanal-no
    analog_numbers: set = field(default_factory=set)    # gecerli analog pin numaralari
    input_only: set = field(default_factory=set)
    unusable_pins: set = field(default_factory=set)     # hic kullanilamaz (flash vb.)
    strapping: set = field(default_factory=set)
    dac_pins: set = field(default_factory=set)
    adc2_pins: set = field(default_factory=set)
    uart: dict = field(default_factory=dict)            # "Serial" -> (tx, rx)
    i2c_default: tuple = ()
    spi_default: dict = field(default_factory=dict)
    adc_max: int = 1023
    features: set = field(default_factory=set)          # {"wifi","ble","dac",...}
    family_only_libs: dict = field(default_factory=dict)
    safe_outputs: list = field(default_factory=list)    # pin belirtilmezse onerilen cikislar
    safe_inputs: list = field(default_factory=list)
    safe_analog: list = field(default_factory=list)     # etiket ("A0") veya numara
    notes: list = field(default_factory=list)

    # ---- pin cozumleme ----
    def resolve_pin(self, text: str) -> Optional[PinSpec]:
        """'7' | 'D7' | 'A0' | 'GPIO18' -> PinSpec (gecersizse None)."""
        if text is None:
            return None
        s = str(text).strip()
        if not s:
            return None
        up = s.upper()
        m = re.fullmatch(r"A(\d{1,2})", up)
        if m:
            ch = int(m.group(1))
            num = self.analog_labels.get(f"A{ch}")
            return PinSpec(s, "analog", num, ch)
        m = re.fullmatch(r"(?:GPIO|G)?(\d{1,2})", up)
        if m:
            num = int(m.group(1))
            return PinSpec(s, "gpio" if up.startswith("GPIO") else "digital", num, None)
        return None

    # ---- sorgular ----
    def is_known_digital(self, num: int) -> bool:
        return self.digital_min <= num <= self.digital_max

    def is_analog_number(self, num: int) -> bool:
        return num in self.analog_numbers

    def is_pwm(self, num: int) -> bool:
        return num in self.pwm_pins

    def is_unusable(self, num: int) -> bool:
        return num in self.unusable_pins

    def is_input_only(self, num: int) -> bool:
        return num in self.input_only

    def supports(self, feature: str) -> bool:
        return feature in self.features

    # ---- dogrulama ----
    def check_pin(self, pin: PinSpec, role: str):
        """(ok, error, warning) dondurur. error doluysa kod uretilmez."""
        num = pin.number
        if num is None and pin.kind == "analog" and pin.channel is not None:
            # "A0" gibi etiketler karta gore sayiya cevrilir (Uno A0=14, Mega A0=54).
            num = self.analog_labels.get(f"A{pin.channel}")
        if num is None or num < 0:
            return False, f"Gecersiz pin: '{pin.raw}' (negatif veya cozumlenemeyen pin).", None

        if role == ROLE_ANALOG_IN:
            if num in self.analog_numbers:
                return True, None, self._analog_warning(num)
            return False, (f"'{pin.raw}' bu kartta analog giris degil "
                           f"(gecerli analog: {self._analog_range()})."), None

        # dijital/pwm rolleri
        if num < 0:
            return False, f"Gecersiz pin (negatif): {num}.", None
        if self.is_unusable(num):
            return False, (f"GPIO {num} bu kartta kullanilamaz "
                           f"(flash/PSRAM'e bagli). Baska pin secin."), None
        if not self.is_known_digital(num) and not self.is_analog_number(num):
            return False, (f"'{pin.raw}' bu kartta tanimli bir pin degil "
                           f"(dijital aralik: {self.digital_min}-{self.digital_max})."), None

        if role == ROLE_DIGITAL_OUT and self.is_input_only(num):
            return False, f"GPIO {num} yalnizca giris (input-only); cikis icin kullanilamaz.", None
        if role == ROLE_PWM and not self.is_pwm(num):
            return (False,
                    f"'{pin.raw}' bu kartta PWM desteklemiyor "
                    f"(PWM pinleri: {sorted(self.pwm_pins)}).", None)
        if role == ROLE_INTERRUPT and num not in self.interrupt_pins:
            return (False,
                    f"'{pin.raw}' bu kartta harici kesme (interrupt) desteklemiyor "
                    f"(kesme pinleri: {sorted(self.interrupt_pins)}).", None)

        warn = None
        if num in self.strapping:
            warn = (f"GPIO {num} strapping pinidir; boot davranisini etkileyebilir, "
                    f"dikkatli kullanin.")
        elif role == ROLE_ANALOG_IN and num in self.adc2_pins and self.supports("wifi"):
            warn = f"GPIO {num} ADC2'dedir; Wi-Fi aktifken ADC2 kullanilamaz."
        return True, None, warn

    def _analog_warning(self, num: int):
        if num in self.adc2_pins and self.supports("wifi"):
            return (f"GPIO {num} ADC2 birimindedir; ESP32'de Wi-Fi/Bluetooth aktifken "
                    f"ADC2 kullanilamaz, ADC1 (32-39) tercih edilmelidir.")
        return None

    def _analog_range(self) -> str:
        labels = sorted(self.analog_labels)
        if labels:
            return ", ".join(labels)
        return str(sorted(self.analog_numbers))

    def supports_library(self, lib: str) -> bool:
        fam = self.family_only_libs.get(lib)
        if fam is None:
            return True
        return self.family in fam
