"""AwuGokturkAgent: boru hattini yoneten orkestrator.

Intent Router -> Board Resolver -> Requirement Parser -> Code Generator ->
AwuGuard -> Build Validator -> Test Generator -> Response Handler.
"""

from __future__ import annotations

import re
from collections import defaultdict

from . import awu_guard, board_resolver, build_validator, code_generator
from . import chat_knowledge as CK
from . import intent_router as IR
from . import knowledge_registry as KR
from . import requirement_parser as RP
from . import test_generator
from .code_generator import GenContext, fill_defaults, generate, pin_str
from .response_handler import AgentResponse

_CODE_FENCE = re.compile(r"```(?:cpp|c\+\+|arduino|ino)?\s*(.*?)```", re.S)

_CONCEPTS = {
    "pinmode": "pinMode(pin, mod): Bir pinin giris (INPUT/INPUT_PULLUP) mi cikis (OUTPUT) "
               "mi olacagini belirler. Ornek: pinMode(13, OUTPUT);",
    "digitalwrite": "digitalWrite(pin, deger): Dijital cikisa HIGH (lojik 1) veya LOW yazar.",
    "digitalread": "digitalRead(pin): Dijital giris durumunu HIGH/LOW olarak okur.",
    "analogread": "analogRead(pin): ADC ile analog giris okur. AVR'de 0-1023 (10 bit), "
                  "ESP32'de 0-4095 (12 bit).",
    "analogwrite": "analogWrite(pin, deger): PWM uretir (AVR'de 0-255). Yalnizca PWM "
                   "destekli pinlerde calisir (Uno: 3,5,6,9,10,11).",
    "pwm": "PWM, dijital cikista darbe genisligi modulasyonu ile ortalama gerilim "
           "uretir; LED parlakligi ve motor hizi icin kullanilir.",
    "i2c": "I2C, SDA/SCL iki hatli senkron seri protokoldur. Uno: A4/A5, Mega: 20/21, "
           "ESP32: varsayilan 21/22.",
    "spi": "SPI, SCK/MOSI/MISO/SS hatlariyla hizli senkron haberlesme saglar.",
    "uart": "UART, TX/RX ile asenkron seri haberlesme saglar. Uno: Serial; Mega ek "
            "Serial1-3; ESP32: Serial, Serial2.",
    "debounce": "Debounce, mekanik buton titremesini yazilimsal/temporal filtreleyerek "
                "tek kararlı okuma saglar.",
    "interrupt": "Kesme (interrupt), bir olayda ISR fonksiyonunu tetikler. Uno: pin 2/3.",
    "adc": "ADC, analog gerilimi sayisal degere cevirir. Cozunurluk karta gore degisir.",
    "millis": "millis(), programin baslangicindan beri gecen milisaniyeyi dondurur; "
              "delay()'den farkli olarak bloklamaz (blink without delay).",
    "servo": "Servo motor, PWM benzeri sinyalle aci kontrolu saglar (Servo kutuphanesi).",
    "dht": "DHT11/DHT22, tek tel ile sicaklik ve nem olcen sensorlerdir (DHT kutuphanesi).",
    "wifi": "Wi-Fi yalnizca ESP32'de dahilidir. Uno/Mega icin Wi-Fi kalkan gerekir ve "
            "bu sistem kalkanlari desteklemez.",
}


def extract_user_code(text: str) -> str:
    blocks = _CODE_FENCE.findall(text)
    if blocks:
        return "\n".join(b.strip() for b in blocks).strip()
    lines = []
    for ln in text.splitlines():
        if any(t in ln for t in (";", "pinMode", "digitalWrite", "analogRead", "analogWrite",
                                 "digitalRead", "void setup", "void loop")):
            lines.append(ln)
    return "\n".join(lines).strip()


