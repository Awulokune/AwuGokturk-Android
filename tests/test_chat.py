"""AwuGokturk sohbet katmani - regresyon testleri.

Calistirma (embedded_agent/ dizininden):
    python3 -m unittest tests.test_chat -v
    # veya tum paket: python3 -m unittest discover -s tests -v

Bagimlilik: yalnizca Python standart kutuphanesi. 5K modeli OPSIYONEL'dir; sohbet
katmani onu kullanmaz.
"""

from __future__ import annotations

import unittest

from awa_agent import intent_router as IR
from awa_agent.agent import AwuGokturkAgent

_TR_CHARS = "çğıöşüÇĞİÖŞÜ"


class TestChatRouting(unittest.TestCase):
    """Mesajlar dogru sohbet kategorisine yonlendirilmeli."""

    def _cat(self, text):
        return IR.route(text, use_classifier=False).category

    def test_greeting_category(self):
        self.assertEqual(self._cat("Merhaba"), IR.CAT_GREETING)
        self.assertEqual(self._cat("Nasılsın?"), IR.CAT_GREETING)

    def test_identity_category(self):
        self.assertEqual(self._cat("Sen kimsin?"), IR.CAT_IDENTITY)
        self.assertEqual(self._cat("Neler yapabilirsin?"), IR.CAT_IDENTITY)
        self.assertEqual(self._cat("Görevin ne?"), IR.CAT_IDENTITY)

    def test_general_chat_category(self):
        self.assertEqual(self._cat("Teşekkürler"), IR.CAT_GENERAL_CHAT)
        self.assertEqual(self._cat("Görüşürüz"), IR.CAT_GENERAL_CHAT)

    def test_concept_category(self):
        self.assertEqual(self._cat("Bilgisayar işlemcisi nasıl çalışır?"),
                         IR.CAT_CONCEPT)
        self.assertEqual(self._cat("CPU nedir?"), IR.CAT_CONCEPT)

    def test_embedded_coding_category(self):
        self.assertEqual(self._cat("Arduino Uno'da 7. pin'deki LED'i yak."),
                         IR.CAT_EMBEDDED)
        self.assertEqual(self._cat("ESP32'de GPIO 18'deki LED'i yakıp söndür."),
                         IR.CAT_EMBEDDED)

    def test_general_knowledge_category(self):
        self.assertEqual(self._cat("Fransa'nın başkenti neresi?"), IR.CAT_KNOWLEDGE)

    def test_creative_writing_category(self):
        self.assertEqual(self._cat("Bana basit bir bilim kurgu hikâyesi anlat."),
                         IR.CAT_CREATIVE)
        # duzeltme isareti (â) de normalize edilmeli: "hikâye" -> "hikaye"
        self.assertEqual(self._cat("Bana bir hikâye anlat."), IR.CAT_CREATIVE)

    def test_name_only_is_identity(self):
        self.assertEqual(self._cat("AwuGöktürk"), IR.CAT_IDENTITY)
        self.assertEqual(self._cat("AwuGöktürk Embedded Agent"), IR.CAT_IDENTITY)

    def test_unsupported_category(self):
        self.assertEqual(self._cat("Zürafaların ortalama ömrü kaç yıldır?"),
                         IR.CAT_UNSUPPORTED)


