"""Yayimlanacak model icin **manifest** uretir (GitHub Release ile birlikte).

Bu araç YALNIZCA gerçek bir agirlik dosyasindan manifest uretir; surum numarasi
ve indirme adresi UYDURULMAZ, siz verirsiniz. Manifestteki boyut ve SHA-256
degerleri dosyadan hesaplanir, mimari/tokenizer bilgileri dosyanin kendisinden
okunur. Dosya once `model_updater.structural_check` ile dogrulanir; bozuk bir
dosya icin manifest uretilmez.

Kullanim (embedded_agent/ dizininden):
    python3 tools/make_model_manifest.py \
        --artifact /tmp/classifier5k.json \
        --version 5K-1.1.0 \
        --release-url https://github.com/Awulokune/AwuGokturk-Android/releases/download/v5K-1.1.0/classifier5k.json \
        --notes "Sürüm notları…" \
        --out /tmp/awu-model-manifest.json

Ardindan iki dosyayi ayni Release'e yukleyin (bkz. model/README.md):
    awu-model-manifest.json   (varlik adi TAM olarak bu olmali)
    classifier5k.json        (manifest'in artifact.name alaniyla ayni ad)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from awa_agent import model_updater as MU  # noqa: E402

MANIFEST_ASSET_NAME = MU.MANIFEST_ASSET_NAME


def build(artifact: Path, version: str, release_url: str, notes: str,
          min_app: str, out: Path, model_name: str, artifact_name: str) -> dict:
    # 1) Dosya gerçekten geçerli bir 5K lite modeli mi?
    info = MU.structural_check(artifact)
    # 2) Manifesti yalnizca dosyadan türeyen degerlerle kur (uydurma yok).
    man = {
        "manifest_version": MU.MANIFEST_VERSION,
        "model_name": model_name,
        "model_version": version,
        "architecture": "lite-json-v1",
        "format": info["format"],
        "tokenizer_version": "char-vocab-%d" % info["vocab_size"],
        "vocab_size": info["vocab_size"],
        "labels": len(info["labels"]),
        "emb": info["emb"],
        "hidden": info["hidden"],
        "artifact": {
            "name": artifact_name,
            "url": release_url,
            "size": info["size"],
            "sha256": MU.sha256_file(artifact),
        },
        "min_app_version": min_app,
        "release_notes": notes,
    }
    # 3) Ürettigimiz manifesti kendi dogrulayicimizdan geçir.
    MU.validate_manifest(man)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    return man


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifact", required=True,
                    help="Yayimlanacak agirlik dosyasi (or. classifier5k.json)")
    ap.add_argument("--version", required=True, help="Model surumu (or. 5K-1.1.0)")
    ap.add_argument("--release-url", required=True,
                    help="Release varlik adresi (https://github.com/Awulokune/"
                         "AwuGokturk-Android/releases/download/<etiket>/<dosya>)")
    ap.add_argument("--notes", default="", help="Surum notlari")
    ap.add_argument("--min-app", default=MU.APP_VERSION_FALLBACK,
                    help="En az uyumlu uygulama surumu (varsayilan: %(default)s)")
    ap.add_argument("--model-name", default="AwuGöktürk-Microcontroller:5K")
    ap.add_argument("--out", default="/tmp/awu-model-manifest.json")
    a = ap.parse_args()

    art = Path(a.artifact)
    if not art.is_file():
        print("HATA: dosya bulunamadi: %s" % art, file=sys.stderr)
        return 2
    if art.name != Path(a.release_url).name:
        print("HATA: --release-url son parcasi (%s) ile dosya adi (%s) ayni olmali."
              % (Path(a.release_url).name, art.name), file=sys.stderr)
        return 2
    try:
        man = build(art, a.version, a.release_url, a.notes, a.min_app,
                    Path(a.out), a.model_name, art.name)
    except MU.UpdateError as e:
        print("HATA: %s -> %s" % (e.__class__.__name__, e), file=sys.stderr)
        return 1

    tag = a.release_url.split("/")[-2]
    print("manifest yazildi: %s" % a.out)
    print("  model_version : %s" % man["model_version"])
    print("  boyut         : %d bayt" % man["artifact"]["size"])
    print("  sha256        : %s" % man["artifact"]["sha256"])
    print()
    print("Yayimlama (GitHub Release varliklari):")
    print("  gh release create %s \"%s\" \"%s\" \\" % (tag, a.out, art))
    print("      --repo %s/%s --title \"%s %s\" --notes \"%s\""
          % (MU.GITHUB_OWNER, MU.GITHUB_REPO, man["model_name"], tag,
             a.notes.replace('"', '\\"')))
    print()
    print("NOT: Manifest varlik adi TAM olarak '%s' olmalidir." % MANIFEST_ASSET_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
