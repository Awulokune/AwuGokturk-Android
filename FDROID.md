# AwuGöktürk — F-Droid yayın hazırlığı

Bu belge, AwuGöktürk Android uygulamasının **F-Droid resmî deposunda
yayımlanmaya** hazırlanması sırasında yapılanları, doğrulanan/doğrulanmayan
noktaları ve **sizin yapmanız gereken adımları** açıklar.

> Slogan: **NO SAY CAVAS**

---

## 1. Özet (dürüst durum)

| Konu | Durum |
|---|---|
| Uygulama kimliği `com.awulokune.awugokturk` | **Değiştirilmedi** |
| Sürüm `1.0.0` / `versionCode 1` | **Değiştirilmedi** |
| Model ağırlıkları APK içinde (`assets/classifier5k.json`) | **Korundu** (99.663 bayt) |
| Çevrimdışı çalışma | **Korundu** (sohbet/kod üretimi internetsiz) |
| Lisans dosyası (GPL-3.0) | **Eklendi** (`LICENSE`, depo kökü) |
| F-Droid metadata (fdroiddata + `.fdroid.yml`) | **Hazırlandı** |
| Kaynak-içi açıklama/görsel (fastlane tr-TR + en-US) | **Hazırlandı** |
| Gradle wrapper (F-Droid Gradle sürümünü buradan okur) | **Eklendi** |
| Release derlemesi (F-Droid'in derlediği varyant) | **Yerelde başarılı**, imzasız, 40.029.770 bayt |
| Mevcut testler | **Geçti** (bkz. §6) |
| Kaynak kodun GitHub'a itilmesi | **YAPILMADI — sizin yapmanız gerekir** |
| Sürüm etiketi (tag) oluşturma | **YAPILMADI — sizin yapmanız gerekir** |
| Chaquopy Python sürümü / F-Droid derleme sunucusu | **UYUMLU — 3.13'e yükseltildi ve cihazda test edildi (§5.1)** |

**Önemli:** F-Droid'in derleme sunucusu (Debian trixie / python3.13) ile projenin
Python hedefi artık **uyumludur** (3.13). Kalan engeller kaynak kodun itilmesi,
sürüm etiketi ve metadata'daki `commit` alanıdır (§5).

---

## 2. F-Droid "kaynaktan derleme" kuralları — kontrol sonuçları

F-Droid, uygulamayı **kaynak koddan kendisi derler**. Bunun için gerekenler
ve bizim durumumuz:

| Kural | Durum | Açıklama |
|---|---|---|
| Tüm bağımlılıklar özgür yazılım olmalı | ✅ | Kotlin stdlib (Apache-2.0), AndroidX/Compose (Apache-2.0), kotlinx-coroutines (Apache-2.0), **Chaquopy 16.0.0 (MIT)**, CPython çalışma zamanı (PSF) |
| Özel mülk SDK yasak (Play Services, Firebase, reklam/izleme) | ✅ | Hiçbiri yok |
| Önceden derlenmiş ikililer güvenilir kaynaktan gelmeli | ✅ | Chaquopy artefaktları **Maven Central**'da (üçü de HTTP 200) |
| Uygulamanın kendisi özgür lisanslı olmalı | ✅ | **GPL-3.0** (`LICENSE` eklendi; GitHub deposu da GPL-3.0) |
| `debuggable`/`testOnly` olmamalı | ✅ | Release APK'da yok (doğrulandı) |
| Derleme ağ üzerinden bağımlılık indirebilir (izinli) | ✅ | Maven Central + Google Maven (izinli kaynaklar) |
| Kaynak depo herkese açık olmalı | ⚠️ | GitHub deposu var ama **içi boş** (yalnız LICENSE + README) |
| Sürüm etiketi (tag) bulunmalı | ⚠️ | Şu an **hiç tag yok** |

### 2.1 F-Droid derlemesinin mekaniği (kaynaktan doğrulandı)

`fdroidserver` (master) kaynağından doğrulanan davranışlar:

- Derleme görevi: **`assembleRelease`** (`gradle: [yes]`).
- `fdroidserver` **`gradlew` ve `gradlew.bat` dosyalarını SİLER**; Gradle
  sürümünü `gradle/wrapper/gradle-wrapper.properties` içindeki
  `distributionUrl` satırından okur (`gradlew-fdroid` aracı) ve o Gradle
  sürümünü F-Droid'in Gradle şeffaflık günlüğünden indirir.
  → **Bu dosya depoda bulunmak ZORUNDADIR.** (Eklendi; AGP 8.5.2 → Gradle 8.7.)
- APK aranırken varsayılan olarak `<subdir>/build/outputs/apk/release`
  taranır. Bizim APK `app` modülünde olduğu için otomatik bulma **başarısız
  olur**; bu yüzden metadata'da `output:` alanı **zorunludur.**
- `gradle-wrapper.jar`, `gradlew`, `gradlew.bat` tarayıcıda "izinli ikili"
  listesindedir (sorun sayılmaz).
- `local.properties` dosyasını F-Droid kendi yazar (`sdk.dir`).
  → Bu dosyayı **depoya koymayın** (`.gitignore`'a eklendi).

---

## 3. Eklenen / değiştirilen dosyalar

**Yeni dosyalar**

| Dosya | Amaç |
|---|---|
| `LICENSE` (depo kökü) | GPL-3.0 tam metin (GitHub deposundakiyle aynı) |
| `.gitignore` (depo kökü) | Derleme çıktıları ve `local.properties` depoya girmesin |
| `.fdroid.yml` (depo kökü) | Kaynak-içi F-Droid metadata (`fdroid build` için) |
| `embedded_agent/fdroid/metadata/com.awulokune.awugokturk.yml` | fdroiddata'ya gönderilecek metadata (kopya) |
| `android/gradle/wrapper/gradle-wrapper.properties` | F-Droid Gradle sürümünü buradan okur |
| `android/gradle/wrapper/gradle-wrapper.jar` | Standart wrapper (izinli ikili) |
| `android/gradlew`, `gradlew.bat` | Geliştirici kolaylığı (F-Droid siler) |
| `android/fastlane/metadata/android/tr-TR/…` | Türkçe ad/kısa+uzun açıklama/changelog |
| `android/fastlane/metadata/android/en-US/…` | İngilizce metinler + 4 ekran görüntüsü |
| `embedded_agent/FDROID.md` | Bu belge |

**Değiştirilen dosyalar**

| Dosya | Değişiklik |
|---|---|
| `android/app/build.gradle.kts` | Chaquopy hedefi **3.13** (F-Droid sunucusuyla uyumlu); `buildPython` verilmezse `python3` kullanılsın (F-Droid/CI) |
| `android/build_apk.sh` | Varsayılan `buildPython` → `$HOME/tools/python313/bin/python3` |
| `android/README_ANDROID.md` | Release derleme bölümü, F-Droid işaretçisi, güncel APK tablosu |

> Değiştirilmeyenler: model ağırlıkları, eğitim verisi, uygulama kimliği,
> sürüm numaraları, arayüz, Python ajanı mantığı, AndroidManifest izinleri.

---

## 4. F-Droid'e özel doğrulanan ayrıntılar

### 4.1 Lisanslar

- **Uygulama:** GPL-3.0-only (GitHub API: `spdx_id: GPL-3.0`).
- **Chaquopy 16.0.0:** MIT (`com.chaquo.python*` POM'larında doğrulandı).
- **CPython çalışma zamanı:** PSF lisansı (özgür).
- **AndroidX / Jetpack Compose / Kotlin / coroutines:** Apache-2.0.
- **Model ağırlıkları:** Proje GPL-3.0 olduğundan ağırlıklar da bu lisans
  kapsamındadır. Ağırlıklar **yeniden üretilebilir**:
  `tools/export_classifier5k.py`, `experiments_v2/exp_B_classification/model.pt`
  dosyasından **bayt-bayt aynı** JSON'u üretir (daha önce doğrulanmıştı).
  → F-Droid incelemesi için `model.pt` ve eğitim betikleri de depoda
  bulunmalıdır (bkz. §5.6).

### 4.2 İnternet izni (dürüstlük)

`INTERNET` izni **yalnızca** isteğe bağlı "model güncellemesi" özelliği
içindir (GitHub Releases'ten sürüm kontrolü/indirme, kullanıcı onayıyla).
Sohbet ve kod üretimi tamamen çevrimdışıdır. Analitik/reklam/izleme yoktur.

- F-Droid açısından bu bir "anti-feature" **değildir** (GitHub özgür bir
  hizmettir; `NonFreeNet` uygulanmaz).
- **Dikkat:** Uygulama çalışma zamanında **model ağırlığı** indirir. Ağırlıklar
  veri olup kod değildir, ancak F-Droid inceleyicisi "çalışma zamanında
  yürütülebilir içerik indirme" konusunda soru sorabilir. Bu, §5.7'de
  "inceleme noktası" olarak listelenmiştir.

### 4.3 ABI kapsamı

Yalnızca `arm64-v8a` ve `x86_64` derlenir (APK boyutunu sınırlamak için).
**32 bit ARM (`armeabi-v7a`) cihazlar uygulamayı kuramaz.** F-Droid bunu kabul
eder ama o cihazlarda "uyumlu değil" görünür. (Bloklayıcı değil.)

---

## 5. Engelleyici ve eksik noktalar (sizin aksiyonunuz)

### 5.1 ✅ ÇÖZÜLDÜ — Chaquopy Python sürümü 3.13'e yükseltildi

**Eski bulgu:** Chaquopy, derleme makinesindeki Python'un "magic number"ını hedef
sürümle karşılaştırır ve uyuşmazsa derlemeyi **durdurur**
(`chaquopy/pyc.py` → `check_magic`). Proje hedefi **Python 3.11** (magic 3495)
idi; F-Droid derleme sunucusu **Debian trixie** (`Dockerfile`/`Vagrantfile`)
olup varsayılan Python **3.13**'tür (magic 3571). Debian trixie'de **python3.11
paketi yoktur** (`sources.debian.org`: yalnız `3.11.2-6+deb12u8` = bookworm).
Bu yüzden derleme `magic number is 3571; expected 3495` hatasıyla duruyordu.

**Uygulanan çözüm:** `chaquopy { defaultConfig { version = "3.13" } }` yapıldı;
`build_apk.sh` ve belgeler 3.13'e güncellendi.

**Doğrulama (yapıldı):**

| Kontrol | Sonuç |
|---|---|
| Temiz `assembleRelease` + `assembleDebug` (python3.13 ile) | **BUİLD SUCCESSFUL** |
| `.pyc` magic (app.imy içinde) | **3571** (= 3.13) ✔ |
| APK içindeki paylaşımlı kütüphane | `libpython3.13.so` ✔ |
| `assets/classifier5k.json` | kaynakla **bayt-bayt aynı** ✔ |
| Emülatörde kurulum + açılış | **Success**, çökme yok ✔ |
| Sohbet turu (Python 3.13 ajanı) | `led yak` → doğru kart-netleştirme yanıtı ✔ |
| Ayarlar | **"5K sınıflandırıcı: yüklü (4893 parametre)"**, sürüm **1.0.0**, çevrimdışı ✔ |
| Python testleri | **162 OK** (1 atlandı) · demo **19/19** ✔ |

> Yerel 3.13 kurulumu: `python-build-standalone` (CPython 3.13.16) →
> `$HOME/tools/python313/bin/python3`. Chaquopy uyarısı ("3.13 may have fewer
> packages") önemsizdir: projede **hiç pip paketi yoktur**.

### 5.2 🔴 Kaynak kod GitHub'a itilmemiş

`https://github.com/Awulokune/AwuGokturk-Android` deposunda yalnızca `LICENSE` ve
`README.md` var. **Android/Python kaynağı itilmelidir.** F-Droid ancak kaynağı
olan bir depoyu derleyebilir.

### 5.3 🔴 Sürüm etiketi (tag) yok

`UpdateCheckMode: Tags` kullanılıyor ama depoda **0 tag** var. `1.0.0`
etiketli bir tag oluşturulmalıdır (sürüm adıyla eşleşmeli).

### 5.4 🔴 `commit:` alanı doldurulmadı

Metadata dosyalarında `commit: BURAYA_TAM_COMMIT_SHA_YAZILACAK` yazıyor.
Kaynak itilip tag atıldıktan sonra o commit'in **40 karakterlik tam SHA'sı**
yazılmalıdır.

### 5.5 🟡 APK imzalama

F-Droid APK'yı **kendi anahtarıyla** imzalar. Kullanıcıların F-Droid
sürümünden sorunsuz yükseltebilmesi için, sizin kendi dağıttığınız APK'yı
**aynı anahtarla** imzalamanız veya kendi dağıtımınızı bırakmanız gerekir.
(Bu projede release derlemesi **imzasızdır** — doğru olan budur.)

### 5.6 🟡 Model ağırlıklarının kökeni

`assets/classifier5k.json` bir **üretilmiş** dosyadır. Kaynağı olan
`experiments_v2/exp_B_classification/model.pt` ve üretim betiği
`tools/export_classifier5k.py` de depoda bulunmalıdır ki F-Droid "kaynaktan
yeniden üretilebilir" diyebilsin. (Deterministik üretim daha önce doğrulandı.)

### 5.7 🟡 İnceleme noktası: çalışma zamanında model indirme

Model güncellemesi, GitHub Releases'ten ağırlık indirir. Ağırlıklar veridir ve
izin listesiyle (yalnız `github.com/Awulokune/AwuGokturk-Android`, HTTPS) ve SHA-256
doğrulamasıyla korunur; ancak F-Droid inceleyicisi bu özelliği sorgulayabilir.
Gerekirse gerekçeyi metadata `MaintainerNotes` alanında açıklayın.

---

## 6. Testler ve derleme

### 6.1 Mevcut testler

```
cd embedded_agent && python3 -m unittest discover -s tests
python3 examples/demo.py
```

(Bu teslimatta çalıştırıldı; sonuçlar teslim raporundadır.)

### 6.2 F-Droid'in derlediği varyantı yerelde derlemek

```bash
cd android
JAVA_HOME=/yol/jdk-17 ANDROID_HOME=/yol/Android/Sdk \
  ../gradle-8.7/bin/gradle :app:assembleRelease \
  -PbuildPython=/yol/python3.13/bin/python3
# çıktı: app/build/outputs/apk/release/AwuGokturk-release.apk  (İMZASIZ)
```

> `--offline` KULLANMAYIN: `lintVitalAnalyzeRelease` görevi
> `com.android.tools.lint:lint-gradle` indirir (Google Maven). F-Droid
> sunucusunda ağ vardır.

### 6.3 APK boyutu

| Varyant | Boyut | İmza |
|---|---|---|
| `release` (F-Droid'in derlediği) | **40.029.770 bayt (~38,2 MiB)** | İmzasız |
| `debug` (geliştirme) | 42.892.370 bayt (~40,9 MiB) | Debug anahtarı |

Release, debug'dan küçüktür çünkü `ui-tooling` yalnızca debug'a dahildir.

**Release APK emülatörde (Android 14 / API 34 / x86_64) doğrulandı:** yerel test
için debug anahtarıyla imzalanıp kuruldu; uygulama açıldı, **çökmedi**, sohbet
turu çalıştı (`led yak` → kart-netleştirme yanıtı) ve Ayarlar'da **"5K
sınıflandırıcı: yüklü (4893 parametre)"**, **"Yüklü model sürümü 5K-1.0.0"**,
sürüm **1.0.0** ve **"Çevrimdışı Durum"** görüldü.

### 6.4 Bilinen sınırlama: bayt-bayt yeniden üretilebilirlik YOK

İki temiz release derlemesi **aynı boyutu** ama **farklı SHA-256** üretir. Fark
yalnızca `assets/chaquopy/app.imy` içindedir: Chaquopy, `.pyc` başlığına
kaynağın **mtime**'ını yazar; bu değer her derlemede değişir. Çalışma zamanı
davranışı etkilenmez (Chaquopy `.pyc`'yi doğrudan yükler).

Bu, F-Droid için **engel değildir** (F-Droid yeniden üretilebilirliği tercih
eder ama zorunlu tutmaz). Olası çözüm (bu teslimatta **DENENMEDİ**): CPython'un
`py_compile` modülü `SOURCE_DATE_EPOCH` ayarlıysa mtime yerine kaynak hash'i
yazar; ancak Chaquopy'nin `.pyc` görevi Gradle `Exec` görevi olmadığından bu
değişken proje içinden ayarlanamadı. Gradle çağrılmadan önce
`export SOURCE_DATE_EPOCH=0` denenebilir (test edilmedi).

---

## 7. Sizin yapmanız gereken adımlar (sıra ile)

1. **Kaynağı itin.** `Awulokune/AwuGokturk-Android` deposuna proje kaynağını
   (bu ağacı) gönderin. Gradle kökü: `android`.
2. **Sürüm etiketi atın:** `git tag 1.0.0 && git push --tags`
   (etiket, `versionName` ile eşleşmeli).
3. **`commit:` SHA'sını doldurun** (hem `.fdroid.yml` hem
   `embedded_agent/fdroid/metadata/com.awulokune.awugokturk.yml`).
4. **Python sürümü:** ✅ **Yapıldı** — Chaquopy `version = "3.13"` olarak
   ayarlandı, python3.13 ile temiz derleme yapıldı ve cihazda test edildi (§5.1).
   Yerelde 3.13 gerekir (`build_apk.sh` varsayılanı `$HOME/tools/python313`).
5. **`local.properties` dosyasını commit etmeyin** (`.gitignore` hallediyor).
6. **F-Droid başvurusu:** `fdroiddata` deposunu çatallayın,
   `metadata/com.awulokune.awugokturk.yml` dosyasını ekleyin ve bir
   **merge request** açın. (Bu adımı sizin adınıza **yapmadım**.)
7. İsteğe bağlı: `model.pt` ve eğitim verisini depoya ekleyin (§5.6).

---

## 8. Doğrulanmayan / test edilmeyen noktalar (dürüstlük)

- **F-Droid derleme sunucusunda gerçek bir `fdroid build` ÇALIŞTIRILMADI**
  (erişimim yok). Yukarıdaki mekanik bulgular `fdroidserver` kaynak kodundan
  okunarak doğrulandı, ancak uçtan uca denenmedi.
- **F-Droid'in kendi imzalı APK'sı** ile cihazda yükseltme denenmedi.
- **32 bit ARM (`armeabi-v7a`) cihazda** çalışma denenmedi (derlenmiyor).
- **Bayt-bayt yeniden üretilebilirlik yok** (§6.4); olası `SOURCE_DATE_EPOCH`
  çözümü denenmedi.
- F-Droid metadata'sı `fdroid lint` ile **resmî olarak denetlenmedi**
  (`fdroidserver` kurulu değil); YAML geçerliliği ve alan adları kaynaktan
  doğrulandı.

**Doğrulananlar (iddia edilmeden önce test edildi):** temiz `assembleRelease`
ve `assembleDebug` **python3.13 ile** başarılı; `.pyc` magic **3571**;
`libpython3.13.so` APK içinde; release APK **imzasız**; release APK yerel olarak
imzalanıp **emülatörde kuruldu, açıldı, sohbet etti** ve modeli (4893 parametre)
yükledi; `assets/classifier5k.json` APK içinde **bayt-bayt aynı**; 162 Python
testi + 19 demo senaryosu geçti.

---

## 9. Kaynaklar (doğrulama için kullanıldı)

- F-Droid Dahil Etme Politikası: https://f-droid.org/docs/Inclusion_Policy/
- F-Droid Build Metadata Referansı: https://f-droid.org/docs/Build_Metadata_Reference/
- F-Droid Açıklama/Görsel: https://f-droid.org/docs/All_About_Descriptions_Graphics_and_Screenshots/
- fdroidserver `build.py`, `metadata.py`, `scanner.py`, `common.py`, `lint.py`
- `gradlew-fdroid`: https://gitlab.com/fdroid/gradlew-fdroid
- F-Droid derleme sunucusu Dockerfile/Vagrantfile (Debian trixie)
- Chaquopy `pyc.py` (magic number denetimi): https://github.com/chaquo/chaquopy
- Chaquopy 16.0.0 sürüm notları: https://chaquo.com/chaquopy/chaquopy-version-16-0-0/