class TestChatResponses(unittest.TestCase):
    def setUp(self):
        self.ag = AwuGokturkAgent(use_classifier=False)

    # 1) Turkce selamlasma dogru calisir
    def test_greeting_turkish(self):
        r = self.ag.handle("Merhaba")
        self.assertEqual(r.status, "greeting")
        self.assertEqual(r.intent, IR.GREETING)
        self.assertIn("AwuGöktürk", r.message)
        self.assertTrue(any(c in r.message for c in _TR_CHARS))

    # 2) Kimlik sorusu unsupported OLMAMALI
    def test_identity_not_unsupported(self):
        r = self.ag.handle("Sen kimsin?")
        self.assertNotEqual(r.status, "unsupported")
        self.assertEqual(r.intent, IR.IDENTITY)
        self.assertIn("AwuGöktürk", r.message)
        self.assertIn("Arduino Uno", r.message)

    # 2b) Yetenek sorusu da kimlige gider ve kapsami anlatir
    def test_capabilities_answer_lists_boards(self):
        r = self.ag.handle("Neler yapabilirsin?")
        self.assertEqual(r.intent, IR.IDENTITY)
        self.assertIn("ESP32", r.message)
        self.assertNotEqual(r.status, "unsupported")

    # 3) Genel bilgisayar kavrami sorusu karta/module donusmez
    def test_computer_concept_not_board_question(self):
        r = self.ag.handle("Bilgisayar işlemcisi nasıl çalışır?")
        self.assertEqual(r.status, "info")
        self.assertEqual(r.intent, IR.CONCEPT)
        self.assertEqual(r.questions, [])
        self.assertIsNone(r.board)
        self.assertIsNone(r.code)
        low = r.message.lower()
        self.assertTrue("işlemci" in low or "islemci" in low)

    # 4) HTTP sunucusu ve istemcisi dogru aciklanir
    def test_http_server_vs_client_explained(self):
        r = self.ag.handle("Bir ESP32'de HTTP sunucusu ile HTTP istemcisi "
                           "arasındaki fark nedir?")
        self.assertEqual(r.status, "info")
        self.assertEqual(r.intent, IR.CONCEPT)
        low = r.message.lower()
        self.assertIn("sunucu", low)
        self.assertIn("istemci", low)
        self.assertNotEqual(r.status, "unsupported")
        self.assertIsNone(r.code)

    # 5) Desteklenmeyen soruda bilgi uydurulmaz
    def test_unknown_question_no_fabrication(self):
        r = self.ag.handle("Zürafaların ortalama ömrü kaç yıldır?")
        self.assertEqual(r.status, "unsupported")
        self.assertIsNone(r.code)
        # uydurma "sayi + yil" ifadesi URETILMEMELI
        self.assertIsNone(__import__("re").search(r"\d+\s*yıl", r.message),
                          "uydurma yas degeri uretildi")

    # 5b) Dogrulanmis genel bilgi (fact) kaynagindan yanit
    def test_general_knowledge_capital(self):
        r = self.ag.handle("Fransa'nın başkenti neresi?")
        self.assertEqual(r.status, "info")
        self.assertEqual(r.intent, IR.FACTS)
        self.assertIn("Paris", r.message)

    def test_unknown_concept_states_limit(self):
        r = self.ag.handle("Kuantum dolanıklık nedir?")
        self.assertEqual(r.status, "needs_info")
        self.assertTrue(r.questions)
        self.assertIn("doğrulanmış", r.message)

    # 6) Arduino kodlama istekleri mevcut Embedded Agent'a yonlendirilir
    def test_arduino_coding_uses_embedded_agent(self):
        prompt = ("Arduino Uno'da dahili LED'i bir saniye aralıklarla yakıp "
                  "söndüren kod yaz.")
        self.assertEqual(IR.route(prompt, use_classifier=False).category,
                         IR.CAT_EMBEDDED)
        r = self.ag.handle(prompt)
        self.assertEqual(r.status, "ok")
        self.assertIsNotNone(r.code)
        self.assertIn("1000", r.code)             # "bir saniye" -> 1000 ms
        self.assertIn("LED_PIN", r.code)

    # 7) Arduino Uno Wi-Fi uyumsuzlugu dogru sekilde reddedilir
    def test_uno_wifi_incompatibility_rejected(self):
        r = self.ag.handle("Arduino Uno'nun dahili Wi-Fi özelliğiyle internete bağlan.")
        self.assertEqual(r.status, "error")
        self.assertIsNone(r.code)
        self.assertEqual(r.board, "Arduino Uno R3")      # kart korunur
        joined = (r.message + " " + " ".join(m for _, m in r.guard)).lower()
        self.assertIn("uno", joined)
        self.assertTrue("wi-fi" in joined or "wifi" in joined)

    # 8) Turkce karakterler ciktida korunur (bozulma yok)
    def test_turkish_characters_preserved(self):
        for prompt in ["Merhaba", "Sen kimsin?", "RAM nedir?",
                       "Bir ESP32'de HTTP sunucusu ile HTTP istemcisi arasındaki fark nedir?"]:
            r = self.ag.handle(prompt)
            self.assertTrue(any(c in r.message for c in _TR_CHARS),
                            f"Turkce karakter yok: {prompt}")
            self.assertNotIn("Ã", r.message)          # mojibake
            self.assertNotIn("\ufffd", r.message)     # replacement char

    # 9) Sohbet katmani eklenince HTTP regresyonu bozulmaz
    def test_http_regression_still_holds(self):
        # 9a) ESP32 HTTP sunucusu -> istemci kodu URETILMEZ
        r1 = self.ag.handle("Klasik ESP32 ve Arduino framework kullanıyorum. "
                            "Wi-Fi üzerinden HTTP sunucusu oluştur.")
        self.assertEqual(r1.status, "unsupported")
        self.assertIsNone(r1.code)
        # 9b) ESP32 HTTP GET -> verilen SSID/sifre/URL korunur
        r2 = self.ag.handle("Klasik ESP32 kullanıyorum. SSID TEST_WIFI ve şifre "
                            "TEST_PASSWORD ile Wi-Fi'ye bağlanıp https://example.com "
                            "adresine HTTP GET isteği yap.")
        self.assertEqual(r2.status, "ok")
        self.assertIn("TEST_WIFI", r2.code)
        self.assertIn("TEST_PASSWORD", r2.code)
        self.assertIn("https://example.com", r2.code)


