"""AwuGokturk Embedded Agent - test paketi.

Calistirma (embedded_agent/ dizininden):
    python3 -m unittest discover -s tests -v
Bagimlilik: yalnizca Python standart kutuphanesi (unittest). torch OPSIYONEL'dir
(5K siniflandirici koprusu icin; yoksa ilgili test atlanir).
"""

from __future__ import annotations

import unittest

from awa_agent import boards as B
from awa_agent import intent_router as IR
from awa_agent import requirement_parser as RP
from awa_agent.agent import AwuGokturkAgent, analyze_conflicts


class TestBoardProfiles(unittest.TestCase):
    def test_boards_registered(self):
        keys = {b.key for b in B.list_boards()}
        self.assertIn("arduino_uno", keys)
        self.assertIn("arduino_mega2560", keys)
        self.assertIn("esp32", keys)

    def test_uno_pin_ranges(self):
        uno = B.get_board("uno")
        self.assertTrue(uno.resolve_pin("13").number == 13)
        self.assertEqual(uno.resolve_pin("A0").number, 14)
        # 20 Uno'da gecersiz
        ok, err, _ = uno.check_pin(uno.resolve_pin("20"), "digital_out")
        self.assertFalse(ok)

    def test_mega_pin_ranges_differ_from_uno(self):
        mega = B.get_board("mega2560")
        uno = B.get_board("uno")
        # Mega'da 20 gecerli; analog A0=54 (Uno'da 14)
        self.assertTrue(mega.check_pin(mega.resolve_pin("20"), "digital_out")[0])
        self.assertEqual(mega.resolve_pin("A0").number, 54)
        self.assertNotEqual(mega.resolve_pin("A0").number, uno.resolve_pin("A0").number)
        # Mega'da 44 PWM
        self.assertTrue(mega.check_pin(mega.resolve_pin("44"), "pwm")[0])

    def test_esp32_limits(self):
        esp = B.get_board("esp32")
        # 34 input-only -> cikis olamaz
        self.assertFalse(esp.check_pin(esp.resolve_pin("34"), "digital_out")[0])
        self.assertTrue(esp.check_pin(esp.resolve_pin("34"), "digital_in")[0])
        # 6 flash -> hic kullanilamaz
        self.assertFalse(esp.check_pin(esp.resolve_pin("6"), "digital_out")[0])
        # A0 etiketi ESP32'de yok
        self.assertFalse(esp.check_pin(esp.resolve_pin("A0"), "analog_in")[0])

    def test_negative_pin_rejected(self):
        uno = B.get_board("uno")
        ok, err, _ = uno.check_pin(B.PinSpec("-1", "digital", -1), "digital_out")
        self.assertFalse(ok)


