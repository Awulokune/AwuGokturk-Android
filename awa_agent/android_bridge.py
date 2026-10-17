"""Android kopru katmani (Chaquopy <-> Kotlin).

Kotlin tarafi `com.chaquo.python.Python` ile bu modulu cagirir; tum fonksiyonlar
**JSON string** dondurur, boylece tip donusumu sorunsuz olur. Is mantigi burada
TEKRAR YAZILMAZ; mevcut `AwuGokturkAgent` ve moduller aynen kullanilir.

Notlar:
  * Torch GEREKMEZ. 5K siniflandirici, `set_model_path()` ile verilen JSON
    agirliklari uzerinden saf Python (`classifier5k_lite`) ile calisir.
  * Derleme dogrulamasi cihazda `g++`/`arduino-cli` bulunmadigi icin
    `ran=False` doner ve yanitlarda acikca etiketlenir.
"""

from __future__ import annotations

import json

from . import boards as B
from . import build_validator, classifier5k, classifier5k_lite
from . import intent_router as IR
from . import knowledge_registry as KR
from .agent import AwuGokturkAgent

APP_NAME = "AwuGöktürk"
MODEL_NAME = "AwuGöktürk-Microcontroller:5K"
PACKAGE_ID = "com.awulokune.awugokturk"
SLOGAN = "NO SAY CAVAS"
APP_VERSION = "1.0.0"

_agent = None


def _get_agent() -> AwuGokturkAgent:
    global _agent
    if _agent is None:
        _agent = AwuGokturkAgent(use_classifier=True)
    return _agent


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Kurulum / bilgi
# ---------------------------------------------------------------------------
def set_model_path(path: str) -> str:
    """5K lite agirlik JSON yolunu ayarlar (Kotlin, asset'i filesDir'a kopyalar)."""
    global _agent
    classifier5k_lite.set_model_path(path)
    classifier5k.reset()
    _agent = None
    return _dump({"ok": True, "path": path})


def classifier_status() -> str:
    c = classifier5k.get_classifier()
    return _dump({
        "available": bool(getattr(c, "available", False)),
        "params": c.param_count() if hasattr(c, "param_count") else 0,
        "labels": list(getattr(c, "labels", [])),
        "backend": "lite-json" if type(c).__name__ == "LiteClassifier" else "torch",
    })


def app_info() -> str:
    """Uygulama/model kimligi ve destek matrisi (Ayarlar + Ana ekran)."""
    clf = classifier5k.get_classifier()
    return _dump({
        "app_name": APP_NAME,
        "model_name": MODEL_NAME,
        "package_id": PACKAGE_ID,
        "slogan": SLOGAN,
        "version": APP_VERSION,
        "boards": [{"key": b.key, "name": b.display_name, "family": b.family,
                    "mcu": b.mcu, "voltage": b.voltage,
                    "digital_range": [b.digital_min, b.digital_max],
                    "pwm_pins": sorted(b.pwm_pins),
                    "analog_labels": sorted(b.analog_labels),
                    "features": sorted(b.features)}
                   for b in B.list_boards()],
        "modules": [{"key": m.key, "name": m.name_tr, "category": m.category,
                     "families": sorted(m.families), "libraries": list(m.libraries)}
                    for m in KR.MODULES.values()],
        "tools": build_validator.toolchain_available(),
        "classifier": {"available": bool(getattr(clf, "available", False)),
                       "params": clf.param_count(),
                       "labels": list(getattr(clf, "labels", []))},
        "categories": [IR.CAT_GREETING, IR.CAT_IDENTITY, IR.CAT_GENERAL_CHAT,
                       IR.CAT_CREATIVE, IR.CAT_KNOWLEDGE, IR.CAT_CONCEPT,
                       IR.CAT_EMBEDDED, IR.CAT_UNSUPPORTED],
    })


def support_matrix() -> str:
    return _dump(KR.support_matrix())


