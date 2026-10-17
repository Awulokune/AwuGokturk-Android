# Model sürüm manifesti ve yayımlama kılavuzu

Bu klasör, **model güncelleme sisteminin** yayımlama (publisher) tarafını
belgeler. Uygulama tarafındaki tüketici mantığı
`awa_agent/model_updater.py` içindedir.

> **Güncel durum (dürüstlük notu):** `github.com/Awulokune/AwuGokturk-Android`
> deposunda **henüz yayımlanmış bir model Release'i yoktur.** Bu nedenle
> uygulamadaki "Güncellemeleri kontrol et" işlemi şu an
> `reason = "no_published_model"` sonucunu döndürür ve uygulamayla gelen model
> kullanılmaya devam eder. Aşağıdaki adımlar uygulandığında sistem gerçek
> Release'i bulup indirir; bu akış sahte verilerle (birim testlerinde) uçtan uca
> doğrulanmıştır.

## 1. Kavramlar

- **Uygulama sürümü** (`android/app/build.gradle.kts` → `versionName`) ile
  **model sürümü** (`manifest.model_version`) birbirinden **bağımsızdır**.
- Her model sürümü bir **GitHub Release**'tir ve içinde **iki varlık (asset)**
  bulunur:

  | Varlık adı | İçerik |
  | --- | --- |
  | `awu-model-manifest.json` | Sürüm manifesti (adı **birebir** bu olmalı) |
  | `manifest.artifact.name` (örn. `classifier5k.json`) | Ağırlık dosyası |

- Uygulama yalnızca bu iki adı bilir. Manifestte bildirilmeyen veya Release'te
  yayımlanmayan hiçbir dosya model olarak **çalıştırılmaz**.

## 2. Manifest şeması

```json
{
  "manifest_version": 1,
  "model_name": "AwuGöktürk-Microcontroller:5K",
  "model_version": "5K-1.1.0",
  "architecture": "lite-json-v1",
  "format": "awugokturk-mcu-5k-lite-v1",
  "tokenizer_version": "char-vocab-103",
  "vocab_size": 103,
  "labels": 8,
  "emb": 8,
  "hidden": 31,
  "artifact": {
    "name": "classifier5k.json",
    "url": "https://github.com/Awulokune/AwuGokturk-Android/releases/download/v5K-1.1.0/classifier5k.json",
    "size": 99663,
    "sha256": "«64 karakterlik hex»"
  },
  "min_app_version": "1.0.0",
  "release_notes": "Sürüm notları…"
}
```

Yukarıdaki blok bir **şablon**dur (`5K-1.1.0` örnek bir sürüm numarasıdır;
yayımlanmış bir sürümü göstermez). Gerçek manifest `make_model_manifest.py` ile
üretilir.

| Alan | Kural |
| --- | --- |
| `manifest_version` | Şu an `1`. Farklıysa sürüm reddedilir. |
| `model_version` | Sürüm karşılaştırması **sayısal parçalara** göre yapılır (`5K-1.10.0` > `5K-1.9.0`). |
| `architecture` | Desteklenen: `lite-json-v1`. Farklıysa **indirilmez**. |
| `format` | Desteklenen: `awugokturk-mcu-5k-lite-v1`. Farklıysa **indirilmez**. |
| `tokenizer_version` | Zorunlu; boş olamaz. |
| `vocab_size` / `labels` / `emb` / `hidden` | Dosyayla **birebir** tutmalı; tutmazsa reddedilir. |
| `artifact.name` | Yalnızca dosya adı (yol/`..` içeremez) ve Release'te yayımlanmış olmalı. |
| `artifact.url` | **HTTPS** + izinli ana bilgisayar + sabit depo yolu. Release varlık adresiyle uyuşmalı. |
| `artifact.size` | Pozitif; üst sınır 8 MiB. |
| `artifact.sha256` | 64 karakterlik hex. İndirilen dosyanın özetiyle karşılaştırılır. |
| `min_app_version` | Yüklü uygulama sürümünden büyükse sürüm **önerilmez** (uygulama güncellenmeli). |
| `release_notes` | Kullanıcıya gösterilir. |

## 3. Yeni model sürümü yayımlama adımları

```bash
cd embedded_agent

# 1) Ağırlık dosyasını (gerekirse sürüm etiketiyle) üret.
#    --model-version YALNIZCA meta veri ekler; ağırlıklar değişmez.
python3 tools/export_classifier5k.py \
    --out /tmp/classifier5k.json --model-version 5K-1.1.0

# 2) Manifesti üret (boyut + SHA-256 dosyadan hesaplanır, doğrulanır).
python3 tools/make_model_manifest.py \
    --artifact /tmp/classifier5k.json \
    --version 5K-1.1.0 \
    --release-url https://github.com/Awulokune/AwuGokturk-Android/releases/download/v5K-1.1.0/classifier5k.json \
    --notes "Sürüm notları" \
    --out /tmp/awu-model-manifest.json

# 3) İki varlığı aynı Release'e yükle (betik komutu yazdırır).
gh release create v5K-1.1.0 /tmp/awu-model-manifest.json /tmp/classifier5k.json \
    --repo Awulokune/AwuGokturk-Android --title "AwuGöktürk-Microcontroller:5K v5K-1.1.0" \
    --notes "Sürüm notları"
```

Kurallar:

- Etiket (`tag`) ile `model_version` aynı olmak **zorunda değildir**, ama
  karışıklığı önlemek için aynı tutulması önerilir.
- **Taslak (`draft`)** ve **ön sürüm (`prerelease`)** Release'ler uygulama
  tarafından **yok sayılır**.
- `awu-model-manifest.json` varlık adı **birebir** bu olmalıdır.
- Aynı Release'te birden fazla sürüm manifesti olamaz.

## 4. Yeni bir mimari yayımlanacaksa

`model_updater.SUPPORTED_ARCHITECTURES` / `SUPPORTED_FORMATS` sabitleri ve
`classifier5k_lite` çıkarım kodu **önce uygulamada** desteklenmelidir. Aksi
hâlde yeni sürüm kullanıcıya gösterilmez (yanlış/uyumsuz model indirilmez).

## 5. Testler

```bash
cd embedded_agent
python3 -m unittest tests.test_model_updater -v          # 68 test (sahte ağ)
AWU_LIVE_UPDATE_TEST=1 python3 -m unittest \
    tests.test_model_updater.TestLiveGitHub -v           # gerçek GitHub API
```