def analyze_conflicts(board, code: str) -> list:
    """Kullanicinin verdigi koddaki pin kullanim cakismalarini bulur."""
    findings = []
    uses = defaultdict(set)          # pin -> {"out"/"in"/"pwm"}
    modes = defaultdict(list)        # pin -> [OUTPUT/INPUT/INPUT_PULLUP, ...]
    for m in re.finditer(r"pinMode\s*\(\s*([A-Za-z]?\d+)\s*,\s*(\w+)\s*\)", code):
        modes[m.group(1)].append(m.group(2))
    for m in re.finditer(r"(digitalWrite|analogWrite)\s*\(\s*([A-Za-z]?\d+)", code):
        uses[m.group(2)].add("out")
    for m in re.finditer(r"(digitalRead|analogRead)\s*\(\s*([A-Za-z]?\d+)", code):
        uses[m.group(2)].add("in")
    for m in re.finditer(r"analogWrite\s*\(\s*([A-Za-z]?\d+)", code):
        uses[m.group(1)].add("pwm")

    # 1) ayni pine celiskili pinMode tanimlari (OUTPUT vs INPUT/INPUT_PULLUP)
    for pin, mlist in modes.items():
        out = any(x == "OUTPUT" for x in mlist)
        inp = any(x in ("INPUT", "INPUT_PULLUP") for x in mlist)
        if out and inp:
            findings.append(("error", f"Pin {pin} ayni kodda hem OUTPUT hem INPUT olarak "
                                      f"tanimlanmis -> pin cakismasi ({modes[pin]})."))

    # 2) ayni pinin hem okuma hem yazma icin kullanilmasi
    for pin, roles in uses.items():
        if "out" in roles and "in" in roles:
            findings.append(("error", f"Pin {pin} hem giris hem cikis olarak kullaniliyor "
                                      f"(pin cakismasi)."))

    # 3) mod ile kullanim tutarsizligi
    for pin, mlist in modes.items():
        if "OUTPUT" in mlist and "in" in uses.get(pin, set()):
            findings.append(("error", f"Pin {pin} OUTPUT tanimli ama okuma icin kullaniliyor."))
        if any(x in ("INPUT", "INPUT_PULLUP") for x in mlist) and "out" in uses.get(pin, set()):
            findings.append(("error", f"Pin {pin} giris (INPUT) tanimli ama yazma icin kullaniliyor."))

    if board is not None:
        for pin in dict.fromkeys(list(uses) + list(modes)):
            spec = board.resolve_pin(pin)
            if spec is None:
                findings.append(("warning", f"Pin '{pin}' cozumlenemedi."))
                continue
            ok, err, _ = board.check_pin(spec, "any")
            if not ok:
                findings.append(("error", f"{board.display_name} icin {err}"))
        # analogWrite PWM kontrolu
        for m in re.finditer(r"analogWrite\s*\(\s*(\d+)", code):
            num = int(m.group(1))
            if not board.is_pwm(num):
                findings.append(("error", f"analogWrite pin {num}: {board.display_name} "
                                          f"PWM desteklemiyor (PWM: {sorted(board.pwm_pins)})."))
    return findings


