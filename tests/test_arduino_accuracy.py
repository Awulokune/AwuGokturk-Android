"""Gerekli Arduino doğruluk (accuracy) testleri.

Bu dosya, teslimatta AÇIKÇA istenen beş senaryoyu birebir doğrular. Testler
gerçek ajan davranışına göre yazılmıştır; hiçbiri "olmasını umduğumuz" değil,
ölçülen davranışı sabitler.

Senaryolar:
  1) "Arduino Uno'da pin 7'de LED'i 5 saniyede bir yakıp söndür."
     -> süre 5000 ms olmalı (500 ms ile KARIŞTIRILMAMALI).
  2) "Arduino Uno'da pin 14'te LED yak."
     -> A0 <-> dijital 14 eşlemesi bilinmeli; etiket ile numara ayrılmalı.
  3) "Arduino Uno'da Wi-Fi kullan."
     -> Uno'da dahili Wi-Fi YOK; donanım uydurulmamalı.
  4) "ESP32'de Wi-Fi HTTP GET isteği yap."
     -> gerçek destek kapsamı içinde yanıtlanmalı (eksik bilgi sorulmalı).
  5) Bilinmeyen özellik -> desteklenmiyor/dur; kod UYDURULMAMALI.

Çalıştırma (embedded_agent/ dizininden):
    python3 -m unittest tests.test_arduino_accuracy -v
Bağımlılık: yalnızca standart kütüphane + mevcut ajan (torch gerekmez).
"""

from __future__ import annotations

import unittest

from awa_agent import boards as B
from awa_agent.agent import AwuGokturkAgent


class TestScenario1_Duration(unittest.TestCase):
    """Süre yorumu: 5 saniye = 5000 ms; 500 ms ile karıştırılmamalı."""

    def setUp(self):
        self.ag = AwuGokturkAgent()

    def test_five_seconds_is_5000ms_not_500(self):
        r = self.ag.handle("Arduino Uno'da pin 7'de LED'i 5 saniyede bir yakıp söndür.")
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.board, "Arduino Uno R3")
        self.assertIsNotNone(r.code)
        code = r.code
        # Doğru süre: 5000 ms
        self.assertIn("INTERVAL_MS = 5000", code)
        # Klasik hata: 500 ms'e düşürmek. Bunun OLMADIĞINI açıkça doğrula.
        self.assertNotIn("INTERVAL_MS = 500;", code)
        self.assertNotIn("= 500;", code)
        # Pin kullanıcının verdiği gibi (7) korunmalı.
        self.assertIn("LED_PIN = 7", code)

    def test_500ms_stays_500ms(self):
        r = self.ag.handle("Arduino Uno'da pin 7'de LED'i 500 ms aralıkla yakıp söndür.")
        self.assertEqual(r.status, "ok")
        self.assertIn("INTERVAL_MS = 500", r.code)
        self.assertNotIn("INTERVAL_MS = 5000", r.code)

    def test_seconds_vs_milliseconds_differ(self):
        a = self.ag.handle("Arduino Uno'da pin 7'de LED'i 5 saniyede bir yakıp söndür.")
        b = self.ag.handle("Arduino Uno'da pin 7'de LED'i 500 ms aralıkla yakıp söndür.")
        self.assertIn("INTERVAL_MS = 5000", a.code)
        self.assertIn("INTERVAL_MS = 500", b.code)
        self.assertNotEqual(a.code, b.code)


class TestScenario2_AnalogLabelVsNumber(unittest.TestCase):
    """A0 <-> dijital 14 eşlemesi; etiket ('A0') ile numara ('14') ayrımı."""

    def setUp(self):
        self.ag = AwuGokturkAgent()
        self.uno = B.get_board("uno")

    def test_a0_maps_to_digital_14(self):
        a0 = self.uno.resolve_pin("A0")
        self.assertEqual(a0.number, 14)
        self.assertEqual(a0.kind, "analog")
        self.assertEqual(a0.raw, "A0")

    def test_pin_14_is_digital_not_analog_label(self):
        p14 = self.uno.resolve_pin("14")
        self.assertEqual(p14.number, 14)
        self.assertEqual(p14.kind, "digital")
        # Aynı fiziksel numara, farklı ifade: etiket vs numara karıştırılmamalı.
        self.assertNotEqual(p14.kind, self.uno.resolve_pin("A0").kind)

    def test_pin_14_request_preserves_number(self):
        r = self.ag.handle("Arduino Uno'da pin 14'te LED yak.")
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.board, "Arduino Uno R3")
        self.assertIsNotNone(r.code)
        self.assertIn("LED_PIN = 14", r.code)