class TestReportedChatFixes(unittest.TestCase):
    """Bildirilen alti girdi icin kategori + yanit + davranis regresyonu."""

    def setUp(self):
        self.ag = AwuGokturkAgent(use_classifier=False)

    def _route(self, text):
        return IR.route(text, use_classifier=False)

    # 1) Selamlama + nezaket birlikte
    def test_greeting_with_politeness(self):
        p = "Merhaba AwuGöktürk! Bugün nasılsın?"
        self.assertEqual(self._route(p).category, IR.CAT_GREETING)
        r = self.ag.handle(p)
        self.assertEqual(r.status, "greeting")
        self.assertEqual(r.intent, IR.GREETING)
        self.assertNotEqual(r.status, "unsupported")
        self.assertTrue(any(c in r.message for c in _TR_CHARS))
        self.assertEqual(r.questions, [])          # kart/modul zorlamasi yok

    # 2) Genel bilgi kaynagi -> Paris
    def test_france_capital_paris(self):
        p = "Fransa'nın başkenti neresi?"
        self.assertEqual(self._route(p).category, IR.CAT_KNOWLEDGE)
        r = self.ag.handle(p)
        self.assertEqual(r.status, "info")
        self.assertIn("Paris", r.message)

    # 3) "Bilmiyorsan bile cevap vermeye calis" dogrulugu GEVSETMEZ
    def test_dont_relax_correctness_instruction(self):
        p = "Bilmiyorsan bile cevap vermeye çalış."
        self.assertEqual(self._route(p).category, IR.CAT_IDENTITY)
        r = self.ag.handle(p)
        self.assertNotEqual(r.status, "unsupported")
        low = r.message.lower()
        self.assertTrue("uydur" in low)             # uydurmayacagini soyler
        self.assertIsNone(r.code)
        self.assertEqual(r.questions, [])

    # 3b) Talimat sonrasi bilinmeyen soru yine uydurulmaz
    def test_after_relax_instruction_still_no_fabrication(self):
        r = self.ag.handle("Zürafaların ortalama ömrü kaç yıldır?")
        self.assertEqual(r.status, "unsupported")

    # 4) Yaratici yazarlik -> sabit, kisa ornek; LLM gibi sunulmaz
    def test_creative_writing_story(self):
        p = "Bana basit bir bilim kurgu hikâyesi anlat."
        self.assertEqual(self._route(p).category, IR.CAT_CREATIVE)
        r = self.ag.handle(p)
        self.assertEqual(r.status, "info")
        self.assertEqual(r.intent, IR.CREATIVE_WRITING)
        self.assertGreater(len(r.message), 120)     # anlamli bir ornek metin
        joined = (r.message + " " + " ".join(r.notes)).lower()
        self.assertIn("sabit", joined)              # genel LLM olmadigi belirtilir
        self.assertIsNone(r.code)

    # 5) Yalnizca ad yazilmasi -> kimlik + kisa tanitim
    def test_bare_name_identity(self):
        p = "AwuGöktürk"
        self.assertEqual(self._route(p).category, IR.CAT_IDENTITY)
        r = self.ag.handle(p)
        self.assertEqual(r.status, "info")
        self.assertEqual(r.intent, IR.IDENTITY)
        self.assertIn("AwuGöktürk", r.message)
        self.assertEqual(r.questions, [])

    # 5b) "AwuGöktürk Embedded Agent"
    def test_full_name_identity(self):
        p = "AwuGöktürk Embedded Agent"
        self.assertEqual(self._route(p).category, IR.CAT_IDENTITY)
        r = self.ag.handle(p)
        self.assertEqual(r.status, "info")
        self.assertEqual(r.intent, IR.IDENTITY)
        self.assertNotEqual(r.status, "unsupported")

    # 6) Sohbet/kimlik/nezaket yanitlari tekrar tekrar kart/modul sormaz
    def test_chat_responses_do_not_demand_board(self):
        for p in ["Merhaba", "Sen kimsin?", "Teşekkürler", "Görüşürüz",
                  "Bana basit bir bilim kurgu hikâyesi anlat."]:
            r = self.ag.handle(p)
            self.assertEqual(r.questions, [], f"gereksiz soru: {p}")
            self.assertNotIn("hedef kart", (r.message or "").lower())

    # 7) "bugun" icindeki "bug" yanlis debug tespiti yapmamali
    def test_bug_substring_not_false_debug(self):
        self.assertNotEqual(self._route("Bugün nasılsın?").intent, IR.DEBUG)
        self.assertEqual(self._route("Bugün nasılsın?").category, IR.CAT_GREETING)


if __name__ == "__main__":
    unittest.main(verbosity=2)
