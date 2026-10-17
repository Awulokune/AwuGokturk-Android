"""Intent Router: istegi gorev turune yonlendirir.

Kural tabanli sinyaller birincildir; mevcut 5K siniflandirici yalnizca ek bir
IPUCU olarak kullanilir ve celiskide kural kazanir. Softmax guveni kanit degildir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import chat_knowledge as CK
from .classifier5k import get_classifier

# gorev turleri (ince taneli)
CODE_GENERATION = "code_generation"
CONCEPT = "concept_explanation"
DEBUG = "debug"
TRANSFORM = "code_transform"
PROJECT = "project_scaffold"
CONCEPT_OR_INFO = "info"
GREETING = "greeting"
IDENTITY = "identity"
GENERAL_CHAT = "general_chat"
CREATIVE_WRITING = "creative_writing"
FACTS = "general_knowledge"
UNSUPPORTED = "unsupported_or_unclear"
NEEDS_INFO = "needs_info"

# Sohbet duzeyi kategoriler (kullaniciya donuk ust basliklar)
CAT_GREETING = "greeting"
CAT_IDENTITY = "identity"
CAT_GENERAL_CHAT = "general_chat"
CAT_CREATIVE = "creative_writing"
CAT_KNOWLEDGE = "general_knowledge"
CAT_CONCEPT = "concept_explanation"
CAT_EMBEDDED = "embedded_coding"
CAT_UNSUPPORTED = "unsupported"

_CATEGORY = {
    GREETING: CAT_GREETING,
    IDENTITY: CAT_IDENTITY,
    GENERAL_CHAT: CAT_GENERAL_CHAT,
    CREATIVE_WRITING: CAT_CREATIVE,
    FACTS: CAT_KNOWLEDGE,
    CONCEPT: CAT_CONCEPT,
    CODE_GENERATION: CAT_EMBEDDED,
    DEBUG: CAT_EMBEDDED,
    TRANSFORM: CAT_EMBEDDED,
    PROJECT: CAT_EMBEDDED,
    CONCEPT_OR_INFO: CAT_EMBEDDED,
    NEEDS_INFO: CAT_EMBEDDED,
    UNSUPPORTED: CAT_UNSUPPORTED,
}


def category_for(intent: str) -> str:
    return _CATEGORY.get(intent, CAT_UNSUPPORTED)

_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜâÂîÎûÛ", "cgiosuCGIOSUaAiIuU")


def _norm(text: str) -> str:
    return text.translate(_TR_MAP).lower()


_GREETINGS = {"merhaba", "selam", "selamlar", "gunaydin", "iyi gunler", "hey", "hi",
              "hello", "slm", "mrb", "nasilsin", "nasilsiniz"}

# Kimlik / yetenek sorulari ("sen kimsin", "neler yapabilirsin", ...)
# Ayrica davranis/durustluk sorulari ("bilmiyorsan ne yaparsin", "uydurma") kimlik
# kapsamindadir: bunlar bilgi dogrulugunu gevsetme talimati olarak ELE ALINMAZ.
_IDENTITY_WORDS = [
    "sen kimsin", "kimsin", "sen nesin", "sen kim", "kim oldugun",
    "gorevin ne", "goreviniz ne", "gorevin", "gorevimiz",
    "neler yapabilirsin", "neler yapabilir", "ne yapabilirsin", "ne yapabilir",
    "ne yaparsin", "yeteneklerin", "neler yaparsin", "kendini tanit",
    "adin ne", "ismin ne", "adini soyle",
    "bilmiyorsan", "bilmiyorsan bile", "cevap vermeye calis", "uydur",
]

# Gunluk sohbet / nezaket kalibi (tesekkur, veda, ...)
_SMALLTALK_WORDS = [
    "tesekkur", "sagol", "sag ol", "gorusuruz", "hosca kal", "hosca",
    "iyi geceler", "iyi aksamlar", "kendine iyi bak", "rica ederim", "gule gule",
    "naber",
]

# Yaratici yazarlik istekleri (kisa, sabit orneklerle karsilanir)
_CREATIVE_WORDS = [
    "hikaye", "masal", "siir", "bilim kurgu", "bilimkurgu", "roman", "oyku",
    "fabl", "senaryo", "hikaye anlat", "hikaye yaz",
]

_DEBUG_WORDS = ["hata", "yanlis", "cakis", "calismi", "neden calism", "duzelt", "debug",
                "problem", "sorun", "hatali", "duzeltir misin", "bozuk"]
_CONCEPT_WORDS = ["nedir", "ne ise yarar", "ne yapar", "ne demek", "farki nedir", "acikla",
                  "aciklar misin", "ornek ver", "nasil calisir", "ne anlama", "ne ise yarıyor"]
_TRANSFORM_WORDS = ["cevir", "donustur", "refactor", "yeniden duzenle", "iyilestir",
                    "optimize", "modernize", "port et", "uyarla"]
_PROJECT_WORDS = ["proje", "iskelet", "birden fazla", "hepsini", "tam sistem", "kur"]
_GEN_VERBS = ["yaz", "yak", "sondur", "oku", "uret", "kontrol et", "olustur", "kullan",
              "baslat", "ekle", "goster", "yazdir", "baglan", "gonder", "cevir"]
_HW_WORDS = ["led", "buton", "potansiyometre", "ldr", "sicaklik", "nem", "dht", "servo",
             "motor", "ultrasonik", "mesafe", "buzzer", "hoparlor", "lcd", "oled", "ekran",
             "pwm", "analog", "dijital", "pin", "gpio", "i2c", "spi", "uart", "seri",
             "wifi", "wi-fi", "bluetooth", "http", "mqtt", "role", "mosfet", "step motor",
             "adc", "sensor", "kesme", "interrupt", "zamanlayici", "timer", "eeprom", "sd"]
_BOARD_WORDS = ["arduino", "uno", "mega", "esp32", "esp-32", "wroom", "rp2040", "pico",
                "nano", "leonardo", "micro", "esp8266", "d1 mini"]


@dataclass
class IntentResult:
    intent: str
    needs_board: bool
    rule_signals: list = field(default_factory=list)
    classifier_label: str | None = None
    classifier_hint: str | None = None
    disagree: bool = False
    notes: list = field(default_factory=list)
    category: str = CAT_UNSUPPORTED     # kullaniciya donuk sohbet kategorisi


def route(text: str, use_classifier: bool = True) -> IntentResult:
    n = _norm(text)
    signals = []
    notes = []

    # selamlama / bos
    stripped = n.strip().strip(".!? ")
    if not stripped or stripped in _GREETINGS or re.fullmatch(r"(merhaba|selam|hi|hello|hey)[!. ]*",
                                                              stripped):
        return IntentResult(GREETING, needs_board=False, rule_signals=["greeting"],
                            category=CAT_GREETING)

    has_hw = any(w in n for w in _HW_WORDS)
    has_board = any(w in n for w in _BOARD_WORDS)
    # "bug" yalnizca tam sozcuk olarak debug sayilir ("bugun" -> "bug" yanlis eslesmesin)
    is_debug = any(w in n for w in _DEBUG_WORDS) or bool(re.search(r"\bbug\b", n))
    is_concept = any(w in n for w in _CONCEPT_WORDS)
    is_transform = any(w in n for w in _TRANSFORM_WORDS)
    is_project = any(w in n for w in _PROJECT_WORDS)
    is_gen = any(w in n for w in _GEN_VERBS)
    # Kimlik: yalnizca ad yazilmasi ("AwuGöktürk") veya kimlik/davranis sorusu
    is_name_only = CK.is_name_only(text)
    is_identity = is_name_only or any(w in n for w in _IDENTITY_WORDS)
    is_smalltalk = any(w in n for w in _SMALLTALK_WORDS)
    is_creative = any(w in n for w in _CREATIVE_WORDS)

    # Selamlama + nezaket: "Merhaba ... nasılsın?" gibi ifadeler de selamlamadir.
    # Ancak icinde donanim/eylem/duzeltme gecen mesajlar kodlama gorevi sayilir.
    has_greet_tok = bool(re.search(
        r"\b(merhaba|selam|selamlar|gunaydin|gunaydinlar|iyi gunler|hey|hello|hi|slm|mrb)\b", n))
    has_politeness = "nasilsin" in n or "nasilsiniz" in n
    is_greeting_soft = (has_greet_tok or has_politeness) and not (
        has_hw or is_gen or is_debug or is_project or is_transform)

    # Dogrulanmis genel bilgi (yalnizca kayitli bilgiler; uydurma yok)
    fact = CK.lookup_fact(text)

    if is_identity:
        intent = IDENTITY
        signals.append("identity:isim/kimlik")
    elif is_creative:
        intent = CREATIVE_WRITING
        signals.append("creative_writing:anahtar kelime")
    elif is_greeting_soft:
        intent = GREETING
        signals.append("greeting:selamlama+nezaket")
    elif is_smalltalk:
        intent = GENERAL_CHAT
        signals.append("general_chat:nezaket kalibi")
    elif fact is not None:
        intent = FACTS
        signals.append("general_knowledge:dogrulanmis kayit")
    elif is_debug and ("kod" in n or "pin" in n or "cakis" in n or "bu " in n or "su " in n):
        intent = DEBUG
        signals.append("debug:anahtar kelime")
    elif is_transform:
        intent = TRANSFORM
        signals.append("transform:anahtar kelime")
    elif is_concept and not is_gen:
        intent = CONCEPT
        signals.append("concept:soru kaliplari")
    elif is_project and has_hw:
        intent = PROJECT
        signals.append("project:anahtar kelime")
    elif has_hw:
        intent = CODE_GENERATION
        signals.append("code_generation:donanim+eylem")
    elif is_gen:
        intent = CODE_GENERATION
        signals.append("code_generation:eylem")
    else:
        intent = UNSUPPORTED
        signals.append("belirsiz")

    # kod uretimi/proje icin kart gerekli
    needs_board = intent in (CODE_GENERATION, PROJECT) and not has_board

    # 5K siniflandirici ipucu
    clf_label = clf_hint = None
    disagree = False
    # 5K ipucu yalnizca gomulu kodlama/kavram gorevlerinde anlamlidir; sohbet
    # kategorilerinde (kimlik, gunluk sohbet) gereksiz gurultu uretmez.
    if use_classifier and intent in (CODE_GENERATION, PROJECT, DEBUG, TRANSFORM, CONCEPT):
        cres = get_classifier().predict(text)
        if cres.available:
            clf_label, clf_hint = cres.label, cres.intent_hint
            # eslesme kurallari: arduino_* etiketleri code_generation ile uyumlu
            compat = {clf_hint == "code_generation" and intent in (CODE_GENERATION, PROJECT),
                      clf_hint == intent}
            if not any(compat):
                disagree = True
                notes.append(f"5K ipucu '{clf_label}' farkli; kural tabani kullanildi.")
        else:
            notes.append(cres.note)

    return IntentResult(intent, needs_board, signals, clf_label, clf_hint, disagree, notes,
                        category_for(intent))
