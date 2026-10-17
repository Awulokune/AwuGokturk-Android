#!/usr/bin/env python3
"""AwuGöktürk — kaynak görselden Android ikon/avatar kaynaklarını üretir.

KAYNAK GÖRSEL (DEĞİŞTİRİLMEZ, yalnızca okunur):
    /home/aras/İndirilenler/file_00000000bab081f4a5b3ebf688d6a0a4.jpg

Yapılan iş:
    * Görselin ana konusu (beyaz çerçeve + harf serisi) KORUNUR; kırpılmaz,
      yeniden çizilmez, başka bir görselle değiştirilmez.
    * Arka plan rengi görselden ÖRNEKLENİR (uydurulmaz) ve düz arka plan
      katmanı olarak kullanılır.
    * Şeffaf zeminli "foreground" katmanı, luminance tabanlı alfa ile çıkarılır.
    * Ölçek, konunun çerçevesi 66dp güvenli daireye SIĞACAK biçimde seçilir
      (kare köşe yarıçapı <= 33dp / 108dp tuval) → her maskede okunaklı.

Üretilenler:
    res/mipmap-*/ic_launcher.png            (legacy, kare)
    res/mipmap-*/ic_launcher_round.png      (legacy, yuvarlak)
    res/mipmap-*/ic_launcher_foreground.png (adaptive foreground, şeffaf)
    res/drawable-nodpi/ic_awu_logo.png      (uygulama içi logo karosu)
    res/drawable-nodpi/ic_awu_avatar.png    (asistan avatarı, yuvarlak)

Kullanım (android/ dizininden):
    python3 tools/make_icons.py
Gereksinim: Pillow, numpy (yalnızca üretim zamanı; uygulamaya girmez).
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

SRC = "/home/aras/İndirilenler/file_00000000bab081f4a5b3ebf688d6a0a4.jpg"
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "app", "src", "main", "res")

# Ölçek oranları: konu bbox GENİŞLİĞİNİN tuvale oranı.
# Foreground: 0.48 -> çerçeve köşe yarıçapı 32.6 <= 33 (66dp güvenli daire).
F_FOREGROUND = 0.48
F_LEGACY = 0.62   # legacy (maskesiz) ikonlar biraz daha dolgun olsun
F_ROUND = 0.60    # yuvarlak ikon: köşe yarıçapı 0.39*S < 0.5*S (daireye sığar)

DENSITIES = {
    "mdpi": 1.0,
    "hdpi": 1.5,
    "xhdpi": 2.0,
    "xxhdpi": 3.0,
    "xxxhdpi": 4.0,
}
LEGACY_BASE = 48          # mdpi legacy ikon boyutu (dp/px)
FOREGROUND_BASE = 108     # adaptive foreground tuvali (dp)


def load_mark() -> tuple[Image.Image, tuple[int, int, int], tuple[int, int, int]]:
    """Görseli okur; (şeffaf işaret, arka plan rengi, işaret rengi) döndürür."""
    if not os.path.isfile(SRC):
        sys.exit("HATA: kaynak görsel bulunamadı: %s" % SRC)

    im = Image.open(SRC).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    lum = a[:, :, 0] * 0.299 + a[:, :, 1] * 0.587 + a[:, :, 2] * 0.114

    # Arka plan: köşelerin medyanı (görselden örneklenir, uydurulmaz).
    corners = np.concatenate([
        a[0:40, 0:40].reshape(-1, 3), a[0:40, -40:].reshape(-1, 3),
        a[-40:, 0:40].reshape(-1, 3), a[-40:, -40:].reshape(-1, 3),
    ])
    bg = np.median(corners, axis=0)
    bg_rgb = tuple(int(round(v)) for v in bg)

    lum_bg = float(np.median(lum[0:40, 0:40]))
    lum_max = float(lum.max())
    if lum_max - lum_bg < 20:
        sys.exit("HATA: görselde belirgin konu bulunamadı (kontrast çok düşük).")

    # Gürültü tabanı: arka plan dalgalanmasını 0'a çeker, kenarları yumuşak tutar.
    t0 = lum_bg + 0.10 * (lum_max - lum_bg)
    t1 = lum_bg + 0.90 * (lum_max - lum_bg)
    alpha = np.clip((lum - t0) / max(1e-6, (t1 - t0)), 0.0, 1.0)

    ys, xs = np.nonzero(alpha > 0.5)
    if len(xs) == 0:
        sys.exit("HATA: konu maskesi boş.")
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1

    # İşaret rengi: çok parlak piksellerin medyanı (görsele sadık kalınır).
    bright = a[alpha > 0.92]
    mark_rgb = tuple(int(round(v)) for v in np.median(bright, axis=0)) if len(bright) else (255, 255, 255)

    al = (alpha[y0:y1, x0:x1] * 255.0).astype(np.uint8)
    rgb = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2] = mark_rgb
    mark = Image.fromarray(np.dstack([rgb, al]), "RGBA")
    return mark, bg_rgb, mark_rgb


def place(mark: Image.Image, canvas_px: int, frac: float, bg, shape: str) -> Image.Image:
    """İşareti, genişliği `frac`*tuval olacak biçimde ortalanmış yerleştirir."""
    c = canvas_px
    cv = Image.new("RGBA", (c, c), (0, 0, 0, 0))
    if bg is not None:
        cv.paste(Image.new("RGBA", (c, c), bg + (255,)), (0, 0))
    w = max(1, int(round(frac * c)))
    h = max(1, int(round(w * mark.size[1] / mark.size[0])))
    m = mark.resize((w, h), Image.LANCZOS)
    cv.alpha_composite(m, ((c - w) // 2, (c - h) // 2))

    if shape == "circle":
        mask = Image.new("L", (c, c), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, c - 1, c - 1], fill=255)
        out = Image.new("RGBA", (c, c), (0, 0, 0, 0))
        out.paste(cv, (0, 0), mask)
        return out
    if shape == "squircle":
        r = int(round(c * 0.26))
        mask = Image.new("L", (c, c), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, c - 1, c - 1], radius=r, fill=255)
        out = Image.new("RGBA", (c, c), (0, 0, 0, 0))
        out.paste(cv, (0, 0), mask)
        return out
    return cv


def save(img: Image.Image, folder: str, name: str) -> str:
    d = os.path.join(RES, folder)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    img.save(p, "PNG", optimize=True)
    return os.path.relpath(p, RES)


def main() -> None:
    mark, bg, mark_rgb = load_mark()
    print("Kaynak : %s" % SRC)
    print("Arka plan rengi (örneklenen): #%02X%02X%02X" % bg)
    print("İşaret rengi (örneklenen)   : #%02X%02X%02X" % mark_rgb)
    print("Konu boyutu (kırpılmadı)    : %dx%d" % mark.size)
    print()
    written = []

    for name, scale in DENSITIES.items():
        legacy = int(round(LEGACY_BASE * scale))
        written.append(save(place(mark, legacy, F_LEGACY, bg, "square"), "mipmap-" + name, "ic_launcher.png"))
        written.append(save(place(mark, legacy, F_ROUND, bg, "circle"), "mipmap-" + name, "ic_launcher_round.png"))
        fg = int(round(FOREGROUND_BASE * scale))
        written.append(save(place(mark, fg, F_FOREGROUND, None, "square"), "mipmap-" + name, "ic_launcher_foreground.png"))

    written.append(save(place(mark, 512, 0.62, bg, "squircle"), "drawable-nodpi", "ic_awu_logo.png"))
    written.append(save(place(mark, 256, 0.60, bg, "circle"), "drawable-nodpi", "ic_awu_avatar.png"))

    for w in written:
        print("  yazıldı: res/%s" % w)
    print("\nToplam %d dosya üretildi." % len(written))


if __name__ == "__main__":
    main()