class AwuGokturkAgent:
    def __init__(self, use_classifier: bool = True):
        self.use_classifier = use_classifier

    # -- yardimci: sohbet / kavram --
    def _identity_response(self, intent_res, text) -> AgentResponse:
        n = CK.norm(text)
        if CK.is_name_only(text):
            subtype = "name"          # kullanici yalnizca adi yazdi -> kisa tanitim
        elif any(w in n for w in ["bilmedig", "bilmiyor", "uydur", "emin degil",
                                  "yanlis bilgi", "halusinasyon", "guvenilir",
                                  "cevap vermeye calis"]):
            subtype = "honesty"
        elif any(w in n for w in ["neler yapabilir", "ne yapabilir", "yetenek", "neler yapsin",
                                  "neler yaparsin"]):
            subtype = "capabilities"
        elif "gorevim" in n or "gorevin" in n:
            subtype = "role"
        else:
            subtype = "who"
        return AgentResponse(status="info", intent=IR.IDENTITY,
                             message=CK.identity_answer(subtype),
                             notes=["Yanıt yerel bilgi kaynağından üretilir; 5K modeli "
                                    "genel sohbet için kullanılmaz."],
                             classifier_hint=intent_res.classifier_hint)

    def _smalltalk_response(self, intent_res, text) -> AgentResponse:
        n = CK.norm(text)
        if any(w in n for w in ["tesekkur", "sagol", "sag ol", "rica ederim"]):
            msg = ("Rica ederim! Yardımcı olabileceğim başka bir şey olursa buradayım.")
        elif any(w in n for w in ["gorusuruz", "hosca kal", "hosca", "iyi geceler",
                                  "iyi aksamlar", "gule gule", "kendine iyi bak"]):
            msg = "Görüşmek üzere! İhtiyaç duyduğunuzda buradayım."
        else:
            msg = "Anladım. Ne konuşmak isterseniz buradayım."
        return AgentResponse(status="info", intent=IR.GENERAL_CHAT, message=msg,
                             classifier_hint=intent_res.classifier_hint)

    def _creative_response(self, intent_res, text) -> AgentResponse:
        message, kind = CK.creative_answer(text)
        return AgentResponse(status="info", intent=IR.CREATIVE_WRITING, message=message,
                             notes=["Yaratıcı yazarlık yalnızca kısa, sabit örneklerle "
                                    "karşılanır; genel amaçlı bir dil modeli DEĞİLİM."],
                             classifier_hint=intent_res.classifier_hint)

    def _facts_response(self, intent_res, text) -> AgentResponse:
        fact = CK.lookup_fact(text)
        if fact is None:
            return AgentResponse(status="unsupported", intent=IR.FACTS,
                                 message=CK.unsupported_message(),
                                 classifier_hint=intent_res.classifier_hint)
        return AgentResponse(status="info", intent=IR.FACTS, message=fact.answer,
                             notes=["Bu bilgi, yerel ve elle doğrulanmış genel bilgi "
                                    "kaynağından gelir; 5K modeli kullanılmadı."],
                             classifier_hint=intent_res.classifier_hint)

    def _concept_response(self, intent_res, text) -> AgentResponse:
        # 1) Dogrulanmis Turkce kavram kaynagi (modüler chat_knowledge)
        topic = CK.lookup(text)
        if topic is not None:
            notes = ["Bu yanıt yerel, doğrulanmış Türkçe bilgi kaynağından gelir; 5K "
                     "modeli kullanılmadı."]
            if topic.related:
                notes.append("İlgili konular: " + ", ".join(topic.related) + ".")
            return AgentResponse(status="info", intent=IR.CONCEPT, message=topic.answer,
                                 notes=notes,
                                 classifier_hint=intent_res.classifier_hint)
        # 2) Gomulu API fonksiyonlari icin kisa aciklamalar (geri donus)
        n = CK.norm(text)
        for key, ans in _CONCEPTS.items():
            if key in n:
                return AgentResponse(status="info", intent=IR.CONCEPT, message=ans,
                                     classifier_hint=intent_res.classifier_hint,
                                     notes=["Bu yanıt yerel (kural tabanlı) bilgi "
                                            "kaynağından gelir; 5K modeli kullanılmadı."])
        # 3) Kapsam disi -> uydurma YOK, sinir acikca bildirilir
        return AgentResponse(status="needs_info", intent=IR.CONCEPT,
                             classifier_hint=intent_res.classifier_hint,
                             message=CK.concept_miss_message(),
                             questions=["Konuyu kapsam dahilindeki bir başlıkla "
                                        "(ör. CPU, RAM, ADC, PWM, I2C, HTTP sunucu/istemci) "
                                        "yeniden ifade eder misiniz?"])

    # -- ana giris --
    def handle(self, text: str, board_hint: str | None = None) -> AgentResponse:
        intent_res = IR.route(text, use_classifier=self.use_classifier)
        intent = intent_res.intent

        if intent == IR.GREETING:
            n = CK.norm(text)
            if "nasilsin" in n:
                msg = ("İyiyim, teşekkür ederim! Ben AwuGöktürk; Arduino Uno R3, "
                       "Mega 2560 ve klasik ESP32 için gömülü kod üretebilirim. Siz nasılsınız, "
                       "yardımcı olabileceğim bir şey var mı?")
            else:
                msg = ("Merhaba! Ben AwuGöktürk. Arduino Uno R3, Arduino Mega "
                       "2560 ve klasik ESP32 için desteklenen gömülü kodları üretebilir, "
                       "mevcut kodu inceleyebilir ve gereksinimleri netleştirebilirim. "
                       "Örneğin: 'Arduino Uno'da 7. pin'deki LED'i yak.'")
            return AgentResponse(status="greeting", intent=intent, message=msg,
                                 notes=["Kod isteyeceğinizde kartı belirtmeniz yeterli; "
                                        "sohbette kart şart değil."])

        if intent == IR.IDENTITY:
            return self._identity_response(intent_res, text)

        if intent == IR.GENERAL_CHAT:
            return self._smalltalk_response(intent_res, text)

        if intent == IR.CREATIVE_WRITING:
            return self._creative_response(intent_res, text)

        if intent == IR.FACTS:
            return self._facts_response(intent_res, text)

        if intent == IR.CONCEPT:
            return self._concept_response(intent_res, text)

        if intent in (IR.DEBUG, IR.TRANSFORM):
            return self._debug_or_transform(text, intent_res)

        if intent == IR.UNSUPPORTED:
            return AgentResponse(status="unsupported", intent=intent,
                                 message=CK.unsupported_message(),
                                 notes=["Emin olmadığım bir konuda cevap üretmedim."])

        # CODE_GENERATION / PROJECT
        return self._generate(text, intent_res, board_hint)

    # -- yetenek / ozellik uyumsuzlugu (eksik parametre sorusundan ONCE) --
    def _capability_problems(self, board, req):
        """(problemler, kart_uyumsuz) dondurur. Kart/ozellik uyumsuzlugu, eksik
        URL/SSID/sifre sorularindan ONCE raporlanmalidir."""
        problems = []
        board_incompat = False
        uses_wifi = ("http_server" in req.unsupported_features) or any(
            a.module in ("wifi_connect", "wifi_http_get") for a in req.actions)
        if uses_wifi and board is not None and not board.supports("wifi"):
            board_incompat = True
            problems.append(
                f"{board.display_name} Wi-Fi donanimina sahip DEGILDIR; Wi-Fi/HTTP gorevleri "
                f"yalnizca ESP32'de desteklenir. Kart degistirilmedi ({board.display_name}).")
        if "http_server" in req.unsupported_features:
            problems.append(
                "HTTP/web SUNUCUSU modulu bu sistemde yok; Wi-Fi istemcisi (HTTPClient) "
                "kodu sunucu olarak SUNULMAZ.")
        return problems, board_incompat

    @staticmethod
    def _mask(text, secrets):
        if not isinstance(text, str):
            return text
        for s in secrets:
            if s:
                text = text.replace(s, "***")
        return text

    # -- kod uretimi --
    def _generate(self, text, intent_res, board_hint=None) -> AgentResponse:
        req = RP.parse(text)

        # 1) negatif pinler karttan bagimsiz olarak REDDEDILIR
        neg = [p for p in req.user_pins if p.number is not None and p.number < 0]
        if neg:
            return AgentResponse(
                status="error", intent=intent_res.intent,
                message="Gecersiz pin numarasi: negatif pin kabul edilmez ve varsayilana "
                        "cevrilmez. Lutfen gecerli bir pin numarasi verin.",
                guard=[("error", f"Gecersiz (negatif) pin: {p.raw}") for p in neg],
                questions=["Gecerli bir pin numarasi belirtin (or. Uno icin 0-13 / A0-A5)."],
                classifier_hint=intent_res.classifier_hint)

        # 2) taninmayan modul -> uydurma yok
        if req.unknown_modules:
            return AgentResponse(status="unsupported", intent=intent_res.intent,
                                 message="Isteginiz taninmayan bir sensor/modul iceriyor. "
                                         "Var olmayan API veya kutuphane UYDURMAYACAGIM.",
                                 questions=["Sensor/modulun tam adini, veri sayfasini veya "
                                            "kullandigi kutuphaneyi paylasir misiniz?",
                                            "Baglanti arayuzu (I2C/SPI/analog/dijital) nedir?"],
                                 classifier_hint=intent_res.classifier_hint)

        # 3) kart cozumleme
        br = board_resolver.resolve(board_hint or text, need_board=True)
        if br.unsupported:
            return AgentResponse(status="unsupported", intent=intent_res.intent,
                                 message=br.unsupported,
                                 classifier_hint=intent_res.classifier_hint)
        if br.needs_board and br.board is None:
            return AgentResponse(status="needs_info", intent=intent_res.intent,
                                 message="Kod uretmeden once hedef karti netlestirmem gerekiyor; "
                                         "pinler ve donanim ozellikleri karta gore degisir.",
                                 questions=[br.question] if br.question else [],
                                 classifier_hint=intent_res.classifier_hint)

        # 4) kart/ozellik uyumsuzlugu -> eksik URL/SSID/sifre sorularindan ONCE
        problems, board_incompat = self._capability_problems(br.board, req)
        if problems:
            return AgentResponse(
                status=("error" if board_incompat else "unsupported"),
                intent=intent_res.intent,
                board=br.board.display_name if br.board else None, framework=br.framework,
                message="Istek desteklenmiyor (kod uretilmedi): " + " ".join(problems),
                guard=[("error", p) for p in problems],
                notes=list(req.notes),
                classifier_hint=intent_res.classifier_hint)

        if not req.actions:
            return AgentResponse(status="needs_info", intent=intent_res.intent,
                                 board=br.board.display_name, framework=br.framework,
                                 message="Istekten somut bir modul/eylem cikaramadim.",
                                 questions=["Hangi modulu nasil kullanmak istiyorsunuz?"],
                                 notes=req.ambiguous,
                                 classifier_hint=intent_res.classifier_hint)

        board = br.board
        assumptions = list(br.assumed or [])
        defaulted, unresolved = fill_defaults(board, req.actions)
        for m, role, p in defaulted:
            assumptions.append(f"{m}: '{role}' pini belirtilmedi -> guvenli varsayilan pin {p} "
                               f"(kullanildi).")
        if unresolved:
            return AgentResponse(status="needs_info", intent=intent_res.intent,
                                 board=board.display_name, framework=br.framework,
                                 message="Bazi roller icin guvenli varsayilan pin bulunamadi; "
                                         "lutfen pin belirtin.",
                                 questions=[f"{m} / {r} icin pin belirtin." for m, r in unresolved],
                                 assumptions=assumptions)

        ctx = GenContext()
        try:
            code, parts = generate(board, req.actions, ctx)
        except Exception as e:  # noqa: BLE001
            return AgentResponse(status="error", intent=intent_res.intent,
                                 board=board.display_name, framework=br.framework,
                                 message=f"Kod uretilemedi: {e}",
                                 classifier_hint=intent_res.classifier_hint)

        guard = awu_guard.check(board, req, req.actions, code, parts)
        guard_pairs = [(f.level, f.message) for f in guard.findings]

        wiring, notes = [], []
        for p in parts:
            wiring.extend(p.wiring)
            notes.extend(p.notes)
        wiring = list(dict.fromkeys(wiring))
        notes = list(dict.fromkeys(notes))
        if br.notes:
            notes.extend(br.notes)

        questions = list(req.missing)
        status = "ok"
        if guard.errors:
            status = "error"
        elif questions or any("placeholder" in n for n in notes):
            status = "needs_info"

        resp = AgentResponse(
            status=status, intent=intent_res.intent, board=board.display_name,
            framework=br.framework, modules=[a.module for a in req.actions],
            libraries=req.libraries, wiring=wiring, assumptions=assumptions,
            guard=guard_pairs, questions=questions, notes=notes,
            classifier_hint=intent_res.classifier_hint,
            message=("Kod uretildi ve AwuGuard'dan gecti." if status == "ok" else
                     ("AwuGuard hata buldu; kod GUVENILIR sayilmaz." if status == "error" else
                      "Kod uretildi ancak bazi bilgiler eksik/asSUMED; asagiya bakin.")))

        # Sirlari log/rapor alanlarinda MASK (kod bloğu kullanicinin istedigi cikti
        # oldugu icin gercek degeri korur; maskeleme yalnizca teshis alanlarina uygulanir).
        secrets = [a.params.get("password") for a in req.actions if a.params.get("password")]
        if secrets:
            resp.notes = [self._mask(x, secrets) for x in resp.notes]
            resp.questions = [self._mask(x, secrets) for x in resp.questions]
            resp.assumptions = [self._mask(x, secrets) for x in resp.assumptions]
            resp.message = self._mask(resp.message, secrets)
            resp.guard = [(lvl, self._mask(m, secrets)) for lvl, m in resp.guard]

        if status == "error":
            return resp
        resp.code = code
        resp.build = self._build(board, code)
        resp.tests = (test_generator.build_tests(board, req.actions)
                      + test_generator.logic_tests(board, req.actions))
        resp.hardware_plan = test_generator.hardware_plan(board, req.actions)
        return resp

    # -- debug / transform --
    def _debug_or_transform(self, text, intent_res) -> AgentResponse:
        code = extract_user_code(text)
        if not code:
            return AgentResponse(status="needs_info", intent=intent_res.intent,
                                 message="Inceleyebilmem icin kodu paylasmaniz gerekiyor.",
                                 questions=["Hata ayiklanacak kodu ```...``` blogu icinde "
                                            "veya satirlar halinde paylasin.",
                                            "Hedef kart nedir? (pin dogrulamasi icin)"],
                                 classifier_hint=intent_res.classifier_hint)
        br = board_resolver.resolve(text, need_board=False)
        board = br.board
        findings = analyze_conflicts(board, code)
        status = "info"          # Ajan basariyla yanit verdi; bulgular guard'da tasinir
        msg = ("Kod incelendi. " +
               ("Pin cakismasi/gecersiz kullanim BULUNDU." if findings else
                "Belirgin bir pin cakismasi bulunmadi."))
        if board is None:
            msg += " (Kart belirtilmedi; pin araligi/ozellik dogrulamasi yapilamadi.)"
        return AgentResponse(status=status, intent=intent_res.intent,
                             board=board.display_name if board else None,
                             message=msg,
                             guard=[(lvl, m) for lvl, m in findings],
                             questions=([] if board else ["Tam pin dogrulamasi icin hedef karti "
                                                          "belirtin (Uno/Mega/ESP32)."]),
                             classifier_hint=intent_res.classifier_hint,
                             notes=["Bu analiz kural tabanlidir; gercek derleme/calistirma "
                                    "dogrulamasi degildir."])

    def _build(self, board, code) -> dict:
        r = build_validator.validate(code, board)
        return {"ran": r.ran, "ok": r.ok, "tool": r.tool, "kind": r.kind,
                "returncode": r.returncode, "stderr": r.stderr, "note": r.note}
