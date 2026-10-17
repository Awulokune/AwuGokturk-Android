"""Mevcut 5K gorev siniflandiricisina salt-okunur kopru.

Model: experiments_v2/exp_B_classification/model.pt
  Embedding(103->8) -> GRU(8->31) -> Linear(31->8), 4893 parametre, 8 sinif.

Bu model YALNIZCA Arduino Uno odakli veri seti uzerinde egitilmis bir
*gorev-turu* siniflandiricisidir. Cikti bir IPUCU'dur; kesin dogruluk kaniti
sayilmaz. Softmax olasiligi guven kaniti olarak kullanilmaz.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[2]
_MODEL_PATH = _ROOT / "experiments_v2" / "exp_B_classification" / "model.pt"

# Sinif -> genel gorev-turu eslemesi
LABEL_TO_INTENT = {
    "hata_bulma": "debug",
    "kavram_sorusu": "concept",
    "arduino_dijital": "code_generation",
    "arduino_analog": "code_generation",
    "kod_cikti": "concept",
    "sinif_uye_metot": "concept",
    "bellek_isaretci": "concept",
    "sinif_tanimlama": "concept",
}


@dataclass
class ClassifierResult:
    available: bool
    label: Optional[str] = None
    intent_hint: Optional[str] = None
    probs: dict = None
    note: str = ""


class UnoTaskClassifier:
    """5K siniflandiricisini yukler; dosya yoksa 'available=False' doner."""

    def __init__(self, path: Path = _MODEL_PATH):
        self.available = False
        self.labels: list[str] = []
        self._model = None
        self._stoi: dict = {}
        self._pad = 0
        self._torch = None
        self._load(path)

    def _load(self, path: Path):
        if not path.exists():
            return
        try:
            import torch
            import torch.nn as nn
        except Exception:  # pragma: no cover
            return

        class _Cls(nn.Module):
            def __init__(self, v, c, e, h):
                super().__init__()
                self.emb = nn.Embedding(v, e)
                self.gru = nn.GRU(e, h, batch_first=True)
                self.fc = nn.Linear(h, c)

            def forward(self, x, lengths):
                y, _ = self.gru(self.emb(x))
                idx = (lengths - 1).clamp(min=0)
                return self.fc(y[torch.arange(x.size(0)), idx])

        try:
            ck = torch.load(str(path), map_location="cpu", weights_only=False)
            cfg = ck["config"]
            self.labels = list(cfg["labels"])
            self._stoi = {c: i for i, c in enumerate(ck["vocab"])}
            self._pad = self._stoi.get("<pad>", 0)
            m = _Cls(cfg["vocab_size"], len(self.labels), cfg["emb"], cfg["hidden"])
            m.load_state_dict(ck["state_dict"])
            m.eval()
            self._model = m
            self._torch = torch
            self.available = True
        except Exception:
            self.available = False

    def predict(self, text: str) -> ClassifierResult:
        if not self.available:
            return ClassifierResult(False, note="5K siniflandirici bulunamadi/ yuklenemedi.")
        t = self._torch
        ids = [self._stoi.get(ch, self._stoi.get("<unk>", 4)) for ch in text]
        if not ids:
            ids = [self._stoi.get("<unk>", 4)]
        x = t.tensor([ids], dtype=t.long)
        lengths = t.tensor([len(ids)], dtype=t.long)
        with t.no_grad():
            logits = self._model(x, lengths)[0]
            probs = t.softmax(logits, dim=-1)
        k = int(probs.argmax())
        label = self.labels[k]
        return ClassifierResult(
            True, label=label, intent_hint=LABEL_TO_INTENT.get(label, "concept"),
            probs={lab: round(float(probs[i]), 4) for i, lab in enumerate(self.labels)},
            note="ipucu (kanit degil)")

    def param_count(self) -> int:
        if not self.available:
            return 0
        return sum(p.numel() for p in self._model.parameters())


_default = None


def reset() -> None:
    """Onbellegi temizler (ör. Android'de lite agirlik yolu degistiginde)."""
    global _default
    _default = None


def get_classifier():
    """torch varsa torch modeli; yoksa (ör. Android) saf-Python 'lite' modeli."""
    global _default
    if _default is None:
        c = UnoTaskClassifier()
        if not c.available:
            try:
                from . import classifier5k_lite
                lite = classifier5k_lite.get_classifier()
                if getattr(lite, "available", False):
                    c = lite
            except Exception:
                pass
        _default = c
    return _default
