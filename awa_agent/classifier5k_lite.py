"""5K siniflandiricisi icin saf-Python (torch/numpy'siz) cikarim.

NEDEN: Android/Chaquopy ortaminda PyTorch YOKTUR. Bu modul, gercek modelin
(`experiments_v2/exp_B_classification/model.pt`) agirliklarindan uretilen JSON
dosyasini okuyup GRU ileri hesabini saf Python ile yapar. Boylece model
cevrimdisi olarak cihazda calisir.

DOGRULUK: Bu, modelin mimarisini (Embedding(103->8) -> GRU(8->31) ->
Linear(31->8)) birebir uygular. Host'ta torch ile ayni etiketi/olasiliklari
verdigi `tests/test_android_bridge.py` icinde test edilir (torch varsa).

KAPSAM: Yalnizca gorev-turu IPUCU. Softmax olasiligi kesin dogruluk kaniti
DEGILDIR.

Agirlik dosyasi: `tools/export_classifier5k.py` ile uretilir
(varsayilan: android/app/src/main/assets/classifier5k.json).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Optional

from .classifier5k import LABEL_TO_INTENT, ClassifierResult

# JSON agirlik yolu: env > bridge tarafindan ayarlanan yol > paket ici varsayilan
MODEL_PATH: Optional[str] = os.environ.get("AWU_CLASSIFIER5K_JSON")


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def _matvec(W, x):
    """W: satir listesi (out x in), x: vektor. Sonuc: W @ x."""
    return [sum(w * xi for w, xi in zip(row, x)) for row in W]


class LiteClassifier:
    """JSON agirliklariyla calisan, torch'suz 5K siniflandirici."""

    def __init__(self, path: Optional[str] = None):
        self.available = False
        self.labels: list = []
        self._d = None
        self._stoi: dict = {}
        self._unk = 4
        p = path or MODEL_PATH
        if p:
            self._load(Path(p))

    def _load(self, path: Path):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            self._d = d
            self.labels = list(d["labels"])
            self._stoi = {c: i for i, c in enumerate(d["vocab"])}
            self._unk = self._stoi.get("<unk>", 4)
            self.available = True
        except Exception:
            self.available = False

    def predict(self, text: str) -> ClassifierResult:
        if not self.available:
            return ClassifierResult(False, note="5K (lite) agirliklari bulunamadi.")
        d = self._d
        H = int(d["config"]["hidden"])
        emb = d["emb"]
        w_ih, w_hh = d["gru_weight_ih"], d["gru_weight_hh"]
        b_ih, b_hh = d["gru_bias_ih"], d["gru_bias_hh"]

        ids = [self._stoi.get(ch, self._unk) for ch in text]
        if not ids:
            ids = [self._unk]

        h = [0.0] * H
        for tid in ids:
            x = emb[tid]
            gi = _matvec(w_ih, x)          # (3H,)  x katkisi
            gh = _matvec(w_hh, h)          # (3H,)  h katkisi
            nh = [0.0] * H
            for i in range(H):
                r = _sigmoid(gi[i] + b_ih[i] + gh[i] + b_hh[i])
                z = _sigmoid(gi[H + i] + b_ih[H + i] + gh[H + i] + b_hh[H + i])
                n = math.tanh(gi[2 * H + i] + b_ih[2 * H + i]
                              + r * (gh[2 * H + i] + b_hh[2 * H + i]))
                nh[i] = (1.0 - z) * n + z * h[i]
            h = nh

        raw = _matvec(d["fc_weight"], h)
        logits = [raw[i] + d["fc_bias"][i] for i in range(len(raw))]
        mx = max(logits)
        ex = [math.exp(v - mx) for v in logits]
        s = sum(ex)
        probs = [v / s for v in ex]
        k = max(range(len(probs)), key=lambda i: probs[i])
        label = self.labels[k]
        return ClassifierResult(
            True, label=label, intent_hint=LABEL_TO_INTENT.get(label, "concept"),
            probs={lab: round(probs[i], 4) for i, lab in enumerate(self.labels)},
            note="ipucu (kanit degil; lite cikarim)",
        )

    def param_count(self) -> int:
        if not self.available:
            return 0
        d = self._d
        n = len(d["emb"]) * len(d["emb"][0])
        n += len(d["gru_weight_ih"]) * len(d["gru_weight_ih"][0])
        n += len(d["gru_weight_hh"]) * len(d["gru_weight_hh"][0])
        n += len(d["gru_bias_ih"]) + len(d["gru_bias_hh"])
        n += len(d["fc_weight"]) * len(d["fc_weight"][0])
        n += len(d["fc_bias"])
        return n


_lite: Optional[LiteClassifier] = None


def set_model_path(path: str) -> None:
    """Bridge tarafindan cagrilir: JSON agirlik yolunu ayarlar ve onbellegi temizler."""
    global MODEL_PATH, _lite
    MODEL_PATH = path
    _lite = None


def get_classifier() -> LiteClassifier:
    global _lite
    if _lite is None:
        _lite = LiteClassifier()
    return _lite
