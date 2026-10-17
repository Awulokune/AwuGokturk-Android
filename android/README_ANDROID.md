# AwuGöktürk — Android (çevrimdışı gömülü kodlama asistanı)

Tamamen **cihazda çalışan**, **internetsiz** kullanılabilen Android uygulaması.
Mevcut Python ajanı (`embedded_agent/awa_agent`) **yeniden yazılmadan** cihazda
çalıştırılır; Kotlin/Jetpack Compose yalnızca arayüz ve JSON köprüdür.

- Uygulama adı: **AwuGöktürk**
- Model adı: **AwuGöktürk-Microcontroller:5K**
- Paket kimliği: `com.awulokune.awugokturk`
- Slogan: **NO SAY CAVAS**
- Arayüz dili: Türkçe · Tema: koyu, turkuaz vurgulu
- Çevrimdışı öncelikli; **isteğe bağlı** model güncellemesi GitHub Releases'ten
  (bkz. §4.1)
- F-Droid yayın hazırlığı: bkz. **`embedded_agent/FDROID.md`** (metadata,
  lisans, uyumluluk bulguları ve engelleyici noktalar)

## Doğrulanan derleme sonucu

Bu teslimatta **hem debug hem release APK gerçekten derlendi** (temiz derleme):

| | debug | release (F-Droid'in derlediği) |
|---|---|---|
| Yol | `app/build/outputs/apk/debug/AwuGokturk-debug.apk` | `app/build/outputs/apk/release/AwuGokturk-release.apk` |
| Boyut | 42.892.370 bayt (~40,9 MiB) | **40.029.770 bayt (~38,2 MiB)** |
| SHA-256 | `a995122dc21dbdab603fe71b63ceaf84c34648dd3d0657e70317dfc55635ad43` | `30a2046421315f54ddc4fdf4504c00d3b97d1258e27ed240032b5494d61525f8` |
| İmza | Debug anahtarı | **İmzasız** (F-Droid kendi imzalar) |
| ABI | `arm64-v8a`, `x86_64` | `arm64-v8a`, `x86_64` |
| İzinler | `INTERNET` — **yalnızca isteğe bağlı model güncellemesi** için (bkz. §4.1); sohbet/kod üretimi hâlâ tamamen çevrimdışı | aynı |
| Simge | `@mipmap/ic_launcher` (adaptive, API 26+) + legacy PNG'ler | aynı |
| Araçlar | JDK 17 · AGP 8.5.2 · Gradle 8.7 · Kotlin 1.9.24 · Chaquopy 16.0.0 · **Python 3.13** | aynı |

> Release, debug'dan küçüktür çünkü `ui-tooling` yalnızca debug'a dahildir.
> **Bayt-bayt yeniden üretilebilir değildir** (aynı boyut, farklı SHA-256);
> neden ve çözüm notu: `embedded_agent/FDROID.md` §6.4.

> **Emülatörde gerçekten çalıştırıldı** (Android 14 / API 34 / x86_64, başsız, 1080×2340):
> `adb install` → **Success**, uygulama açıldı; boş sohbet ekranı, sohbette kod üretimi
> (kod kartı + AwuGuard), geçmiş paneli, Kod sekmesi ve Ayarlar gezildi.
> **5K modeli cihazda "yüklü (4893 parametre)"** olarak göründü ve **uçak modunda
> (`Active default network: none`)** yanıt üretmeye devam etti. Ayrıca
> **Model Güncellemeleri** ekranı gezildi: ağ açıkken **gerçek GitHub API** ile
> `no_published_model` dürüst sonucu, uçak modunda **ağ hatası** (yerel model
> bozulmadan) görüldü. Ekran görüntüleri: `screenshots/`. Betikler:
> `emulator_test.sh` (duman testi) ve `tools/verify_ui.sh` (arayüz turu + ekran
> görüntüleri). Fiziksel telefonda test edilmedi.
>
> **Release APK da ayrıca doğrulandı (Python 3.13 hedefiyle):** yerel test için
> debug anahtarıyla imzalanıp aynı emülatöre kuruldu; açıldı, **çökmedi**,
> sohbet turu çalıştı (`led yak` → kart-netleştirme yanıtı) ve Ayarlar'da
> **"5K sınıflandırıcı: yüklü (4893 parametre)"** ile **"Yüklü model sürümü
> 5K-1.0.0"** görüldü.

## 1. Arayüz ve logo (bu teslimatta yenilendi)

Uygulama artık bir **AI sohbet uygulaması** gibi davranır; Arduino kod üretimi bu
asistanın bir yeteneği olarak sunulur.

- **Logo:** `/home/aras/İndirilenler/file_00000000bab081f4a5b3ebf688d6a0a4.jpg`
  kaynağından üretildi (kaynak dosya **değiştirilmedi**). Üretim betiği:
  `tools/make_icons.py`.
  - Görselin ana konusu (beyaz çerçeve + harf serisi) **kırpılmadan** korunur.
  - Arka plan rengi (`#D94A25`) ve işaret rengi görselden **örneklenir** (uydurulmaz).
  - **Adaptive icon** (API 26+): `mipmap-anydpi-v26/ic_launcher.xml` +
    `ic_launcher_round.xml`, arka plan `drawable/ic_launcher_background.xml`,
    ön plan `mipmap-*/ic_launcher_foreground.png`.
  - Ön plan, çerçeve köşe yarıçapı **66dp güvenli daireye sığacak** biçimde
    ölçeklenir (32,6 ≤ 33) → yuvarlak/kare/squircle **tüm maskelerde okunaklı**.
  - Legacy `mipmap-*/ic_launcher.png` ve `ic_launcher_round.png` de üretilir.
  - Sohbet asistanı avatarı: `drawable-nodpi/ic_awu_avatar.png`;
    boş ekran/üst çubuk logosu: `drawable-nodpi/ic_awu_logo.png`.
- **Sohbet (ana ekran):** üst çubukta logo + "AwuGöktürk" + "Microcontroller:5K"
  alt başlığı, yeni sohbet ve geçmiş düğmeleri; boş durumda karşılama metni ve
  tıklanabilir örnek istemler; turkuaz→mavi degrade kullanıcı balonları, avatarlı
  asistan balonları; yazıyor göstergesi; klavye açıkken alt gezinme gizlenir ve
  giriş alanı klavyenin üstünde kalır.
- **Kod yanıtları** sohbette **kod kartı** olarak gösterilir: kart adı, dürüst
  "derleme/donanım testi: yapılmadı" satırı, sözdizimi vurgusu, **Kopyala** ve
  **Paylaş**, altında kompakt **AwuGuard** etiketi + açılabilir ayrıntı.
- **Geçmiş:** gerçek çok-oturumlu yerel geçmiş. "Yeni sohbet" mevcut sohbeti
  geçmişe alır; geçmiş panelinden oturum açılır/silinir. Eski tek-oturumlu
  `chat_history.json` varsa sessizce içe aktarılır.
- **Kod sekmesi** kod üretimine odaklanır; **Ayarlar** sade ve profesyoneldir.

---

## 2. Mimari ve neden bu mimari

Değerlendirilen yaklaşımlar:

| Yaklaşım | Değerlendirme | Seçim |
|---|---|---|
| Modeli doğrudan çalıştıran Python/yerel çalışma zamanı | **Chaquopy** (Android için CPython) ile mevcut `awa_agent` paketi aynen çalışır; sıfır kod çoğaltma | ✅ **seçildi** |
| Ajanı Kotlin'e port etmek | Kod üreticide 17 modül + şablon + guard; port etmek büyük ve **çatallanma (drift)** riski yüksek | ❌ |
| Ağırlıkları uyumsuz biçime zorla dönüştürmek | PyTorch Android'de ağırdır; model yine de çalışmalı | ❌ (bkz. §3 ile hafif ve **doğrulanmış** yol) |

**Bileşenler:**

```
Kotlin + Jetpack Compose (UI)
        │  JSON (org.json)
        ▼
PythonBridge.kt  ──(Chaquopy)──►  awa_agent.android_bridge
                                        │
                                        ├─ AwuGokturkAgent (sohbet + kod)
                                        ├─ intent_router / chat_knowledge
                                        ├─ code_generator / awu_guard
                                        ├─ classifier5k_lite  ← 5K (JSON ağırlık, torch YOK)
                                        └─ build_validator (cihazda araç yoksa "yapılmadı")
```

Paketleme: `android/app/build.gradle.kts` içindeki `copyPython` görevi,
`embedded_agent/awa_agent` paketini derleme anında `build/generated/python`
altına kopyalar (tek doğruluk kaynağı: gerçek paket). Böylece Python kodu
Android tarafında çoğaltılmaz.

## 3. Çevrimdışılık ve gizlilik

- **Çevrimdışı öncelikli:** sohbet, kod üretimi, AwuGuard ve kavram açıklamaları
  **hiçbir ağ bağlantısı gerektirmez**; uçak modunda çalışır.
- **`INTERNET` izni yalnızca isteğe bağlı model güncellemesi içindir** (bkz. §4.1).
  Uygulama hedef adresleri **izin listesiyle** sınırlıdır: yalnızca HTTPS ve yalnızca
  `github.com/Awulokune/AwuGokturk-Android` (API/asset yolları dahil).
- **Kendiliğinden indirme yoktur.** Otomatik kontrol (varsayılan açık, günde en fazla
  bir kez) yalnızca **küçük sürüm metadata'sı** ister; indirme ve etkinleştirme
  **her zaman kullanıcı onayı** gerektirir.
- Uzak API/bulut model **yoktur**; hesap girişi ve API anahtarı istenmez;
  uygulamaya gömülü token/parola **yoktur**.
- Analitik/reklam/izleme SDK'sı **eklenmemiştir**.
- Sohbet içeriği ve üretilen kod **hiçbir sunucuya gönderilmez**.
- Sohbet geçmişi yalnızca cihazda (`filesDir/chat_sessions.json`, çok oturumlu)
  tutulur ve Ayarlar → "Geçmişi temizle" ile kullanıcı tarafından silinir.
  Eski tek-oturumlu `chat_history.json` varsa sessizce içe aktarılır.
- 5K ağırlıkları ve model **APK içindedir**; güncelleme **zorunlu değildir**.

## 4. Model entegrasyonu (teknik)

**Model dosyası (değiştirilmez):** `experiments_v2/exp_B_classification/model.pt`
— Embedding(103→8) → GRU(8→31) → Linear(31→8), **4.893 parametre**, 8 sınıf.

Android'de PyTorch **yoktur**. Çözüm, uyumlu ve **doğrulanmış** bir dönüşüm yoludur:

1. `tools/export_classifier5k.py` — checkpoint'i **salt-okunur** açar ve
   ağırlıkları JSON'a yazar (`app/src/main/assets/classifier5k.json`, ~100 KB).
2. `awa_agent/classifier5k_lite.py` — aynı mimariyi **saf Python** (matematik
   kütüphanesi olmadan) uygular: karakter→embedding→GRU→lineer→softmax.
   GRU denklemi PyTorch ile birebir aynıdır (r/z/n kapıları, reset kapısı yeni
   duruma uygulanır).
3. Kotlin, asset'i `filesDir`'a kopyalar ve `set_model_path()` ile Python'a bildirir.

**Doğrulama:** `tests/test_android_bridge.py::test_lite_matches_torch`, aynı
girdilerde saf-Python çıkarımının PyTorch ile **aynı etiketi** ve **~5e-5'ten az**
olasılık farkını verdiğini kanıtlar. Modelin parametre sayısı JSON'dan yeniden
hesaplanır (4.893).

> 5K modeli yalnızca **Arduino Uno odaklı görev-türü ipucu** olarak kullanılır;
> kesin doğruluk kanıtı değildir. Arayüzde "5K: …" etiketi ile **ipucu** olarak
> gösterilir. Sohbet/kavram/genel bilgi yanıtları 5K olmadan, kural tabanlı
> yerel kaynaklardan üretilir.

### 4.1 Model güncelleme sistemi (GitHub Releases)

Model güncellemesi **uygulama güncellemesinden bağımsızdır**; uygulama yeniden
yüklenmeden model yükseltilebilir. Karar mantığının tamamı Python'dadır
(`awa_agent/model_updater.py`); Kotlin yalnızca arayüz ve ilerleme yoklaması yapar.

**Akış:** GitHub Releases → `awu-model-manifest.json` → doğrula → (onay) indir →
geçici dosya → **boyut + SHA-256 + yapı + fiili yükleme** doğrulaması → yedekle →
**atomik** etkinleştir → başarısızsa **otomatik geri dönüş**.

**Depolama:**

| Yol (`filesDir/`) | İçerik |
|---|---|
| `classifier5k.json` | paket içi model (**hiç üzerine yazılmaz**) |
| `awu_models/<sürüm>/<ad>` | etkin güncelleme |
| `awu_models/downloads/<ad>.part` | yarım indirme (açılışta temizlenir) |
| `awu_models/backup/` | geri dönüş yedeği |
| `awu_models/model_state.json` | kalıcı durum (atomik: tmp → `os.replace`) |

**Güvenlik:** HTTPS + izin listesi (her yönlendirme adımı doğrulanır), basit dosya adı
zorunluluğu, 8 MiB ağırlık sınırı + 8 MiB disk marjı, manifestte bildirilmeyen dosya
çalıştırılmaz, doğrulama geçmeden etkinleştirme yok, kilitlenmede yarım iş
etkinleştirilmez, gömülü anahtar yok, GitHub API limiti ayrı raporlanır.

**Arayüz:** Ayarlar → **Model Güncellemeleri**: yüklü sürüm/kaynak, en son uyumlu
sürüm, "Güncellemeleri kontrol et", yeni sürüm kartı (boyut, notlar, "İndir ve
yükselt"), yüzde + inen/toplam/kalan + iptal, sonuç (gerekiyorsa "geri alındı"),
"Önceki modele dön", otomatik kontrol anahtarı ve güvenlik listesi.

**Yayımlama:** `model/README.md` + `tools/make_model_manifest.py` (manifesti
**dosyadan türetir**, uydurmaz; bozuk dosya için manifest üretmez).

> **Dürüst durum:** `github.com/Awulokune/AwuGokturk-Android` deposunda **henüz yayımlanmış
> model Release'i yoktur**. Bu nedenle kontrol şu an dürüstçe
> `reason = "no_published_model"` döndürür. İndirme/doğrulama/geri dönüş zinciri
> **70 birim testinde** (sahte taşıma katmanı) uçtan uca doğrulanmıştır; **gerçek bir
> Release ile denenmemiştir** (yayımlanmış sürüm bulunmadığı için).

## 5. Derleme

Gereksinimler (root gerekmez; HOME içine kurulabilir):

- **JDK 17**
- **Android SDK**: `platform-tools`, `platforms;android-34`, `build-tools;34.0.0`
- **Python 3.13** (Chaquopy `buildPython`; hedef sürüm 3.13 — F-Droid derleme
  sunucusu Debian trixie'nin varsayılanıyla uyumlu. 3.8–3.13 arası desteklenir
  ama **hedef sürüm ile build Python AYNI minor sürüm olmalıdır**.)
- **Gradle 8.7** (AGP 8.5.2 / Kotlin 1.9.24 / Chaquopy 16.0.0)

```bash
cd android
export JAVA_HOME=$HOME/tools/jdk-17
export ANDROID_HOME=$HOME/Android/Sdk
export AWU_BUILD_PYTHON=$HOME/tools/python313/bin/python3
./build_apk.sh
# veya:
$HOME/tools/gradle-8.7/bin/gradle --no-daemon :app:assembleDebug \
    -PbuildPython="$AWU_BUILD_PYTHON"
```

Çıktı: `android/app/build/outputs/apk/debug/AwuGokturk-debug.apk`

### F-Droid / release derlemesi

F-Droid, uygulamayı **release** varyantından derler (`assembleRelease`).
Aynı yolu yerelde denemek için (çıktı **imzasızdır** — doğrusu budur):

```bash
cd android
$HOME/tools/gradle-8.7/bin/gradle --no-daemon :app:assembleRelease \
    -PbuildPython="$AWU_BUILD_PYTHON"
# çıktı: app/build/outputs/apk/release/AwuGokturk-release.apk
```

> `--offline` kullanmayın: `lintVitalAnalyzeRelease` Google Maven'dan
> `com.android.tools.lint:lint-gradle` indirir.

F-Droid yayın hazırlığı, uyumluluk bulguları ve **engelleyici noktalar**
(özellikle Chaquopy Python sürümü uyuşmazlığı) için bkz.
**`embedded_agent/FDROID.md`**.

### Kurulum (cihaz)

```bash
adb install -r android/app/build/outputs/apk/debug/AwuGokturk-debug.apk
```

## 6. Çevrimdışı kullanım

Kurulumdan sonra uygulama hiçbir ağ bağlantısı gerektirmez. Uçak modunda
açılabilir; sohbet, kod üretimi, AwuGuard ve kavram açıklamaları çalışır.

## 7. Testler

Python tarafı (mevcut testler + köprü/lite testleri) — bu teslimatta çalıştırıldı:

```bash
cd embedded_agent
python3 -m unittest discover -s tests        # 162 test — OK (1 atlandı: canlı ağ)
python3 -m unittest tests.test_android_bridge -v
python3 -m unittest tests.test_model_updater -v   # 70 test (10 zorunlu senaryo + güvenlik)
AWU_LIVE_UPDATE_TEST=1 python3 -m unittest \
    tests.test_model_updater.TestLiveGitHub -v    # gerçek GitHub API (opt-in)
python3 examples/demo.py                     # 19 senaryo — OK
```

Arayüz tarafı (emülatör, başsız):

```bash
cd android
ANDROID_HOME=$HOME/Android/Sdk ./emulator_test.sh \
    app/build/outputs/apk/debug/AwuGokturk-debug.apk     # duman testi
ANDROID_HOME=$HOME/Android/Sdk ./tools/verify_ui.sh \
    app/build/outputs/apk/debug/AwuGokturk-debug.apk     # arayüz turu + ekran görüntüleri
```

`tools/verify_ui.sh` boş sohbet, sohbette kod üretimi, geçmiş paneli, Kod sekmesi,
Ayarlar, **Model Güncellemeleri ekranı**, **gerçek GitHub kontrolü**, **uçak modunda
kontrol** ve başlatıcı ikonu adımlarını gezer ve `screenshots/` altına kaydeder.

## 8. Bilinen sınırlamalar

- **Genel amaçlı LLM değildir.** Sohbet kural tabanlıdır; yalnızca tanımlı
  başlıkları (CPU/RAM/GPU/OS, dijital I/O, ADC/PWM, I2C/SPI/UART, HTTP
  sunucu/istemci, temel matematik/fizik) ve elle doğrulanmış birkaç genel bilgiyi
  yanıtlar. Bilmediğinde **uydurmaz**.
- **Gerçek donanım derlemesi yapılmaz.** Cihazda `arduino-cli`/`avr-gcc` yoktur;
  derleme sonucu "yapılmadı" olarak etiketlenir. Fiziksel donanımda çalıştırma
  testi yapılmamıştır.
- **HTTP sunucusu (WebServer)** modülü desteklenmez; istekler gerekçeli reddedilir.
- Model **klasik ESP32** içindir; S2/S3/C3/S1/P4, ESP8266, RP2040 reddedilir.
- 5K sınıflandırıcı yalnızca **ipucudur**.
- **Örnek istemlerden ikisi (\"C++ kodumu açıkla.\", \"Pin 14'ün Uno'da ne olduğunu
  açıkla.\")** ajanın \"doğrulanmış bilgim yok\" yanıtını verir: ajanın kavram
  sözlüğü (CPU/RAM/…/ADC/PWM/I2C/SPI/UART, temel matematik/fizik) bu iki soruyu
  kapsamaz ve ajan uydurmaz. Pin bilgisi **kod üretimi yolunda** doğru kullanılır
  (örn. \"Arduino Uno'da pin 14'te LED yak.\" → A0/dijital-14 eşlemesi). Örnek
  istemler istekte belirtildiği için **aynen** korunmuştur; bu sınırlama ajanın
  Python katmanında olup bilinçli olarak **değiştirilmemiştir**.
- Ajanın sohbet mesajları kimi yerde **Türkçe diakritiksiz** yazılır
  (ör. \"Kod uretildi ve AwuGuard'dan gecti.\"). Bu, mevcut Python
  `response_handler` çıktısıdır; yeniden yazılmadı. Arayüz etiketleri ve boş
  durum/kod kartı/geçmiş metinleri doğru Türkçedir.
- APK, bu teslim ortamındaki araç kısıtları nedeniyle iki ABI ile derlenir
  (`arm64-v8a`, `x86_64`). Diğer ABI'ler için `abiFilters` güncellenebilir.
- **Model güncellemesi gerçek bir Release ile denenmedi:** depoda yayımlanmış model
  sürümü yoktur (`no_published_model`). İndirme → doğrulama → etkinleştirme → geri
  dönüş zinciri **70 birim testinde sahte taşıma katmanıyla** doğrulanmıştır; cihazda
  yalnızca "yayımlanmış sürüm yok" ve "ağ hatası" yolları görülmüştür. Gerçek indirme
  hızı/süresi ve "indirme sırasında uygulama öldürüldü" senaryosu **cihazda**
  denenmemiştir (ikincisi birim testleriyle kapsanır).
- **F-Droid derleme uyumu (Chaquopy/Python):** Chaquopy, derleme Python'unun
  magic number'ını hedef sürümle karşılaştırır. Hedef, F-Droid derleme
  sunucusuyla (Debian trixie / python3.13) uyumlu olacak şekilde **3.13**'e
  yükseltilmiş ve python3.13 ile derlenip cihazda test edilmiştir. Yerelde
  derlerken build Python **3.13** olmalıdır (`build_apk.sh` varsayılanı bunu
  kullanır). Tüm F-Droid bulguları için bkz. **`embedded_agent/FDROID.md`**.