# ---------------------------------------------------------------------------
# Ana giris: sohbet + kod uretimi ayni boru hattindan gecer
# ---------------------------------------------------------------------------
def _resp_to_dict(r) -> dict:
    return {
        "status": r.status,
        "category": IR.category_for(r.intent) if r.intent else None,
        "intent": r.intent,
        "message": r.message,
        "board": r.board,
        "framework": r.framework,
        "code": r.code,
        "modules": list(r.modules),
        "libraries": list(r.libraries),
        "wiring": list(r.wiring),
        "assumptions": list(r.assumptions),
        "guard": [{"level": lvl, "message": msg} for lvl, msg in r.guard],
        "build": r.build,
        "tests": list(r.tests),
        "hardware_plan": list(r.hardware_plan),
        "questions": list(r.questions),
        "notes": list(r.notes),
        "classifier_hint": r.classifier_hint,
        "model_name": MODEL_NAME,
    }


def handle(text: str, board_hint: str = "") -> str:
    """Sohbet + kod uretimi. Kotlin `board_hint` (or. 'uno') opsiyoneldir."""
    r = _get_agent().handle(text, board_hint or None)
    return _dump(_resp_to_dict(r))


def route(text: str) -> str:
    """Yalnizca yonlendirme bilgisi (test/hata ayiklama)."""
    ir = IR.route(text, use_classifier=False)
    return _dump({"intent": ir.intent, "category": ir.category,
                  "needs_board": ir.needs_board, "signals": list(ir.rule_signals)})


def guard_check(code: str, board_key: str = "") -> str:
    """Kullanicinin verdigi kodu AwuGuard'dan gecirir (pin/cakisma kontrolleri)."""
    from .agent import analyze_conflicts
    b = B.get_board(board_key) if board_key else None
    findings = analyze_conflicts(b, code)
    return _dump({"findings": [{"level": lvl, "message": m} for lvl, m in findings],
                  "board": b.display_name if b else None})


# ---------------------------------------------------------------------------
# Model guncelleme sistemi (GitHub Releases)
# ---------------------------------------------------------------------------
# Is mantigi `model_updater` icindedir; burada yalnizca JSON koprusu vardir.
# `configure_models`, paket ici model ile (varsa) indirilmis guncel model
# arasindan DOGRU olani secer ve onu yukler. Boylece uygulama yeniden
# baslatildiginda da dogru model kullanilir.
def configure_models(base_dir: str, bundled_path: str) -> str:
    """Depolama koklerini ayarlar, etkin modeli secer ve yukler."""
    from . import model_updater as MU
    info = MU.configure(base_dir, bundled_path, app_version=APP_VERSION)
    set_model_path(str(info.get("active_path") or bundled_path))
    info["loaded_path"] = str(info.get("active_path") or bundled_path)
    return _dump(info)


def update_status() -> str:
    """Model guncelleme ozeti + varsa surren islemin ilerlemesi."""
    from . import model_updater as MU
    out = MU.status()
    out["progress"] = MU.current_progress()
    out["running"] = MU.is_running()
    out["auto_check_due"] = MU.auto_check_due()
    out["max_artifact_bytes"] = MU.MAX_ARTIFACT_BYTES
    return _dump(out)


def update_check(force: bool = False) -> str:
    """GitHub Releases'i kontrol eder (ag islemi; Kotlin IO thread'inde cagirir)."""
    from . import model_updater as MU
    return _dump(MU.check_for_update(force=bool(force)))


def update_download_start() -> str:
    """Onaylanan surumu indirir, dogrular ve etkinlestirir (arka planda)."""
    from . import model_updater as MU

    def _on_activated(info):
        # Basarili etkinlestirme: yeni agirliklari gercekten yukle.
        try:
            set_model_path(str(info.get("active_path") or ""))
        except Exception:
            pass

    return _dump(MU.start_download(on_activated=_on_activated))


def update_progress() -> str:
    """Arayuzun yokladigi ilerleme (yuzde, inen/kalan, durum, hata)."""
    from . import model_updater as MU
    p = MU.current_progress()
    p["running"] = MU.is_running()
    return _dump(p)


def update_cancel() -> str:
    from . import model_updater as MU
    return _dump(MU.cancel())


def update_rollback() -> str:
    """Onceki modele doner (yedekten) ve onu yukler."""
    from . import model_updater as MU
    res = MU.rollback()
    if res.get("ok"):
        set_model_path(str(res.get("active_path") or ""))
    res["status"] = MU.status()
    return _dump(res)


def update_set_auto(enabled: bool) -> str:
    from . import model_updater as MU
    return _dump(MU.set_auto_check(bool(enabled)))
