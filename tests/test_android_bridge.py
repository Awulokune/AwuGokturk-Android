"""Android kopru + 5K 'lite' (torch'suz) cikarim testleri.

Calistirma (embedded_agent/ dizininden):
    python3 -m unittest tests.test_android_bridge -v

Bu testler mevcut davranisi BOZMAZ; yeni yetenekleri dogrular. torch yoksa
parite testi atlanir (skip), ancak lite yukleme testi yine calisir.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from awa_agent import android_bridge as AB
from awa_agent import classifier5k_lite as LITE
from awa_agent import intent_router as IR

_ROOT = Path(__file__).resolve().parents[2]                 # awu-gokturk-coder-5k/
_MODEL = _ROOT / "experiments_v2" / "exp_B_classification" / "model.pt"


def _export_json(dst: Path) -> bool:
    try:
        import torch  # noqa: F401
    except Exception:
        return False
    if not _MODEL.exists():
        return False
    from tools.export_classifier5k import export
    export(_MODEL, dst)
    return True


class TestLiteClassifier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="awu_lite_")
        self.json_path = Path(self.tmp.name) / "classifier5k.json"
        self.have_json = _export_json(self.json_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_export_and_load(self):
        if not self.have_json:
            self.skipTest("torch/model yok; JSON uretilemedi")
        LITE.set_model_path(str(self.json_path))
        c = LITE.get_classifier()
        self.assertTrue(c.available)
        self.assertEqual(c.param_count(), 4893)
        self.assertEqual(len(c.labels), 8)
        r = c.predict("pinMode(13, OUTPUT);")
        self.assertTrue(r.available)
        self.assertIsNotNone(r.label)
        self.assertEqual(len(r.probs), 8)

    def test_lite_matches_torch(self):
        if not self.have_json:
            self.skipTest("torch/model yok; karsilastirma yapilamaz")
        import torch
        ck = torch.load(str(_MODEL), map_location="cpu", weights_only=False)
        cfg, sd, vocab = ck["config"], ck["state_dict"], ck["vocab"]
        stoi = {c: i for i, c in enumerate(vocab)}

        def torch_probs(text):
            ids = [stoi.get(ch, stoi.get("<unk>", 4)) for ch in text] or [4]
            x = torch.tensor([ids])
            L = torch.tensor([len(ids)])
            emb = torch.nn.Embedding(cfg["vocab_size"], cfg["emb"]); emb.weight.data = sd["emb.weight"]
            gru = torch.nn.GRU(cfg["emb"], cfg["hidden"], batch_first=True)
            gru.weight_ih_l0.data = sd["gru.weight_ih_l0"]
            gru.weight_hh_l0.data = sd["gru.weight_hh_l0"]
            gru.bias_ih_l0.data = sd["gru.bias_ih_l0"]
            gru.bias_hh_l0.data = sd["gru.bias_hh_l0"]
            fc = torch.nn.Linear(cfg["hidden"], len(cfg["labels"]))
            fc.weight.data = sd["fc.weight"]; fc.bias.data = sd["fc.bias"]
            with torch.no_grad():
                y, _ = gru(emb(x))
                logits = fc(y[torch.arange(1), (L - 1).clamp(min=0)])
                return torch.softmax(logits, -1)[0].tolist()

        LITE.set_model_path(str(self.json_path))
        c = LITE.get_classifier()
        labels = c.labels
        samples = ["pinMode(13, OUTPUT); digitalWrite(13, HIGH);",
                   "Uno'da 7. pindeki LED'i yak",
                   "RAM nedir, aciklar misin?",
                   "kodumda hata var, nasil duzeltirim?"]
        for t in samples:
            tp = torch_probs(t)
            lp = [c.predict(t).probs[l] for l in labels]
            torch_label = labels[tp.index(max(tp))]
            lite_label = c.predict(t).label
            self.assertEqual(torch_label, lite_label, f"etiket farkli: {t}")
            self.assertLess(max(abs(a - b) for a, b in zip(tp, lp)), 1e-3,
                            f"olasilik farki buyuk: {t}")


class TestAndroidBridge(unittest.TestCase):
    def _j(self, s):
        return json.loads(s)

    def test_app_info_identity(self):
        d = self._j(AB.app_info())
        self.assertEqual(d["app_name"], "AwuGöktürk")
        self.assertEqual(d["model_name"], "AwuGöktürk-Microcontroller:5K")
        self.assertEqual(d["package_id"], "com.awulokune.awugokturk")
        self.assertEqual(d["slogan"], "NO SAY CAVAS")
        keys = {b["key"] for b in d["boards"]}
        self.assertEqual(keys, {"arduino_uno", "arduino_mega2560", "esp32"})

    def test_handle_greeting(self):
        d = self._j(AB.handle("Merhaba"))
        self.assertEqual(d["status"], "greeting")
        self.assertEqual(d["category"], IR.CAT_GREETING)

    def test_handle_general_knowledge(self):
        d = self._j(AB.handle("Fransa'nın başkenti neresi?"))
        self.assertEqual(d["category"], IR.CAT_KNOWLEDGE)
        self.assertIn("Paris", d["message"])

    def test_handle_bare_name_identity(self):
        d = self._j(AB.handle("AwuGöktürk"))
        self.assertEqual(d["category"], IR.CAT_IDENTITY)
        self.assertEqual(d["status"], "info")

    def test_handle_uno_led_code(self):
        d = self._j(AB.handle("Arduino Uno'da 7. pin'deki LED'i 500 ms aralikla yakip sondur."))
        self.assertEqual(d["board"], "Arduino Uno R3")
        self.assertIsNotNone(d["code"])
        self.assertIn("pinMode", d["code"])
        self.assertIn("digitalWrite", d["code"])
        self.assertEqual(d["intent"], IR.CODE_GENERATION)
        # build: cihazda/ana makinede toolchain olabilir; alan her zaman var
        self.assertIn("build", d)

    def test_handle_esp32_http_get(self):
        d = self._j(AB.handle("Klasik ESP32'de https://example.com adresine HTTP GET istegi yap. "
                              "SSID TEST_WIFI sifre TEST_PASSWORD.", "esp32"))
        self.assertEqual(d["board"], "ESP32 (klasik, ESP32-D0WD/WROOM-32)")
        self.assertIsNotNone(d["code"])
        self.assertIn("WiFi", d["code"])
        self.assertIn("TEST_WIFI", d["code"])

    def test_handle_uno_wifi_refused(self):
        d = self._j(AB.handle("Arduino Uno'da Wi-Fi kullanarak internete baglan."))
        self.assertEqual(d["status"], "error")
        self.assertIsNone(d["code"])

    def test_handle_unsupported_no_fabrication(self):
        d = self._j(AB.handle("Zürafaların ortalama ömrü kaç yıldır?"))
        self.assertEqual(d["status"], "unsupported")
        self.assertIsNone(d["code"])

    def test_route_endpoint(self):
        d = self._j(AB.route("CPU nedir?"))
        self.assertEqual(d["category"], IR.CAT_CONCEPT)

    def test_identity_names_model_correctly(self):
        # ADLANDIRMA KURALI: asistan "AwuGöktürk", model "AwuGöktürk-Microcontroller:5K".
        d = self._j(AB.handle("AwuGöktürk"))
        self.assertEqual(d["category"], IR.CAT_IDENTITY)
        self.assertIn("AwuGöktürk-Microcontroller:5K", d["message"])
        # Model, "Embedded Agent" olarak ADLANDIRILMAMALI.
        self.assertNotIn("Embedded Agent", d["message"])

    def test_model_name_is_not_embedded_agent(self):
        info = self._j(AB.app_info())
        self.assertEqual(info["model_name"], "AwuGöktürk-Microcontroller:5K")
        self.assertNotEqual(info["model_name"], "AwuGöktürk Embedded Agent")


if __name__ == "__main__":
    unittest.main(verbosity=2)
