"""5K siniflandiriciyi Android icin hafif JSON agirliklarina aktarir.

Kaynak : experiments_v2/exp_B_classification/model.pt  (SALT-OKUNUR; degistirilmez)
Mimari : Embedding(103->8) -> GRU(8->31) -> Linear(31->8), 4893 parametre
Cikti  : saf Python (torch/numpy OLMADAN) ile yuklenebilen JSON

Kullanim:
    python3 tools/export_classifier5k.py
    python3 tools/export_classifier5k.py --out /tmp/classifier5k.json

Yeni bir MODEL SURUMU yayimlamak icin (agirliklar DEGISMEZ, yalnizca surum
etiketi eklenir):
    python3 tools/export_classifier5k.py --out /tmp/classifier5k.json \
        --model-version 5K-1.1.0
    # Ardindan: model/manifest.schema.md adimlarini izleyip GitHub Release acin.

Kaynak model dosyasi DEGISTIRILMEZ; yalnizca okunur. `--model-version`
verilmezse cikti birebir ayni kalir (paket ici asset'in SHA-256'si sabittir).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]          # awu-gokturk-coder-5k/
_DEFAULT_MODEL = _ROOT / "experiments_v2" / "exp_B_classification" / "model.pt"
_DEFAULT_OUT = (_ROOT / "embedded_agent" / "android" / "app" / "src" / "main"
                / "assets" / "classifier5k.json")

FORMAT = "awugokturk-mcu-5k-lite-v1"
MODEL_NAME = "AwuGöktürk-Microcontroller:5K"
#: APK ile gelen (paket ici) modelin surumu. `model_updater.BUNDLED_MODEL_VERSION`
#: ile ayni olmalidir.
BUNDLED_MODEL_VERSION = "5K-1.0.0"


def export(model_path: Path, out_path: Path,
           model_version: str = "") -> Path:
    import torch  # yalnizca bu araçta gerekir

    ck = torch.load(str(model_path), map_location="cpu", weights_only=False)
    cfg = ck["config"]
    sd = ck["state_dict"]
    data = {
        "format": FORMAT,
        "model_name": MODEL_NAME,
        "config": {"vocab_size": int(cfg["vocab_size"]),
                   "emb": int(cfg["emb"]),
                   "hidden": int(cfg["hidden"])},
        "labels": list(cfg["labels"]),
        "vocab": list(ck["vocab"]),
        "emb": sd["emb.weight"].tolist(),
        "gru_weight_ih": sd["gru.weight_ih_l0"].tolist(),
        "gru_weight_hh": sd["gru.weight_hh_l0"].tolist(),
        "gru_bias_ih": sd["gru.bias_ih_l0"].tolist(),
        "gru_bias_hh": sd["gru.bias_hh_l0"].tolist(),
        "fc_weight": sd["fc.weight"].tolist(),
        "fc_bias": sd["fc.bias"].tolist(),
    }
    if model_version:
        # Yalnizca meta veri; agirliklar DEGISMEZ.
        data["model_version"] = str(model_version)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False),
                        encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=str(_DEFAULT_MODEL))
    ap.add_argument("--out", default=str(_DEFAULT_OUT))
    ap.add_argument("--model-version", default="",
                    help="Yalnizca yeni surum yayimlarken doldurun (or. 5K-1.1.0). "
                         "Bos birakilirsa cikti birebir ayni kalir.")
    a = ap.parse_args()
    p = export(Path(a.model), Path(a.out), model_version=a.model_version)
    v = ("  surum=" + a.model_version) if a.model_version else ""
    print(f"yazildi: {p}  ({p.stat().st_size} bayt){v}")


if __name__ == "__main__":
    main()