class TestIntentRouter(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual(IR.route("Merhaba.", use_classifier=False).intent, IR.GREETING)

    def test_code_generation(self):
        r = IR.route("Arduino Uno'da 7. pindeki LED'i yak.", use_classifier=False)
        self.assertEqual(r.intent, IR.CODE_GENERATION)
        self.assertFalse(r.needs_board)

    def test_needs_board(self):
        r = IR.route("LED'i yak.", use_classifier=False)
        self.assertTrue(r.needs_board)

    def test_debug(self):
        r = IR.route("Bu kodda pin çakışması var mı?", use_classifier=False)
        self.assertEqual(r.intent, IR.DEBUG)

    def test_concept(self):
        r = IR.route("pinMode nedir?", use_classifier=False)
        self.assertEqual(r.intent, IR.CONCEPT)


class TestRequirementParser(unittest.TestCase):
    def test_single_pin_and_interval(self):
        req = RP.parse("Arduino Uno'da 7. pindeki LED'i 500 ms aralıklarla yakıp söndür.")
        self.assertEqual(req.actions[0].module, "led_blink")
        self.assertEqual(req.actions[0].params["interval_ms"], 500)
        self.assertEqual(req.actions[0].pins["led"].raw, "7")

    def test_negative_pin_captured(self):
        req = RP.parse("Arduino Uno'da -1 numaralı pindeki LED'i yak.")
        self.assertEqual(req.user_pins[0].number, -1)

    def test_pin_list(self):
        req = RP.parse("Arduino Uno'da 7 ve 8 numaralı pinlerde iki LED'i yak.")
        nums = sorted(p.number for p in req.user_pins)
        self.assertEqual(nums, [7, 8])

    def test_gpio_not_confused_with_esp32_word(self):
        req = RP.parse("ESP32'de GPIO 18'deki LED'i yak.")
        nums = [p.number for p in req.user_pins]
        self.assertEqual(nums, [18])   # "ESP32" -> 32 yanlis pin URETILMEMELI

    def test_unknown_sensor(self):
        req = RP.parse("Bilinmeyen bir sensörü oku.")
        self.assertTrue(req.unknown_modules)


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.ag = AwuGokturkAgent(use_classifier=False)

    def test_uno_led_on_pin_preserved(self):
        r = self.ag.handle("Arduino Uno'da 7. pindeki LED'i yak.")
        self.assertEqual(r.status, "ok")
        self.assertIn("LED_PIN = 7", r.code)
        self.assertTrue(r.build["ok"])

    def test_negative_pin_no_code(self):
        r = self.ag.handle("Arduino Uno'da -1 numaralı pindeki LED'i yak.")
        self.assertEqual(r.status, "error")
        self.assertIsNone(r.code)

    def test_invalid_pin_no_default(self):
        r = self.ag.handle("Arduino Uno'da 20 numaralı pindeki LED'i yak.")
        self.assertEqual(r.status, "error")
        self.assertIsNone(r.code)

    def test_mega_two_buttons(self):
        r = self.ag.handle("Arduino Mega'da iki butonla iki LED'i kontrol et.")
        self.assertEqual(r.status, "ok")
        self.assertTrue(r.assumptions)             # varsayilan pinler bildirildi
        self.assertTrue(r.build["ok"])

    def test_esp32_blink(self):
        r = self.ag.handle("ESP32'de GPIO 18'deki LED'i 500 ms aralıklarla yakıp söndür.")
        self.assertEqual(r.status, "ok")
        self.assertIn("LED_PIN = 18", r.code)
        self.assertTrue(r.build["ok"])

    def test_pwm_on_non_pwm_pin_rejected(self):
        r = self.ag.handle("Arduino Uno'da 7. pinde analogWrite ile PWM ver.")
        self.assertEqual(r.status, "error")

    def test_no_board_asks(self):
        r = self.ag.handle("A0 pinindeki potansiyometre değerini seri monitöre yazdır.")
        self.assertEqual(r.status, "needs_info")
        self.assertTrue(r.questions)

    def test_unknown_sensor_refused(self):
        r = self.ag.handle("Bilinmeyen bir sensörü oku.")
        self.assertEqual(r.status, "unsupported")
        self.assertIsNone(r.code)

    def test_unsupported_variant(self):
        r = self.ag.handle("ESP32-S3'te GPIO 5'teki LED'i yak.")
        self.assertEqual(r.status, "unsupported")

    def test_esp8266_unsupported(self):
        r = self.ag.handle("ESP8266 icin LED blink yaz.")
        self.assertEqual(r.status, "unsupported")

    def test_wifi_on_mega_refused(self):
        r = self.ag.handle("Arduino Mega'da Wi-Fi ile HTTP isteği yap.")
        self.assertEqual(r.status, "error")   # kart desteklemiyor -> kod yok
        self.assertIsNone(r.code)

    def test_wifi_http_needs_url(self):
        r = self.ag.handle("ESP32'de Wi-Fi üzerinden HTTP isteği yap.")
        self.assertEqual(r.status, "needs_info")
        self.assertTrue(any("URL" in q for q in r.questions))

    def test_servo_library_include(self):
        r = self.ag.handle("Arduino Uno'da 10. pinde servo motoru süpür.")
        self.assertEqual(r.status, "ok")
        self.assertIn("#include <Servo.h>", r.code)
        self.assertIn("Servo", r.libraries)


class TestDebug(unittest.TestCase):
    def test_pin_mode_conflict(self):
        code = "void setup(){ pinMode(7, OUTPUT); pinMode(7, INPUT); }"
        f = analyze_conflicts(None, code)
        self.assertTrue(any("cakismasi" in m for _, m in f))

    def test_debug_without_code_asks(self):
        ag = AwuGokturkAgent(use_classifier=False)
        r = ag.handle("Bu kodda pin çakışması var mı?")
        self.assertEqual(r.status, "needs_info")

    def test_debug_with_code(self):
        ag = AwuGokturkAgent(use_classifier=False)
        r = ag.handle("Arduino Uno'da bu kodda pin çakışması var mı?\n```\n"
                      "void setup(){ pinMode(7, OUTPUT); digitalRead(7); }\n```")
        self.assertTrue(any("cakismasi" in m or "kullaniliyor" in m for _, m in r.guard))


class TestHttpIntentAndParams(unittest.TestCase):
    """Regresyon: HTTP sunucu/istemci ayrimi ve parametre koruma."""

    def setUp(self):
        self.ag = AwuGokturkAgent(use_classifier=False)

    # 1) ESP32 HTTP sunucusu istegi istemci kodu URETMEZ
    def test_esp32_http_server_not_client(self):
        r = self.ag.handle("Klasik ESP32 ve Arduino framework kullanıyorum. "
                           "Wi-Fi üzerinden HTTP sunucusu oluştur.")
        self.assertEqual(r.status, "unsupported")
        self.assertIsNone(r.code)                       # istemci kodu URETILMEDI
        self.assertNotIn("HTTPClient.h", (r.code or ""))
        self.assertNotIn("http.GET", (r.code or ""))
        joined = " ".join(m for _, m in r.guard) + " " + r.message
        self.assertIn("SUNUCU", joined.upper())         # gerekce sunucu modulu

    # 2) verilen SSID/sifre/URL kodda korunur
    def test_esp32_http_get_preserves_credentials(self):
        r = self.ag.handle("Klasik ESP32 kullanıyorum. SSID TEST_WIFI ve şifre "
                           "TEST_PASSWORD ile Wi-Fi'ye bağlanıp https://example.com "
                           "adresine HTTP GET isteği yap.")
        self.assertEqual(r.status, "ok")
        self.assertIn("TEST_WIFI", r.code)
        self.assertIn("TEST_PASSWORD", r.code)
        self.assertIn("https://example.com", r.code)
        self.assertNotIn("YOUR_SSID", r.code)
        self.assertNotIn("YOUR_PASSWORD", r.code)

    # 3) verilen zorunlu parametreler icin gereksiz needs_info DONMEZ
    def test_no_spurious_needs_info_when_params_given(self):
        r = self.ag.handle("Klasik ESP32 kullanıyorum. SSID TEST_WIFI ve şifre "
                           "TEST_PASSWORD ile Wi-Fi'ye bağlanıp https://example.com "
                           "adresine HTTP GET isteği yap.")
        self.assertNotEqual(r.status, "needs_info")
        self.assertEqual(r.questions, [])
        self.assertTrue(r.build["ok"])   # host sozdizimi (gercek ESP32 derlemesi DEGIL)

    # 3b) sifre log/rapor alanlarinda maskelenir (kod blokunda kullanicinin istedigi deger kalir)
    def test_password_masked_in_diagnostics(self):
        r = self.ag.handle("Klasik ESP32 kullanıyorum. SSID TEST_WIFI ve şifre "
                           "TEST_PASSWORD ile Wi-Fi'ye bağlanıp https://example.com "
                           "adresine HTTP GET isteği yap.")
        diagnostics = " ".join(r.questions + r.notes + [r.message]
                               + [m for _, m in r.guard] + r.assumptions)
        self.assertNotIn("TEST_PASSWORD", diagnostics)

    # 4) Uno HTTP sunucusu: dogru uyumsuzluk gerekcesi, eksik-param sorusu YOK
    def test_uno_http_server_refused_with_correct_reason(self):
        r = self.ag.handle("Arduino Uno kullanıyorum. Wi-Fi ağına bağlanıp HTTP "
                           "sunucusu oluştur. Kartı değiştirme.")
        self.assertIn(r.status, ("error", "unsupported"))
        self.assertEqual(r.board, "Arduino Uno R3")     # kart korunur
        self.assertIsNone(r.code)                        # ESP32 kodu uretilmez
        joined = (r.message + " " + " ".join(m for _, m in r.guard)).lower()
        self.assertIn("uno", joined)
        self.assertTrue("wi-fi" in joined or "wifi" in joined)
        # uyumsuzluk gerekcesi, eksik URL/SSID/sifre sorularindan ONCE ve onlarin yerine
        self.assertEqual(r.questions, [])
        for q in r.questions:
            self.assertNotIn("URL", q)


class TestClassifierBridge(unittest.TestCase):
    def test_classifier_optional(self):
        from awa_agent import classifier5k
        clf = classifier5k.get_classifier()
        # Model yoksa da sistem calismali (available=False). Varsa sinif uretmeli.
        if clf.available:
            res = clf.predict("Arduino'da LED yak")
            self.assertIsNotNone(res.label)
            self.assertLessEqual(clf.param_count(), 5000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