class TestScenario3_UnoHasNoWifi(unittest.TestCase):
    """Arduino Uno'da dahili Wi-Fi yoktur; donanım uydurulmaz."""

    def setUp(self):
        self.ag = AwuGokturkAgent()

    def test_uno_wifi_is_refused(self):
        r = self.ag.handle("Arduino Uno'da Wi-Fi kullan.")
        self.assertEqual(r.status, "error")
        self.assertIsNone(r.code, "Wi-Fi için kod ÜRETİLMEMELİ (donanım yok)")
        low = r.message.lower()
        self.assertIn("wi-fi", low)
        self.assertIn("esp32", low)

    def test_uno_wifi_does_not_silently_switch_board(self):
        r = self.ag.handle("Arduino Uno'da Wi-Fi kullan.")
        # Kart sessizce ESP32'ye çevrilmemeli.
        self.assertEqual(r.board, "Arduino Uno R3")


class TestScenario4_Esp32HttpGetWithinScope(unittest.TestCase):
    """ESP32 Wi-Fi HTTP GET: gerçek destek kapsamı içinde yanıtlanır."""

    def setUp(self):
        self.ag = AwuGokturkAgent()

    def test_esp32_http_get_missing_info_asks(self):
        r = self.ag.handle("ESP32'de Wi-Fi HTTP GET isteği yap.")
        self.assertIn(r.status, ("needs_info", "ok"))
        self.assertEqual(r.board, "ESP32 (klasik, ESP32-D0WD/WROOM-32)")
        self.assertIsNotNone(r.code)
        self.assertIn("WiFi", r.code)
        self.assertIn("HTTPClient", r.code)
        # URL/SSID/şifre verilmedi -> SORULMALI (uydurulmamalı).
        self.assertEqual(r.status, "needs_info")
        self.assertTrue(any("url" in q.lower() for q in r.questions),
                        f"URL sorusu beklenirdi; sorular={r.questions}")

    def test_esp32_http_get_full_spec_preserves_values(self):
        r = self.ag.handle("Klasik ESP32'de https://example.com adresine HTTP GET isteği yap. "
                           "SSID TEST_WIFI şifre TEST_PASSWORD.")
        self.assertEqual(r.status, "ok")
        self.assertIsNotNone(r.code)
        self.assertIn("TEST_WIFI", r.code)
        self.assertIn("TEST_PASSWORD", r.code)
        self.assertIn("example.com", r.code)


class TestScenario5_UnknownFeatureNotFabricated(unittest.TestCase):
    """Bilinmeyen özellik: desteklenmiyor/dur; kod uydurulmaz."""

    def setUp(self):
        self.ag = AwuGokturkAgent()

    def test_out_of_scope_feature_is_unsupported(self):
        r = self.ag.handle("Arduino Uno'da makine öğrenmesi modeli eğit.")
        self.assertEqual(r.status, "unsupported")
        self.assertIsNone(r.code)
        self.assertIn("uydur", r.message.lower())

    def test_bogus_module_does_not_produce_code(self):
        r = self.ag.handle("Arduino Uno'da kuantum bilgisayar modülü kullan.")
        self.assertIn(r.status, ("unsupported", "needs_info"))
        self.assertIsNone(r.code, "Bilinmeyen modül için kod ÜRETİLMEMELİ")
        self.assertTrue(r.questions or r.status == "unsupported")


if __name__ == "__main__":
    unittest.main(verbosity=2)
