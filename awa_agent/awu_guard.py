"""AwuGuard: halusinasyon ve hata azaltma kontrolleri.

Kontroller: pin gecerliligi, istenen pinin korunmasi, pin cakismasi, kart-kutuphane
uyumsuzlugu, eksik zorunlu parametre, eksik #include, celiskili gereksinim,
riskli elektriksel varsayim. Tanimsiz semboller icin asil kontrol Build
Validator'dadir (g++ hatalari); burada yalnizca heuristik on kontroller yapilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import knowledge_registry as KR
from .code_generator import pin_str


@dataclass
class Finding:
    level: str      # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class GuardReport:
    findings: list = field(default_factory=list)

    def add(self, level, code, message):
        self.findings.append(Finding(level, code, message))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.level == "warning"]

    @property
    def ok(self):
        return not self.errors


def check(board, requirements, actions, code: str, parts=None) -> GuardReport:
    rep = GuardReport()
    if board is None:
        rep.add("info", "no_board", "Kart profili yok; kart-bagimli kontroller atlandi.")
        return rep

    # 1) rol bazli pin dogrulama + 2) cakisma
    pin_users: dict[int, list[tuple[str, str, str]]] = {}
    for a in actions:
        md = KR.get_module(a.module)
        if md is None:
            rep.add("error", "unknown_module", f"Bilinmeyen modul: {a.module}")
            continue
        if board.family not in md.families:
            rep.add("error", "family_unsupported",
                    f"'{md.name_tr}' {board.display_name} icin desteklenmiyor "
                    f"(desteklenen aileler: {sorted(md.families)}).")
        for lib in md.libraries:
            if not board.supports_library(lib):
                rep.add("error", "lib_unsupported",
                        f"'{lib}' kutuphanesi {board.display_name} ile uyumlu degil.")
        for role, sp in a.pins.items():
            rq = md.roles.get(role)
            if rq is None:
                continue
            ok, err, warn = board.check_pin(sp, rq.role_type)
            if not ok:
                rep.add("error", "bad_pin", f"[{md.name_tr}] {rq.label_tr}: {err}")
            elif warn:
                rep.add("warning", "pin_warn", f"[{md.name_tr}] {rq.label_tr}: {warn}")
            eff = sp.number
            if eff is None and sp.kind == "analog" and sp.channel is not None:
                eff = board.analog_labels.get(f"A{sp.channel}")
            if eff is not None:
                pin_users.setdefault(eff, []).append((a.module, role, rq.role_type))

    for num, users in sorted(pin_users.items()):
        if len(users) > 1:
            roles = ", ".join(f"{m}:{r}" for m, r, _ in users)
            directions = {t for _, _, t in users}
            lvl = "error" if (KR.T_DIGITAL_OUT in directions and KR.T_DIGITAL_IN in directions) \
                else "warning"
            rep.add(lvl, "pin_conflict",
                    f"Pin {num} birden fazla rol icin kullaniliyor ({roles}) -> pin cakismasi.")

    # 3) istenen pinlerin korunmasi
    for sp in getattr(requirements, "user_pins", []):
        target = pin_str(sp)
        if target and target not in code:
            rep.add("error", "pin_changed",
                    f"Istenen pin '{sp.raw}' uretilen kodda bulunamadi (varsayilana cevrilmis olabilir).")

    # 4) eksik zorunlu parametre
    for a in actions:
        md = KR.get_module(a.module)
        if md is None:
            continue
        for pname, pd in md.params.items():
            if pd.required and (pname not in a.params or a.params[pname] in (None, "")):
                rep.add("warning", "missing_param",
                        f"[{md.name_tr}] Zorunlu parametre eksik: {pd.label_tr} ({pname}). "
                        f"Placeholder ile uretildi; lutfen degeri belirtin.")

    # 5) eksik #include
    used_libs = set(requirements.libraries) if requirements else set()
    for lib in used_libs:
        info = KR.library_info(lib)
        if not info:
            continue
        for h in info["headers"]:
            if h not in code:
                rep.add("warning", "missing_include",
                        f"'{lib}' kullaniliyor ama '{h}' dahil edilmemis olabilir.")

    # 6) riskli elektriksel varsayimlar
    if board.family == "esp32":
        for a in actions:
            if a.module == "ultrasonic_distance":
                rep.add("warning", "level_shift",
                        "HC-SR04 ECHO 5V verir; ESP32 3.3V oldugu icin gerilim bolucu gerekir.")
            if a.module in ("dht_read", "lcd_i2c_print", "servo_sweep"):
                rep.add("info", "power_3v3",
                        f"{board.display_name} 3,3V lojik kullanir; 5V modullerde seviye/"
                        f"besleme uyumunu kontrol edin.")
    return rep
