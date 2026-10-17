# AwuGöktürk Embedded Agent AI — Teslimat Raporu

Tarih: 2026-10-16 · Kapsam: mevcut `awu-gokturk-coder-5k` projesi üzerine modüler
gömülü kodlama ajanı. **Mevcut `model/`, veri setleri (`*.jsonl`), `experiments/`
ve `experiments_v2/` DEĞİŞTİRİLMEDİ.** Tüm yeni kod `embedded_agent/` altındadır.

---

## 0. Mevcut proje yapısı ve test komutları (önce incelendi)

| Bileşen | Konum | Durum |
|---|---|---|
| Üretim modeli (char GRU, 4.990 param) | `model/checkpoints/best_fp32.pt` | Dokunulmadı |
| 5K sınıflandırıcı (4.893 param, 8 sınıf) | `experiments_v2/exp_B_classification/model.pt` | Salt-okunur köprü ile kullanıldı |
| Veri seti (4000/500/500) | `train.jsonl`, `validation.jsonl`, `test.jsonl` | Dokunulmadı |
| Paylaşılan kütüphaneler | `experiments/lib/awu.py`, `experiments_v2/lib_v2.py` | Değiştirilmedi |
| Test komutları (mevcut) | `python3 experiments_v2/data_v2.py`, `python3 exp_B_classification/run.py`, `python3 exp_A_code_completion/run.py` | Değiştirilmedi |

**Araç zinciri (tespit edildi):** `g++` 16.2.1 var; `arduino-cli` **yok**,
`avr-gcc` **yok**, `platformio` **yok**. → Gerçek AVR/ESP32 derlemesi yapılamaz;
yalnızca host sözdizimi doğrulaması mümkündür.

Yeni ajan test komutları:
```bash
cd embedded_agent
python3 -m unittest discover -s tests -v     # birim testleri
python3 examples/demo.py                     # kabul senaryoları
python3 tools/generate_agent_dataset.py      # veri seti şeması örneği (eğitim yok)
```

---

## 1. Değiştirilen ve eklenen dosyalar

**Değiştirilen dosya: YOK.** Mevcut projeye (model, veri, deneyler, raporlar) hiç
dokunulmadı; hiçbir checkpoint üzerine yazılmadı, hiçbir dosya silinmedi.

**Eklenen dosyalar (hepsi `embedded_agent/` altında):**

```
DESIGN.md, README.md, REPORT.md
awa_agent/__init__.py
awa_agent/agent.py                (orkestratör / boru hattı)
awa_agent/intent_router.py        (Intent Router)
awa_agent/board_resolver.py       (Board Resolver)
awa_agent/requirement_parser.py   (Requirement Parser)
awa_agent/knowledge_registry.py   (Knowledge/Library Registry)
awa_agent/code_generator.py       (Code Generator)
awa_agent/awu_guard.py            (AwuGuard)
awa_agent/build_validator.py      (Build Validator)
awa_agent/test_generator.py       (Test Generator)
awa_agent/response_handler.py     (Response Handler)
awa_agent/classifier5k.py         (mevcut 5K modeline salt-okunur köprü)
awa_agent/boards/{base,arduino_uno,arduino_mega2560,esp32,__init__}.py
awa_agent/stubs/arduino/{Arduino,Servo,DHT,Wire,SPI,LiquidCrystal_I2C,EEPROM}.h
awa_agent/stubs/esp32/{Arduino,WiFi,HTTPClient,WebServer,BLEDevice}.h
tests/{__init__.py,test_agents.py}
examples/{demo.py,demo_results.json}
tools/generate_agent_dataset.py
data_agent/{schema.md,agent_train.jsonl,agent_validation.jsonl,agent_test.jsonl,summary.json}
```
(~2.900 satır Python + stub başlıklar.)

---

## 2. Uygulanan özellikler

### 2.1 Mimari (9 bileşen ayrıştırıldı)
Intent Router · Board Resolver · Requirement Parser · Knowledge/Library Registry ·
Code Generator · AwuGuard · Build Validator · Test Generator · Response Handler
— tümü `awa_agent/agent.py` boru hattında birleştirilir.

### 2.2 Kart profilleri (bağımsız, genişletilebilir)
| | Arduino Uno R3 | Arduino Mega 2560 | ESP32 (klasik) |
|---|---|---|---|
| MCU | ATmega328P | ATmega2560 | ESP32-D0WD |
| Dijital | 0–13 | 0–53 | GPIO 0–39 (kısıtlı) |
| Analog | A0–A5 (14–19) | A0–A15 (54–69) | ADC1 32–39; ADC2 0,2,4,12–15,25–27 |
| PWM | 3,5,6,9,10,11 | 2–13,44,45,46 | LEDC (tüm çıkış GPIO) |
| Kesme | 2,3 | 2,3,18,19,20,21 | tüm giriş GPIO |
| Gerilim | 5 V | 5 V | **3,3 V (5 V toleranslı değil)** |
| Kısıt | 0/1 UART | Uno A0=14 kuralı **geçersiz** | 6–11 flash; 34–39 giriş-only |

Yeni kart = `boards/` altına `BoardProfile` + `register()`; çekirdek değişmez
(RP2040 vb. bu yolla eklenebilir). ESP32 **varyantları (S2/S3/C3/S1)** ve
ESP8266/RP2040 desteklenmez; istek gelirse dürüstçe belirtilir.

### 2.3 Desteklenen modüller (registry tabanlı, 17 modül)
led_on, led_off, led_blink, two_leds, button_led, two_buttons_two_leds,
analog_read_serial, pwm_fade, pwm_write, servo_sweep, ultrasonic_distance,
buzzer_tone, dht_read, lcd_i2c_print, i2c_scan, wifi_connect, wifi_http_get.

| Modül | Uno | Mega | ESP32 |
|---|---|---|---|
| led_on/off/blink, two_leds, button_led, two_buttons_two_leds | evet | evet | evet |
| analog_read_serial, pwm_fade/pwm_write | evet | evet | evet |
| servo_sweep, ultrasonic_distance, buzzer_tone, dht_read | evet | evet | evet |
| lcd_i2c_print, i2c_scan | evet | evet | evet |
| wifi_connect, wifi_http_get | – | – | evet |

### 2.4 Kod üretim kuralları (uygulandı)
- Kullanıcı pini **aynen korunur**; sessizce varsayılana çevrilmez.
- Negatif/aralık dışı/kullanılamaz pin → **açık hata, kod üretilmez**.
- Pin belirtilmemişse yalnızca kartın `safe_*` listesinden güvenli varsayılan
  atanır ve bu varsayımlar yanıtta **açıkça bildirilir**.
- Pin çakışması, kart–kütüphane uyumsuzluğu, eksik `#include`, eksik zorunlu
  parametre, çelişkili gereksinim → AwuGuard bulgusu.
- Bilinmeyen modül/API → **uydurulmaz**; net soru veya ret.

### 2.5 AwuGuard
Geçersiz/kullanılamaz pin, istenen pinin değiştirilmesi, çift yönlü pin çakışması,
OUTPUT/INPUT çelişkisi, PWM olmayan pinde `analogWrite`, giriş-only pine yazma,
ADC2 + Wi-Fi uyarısı, kart–kütüphane uyumsuzluğu, eksik zorunlu parametre, eksik
`#include`, ESP32'de 5 V sensör seviye uyarısı. **Softmax güveni doğruluk kanıtı
sayılmaz.**

### 2.6 Build Validator (dürüst sınır)
`g++ -fsyntax-only` + Arduino/ESP32 API taklidi stub başlıklarla **host sözdizimi**
doğrulaması. Her yanıtta "gerçek hedef derlemesi değildir" etiketi bulunur.
`arduino-cli`/`avr-gcc` olmadığı için **AVR/ESP32 hedef derlemesi yapılamaz.**

### 2.7 5K sınıflandırıcı entegrasyonu
`classifier5k.py` mevcut `exp_B_classification/model.pt`'yi **salt-okunur** yükler
(4.893 param, 8 sınıf: `kod_cikti, kavram_sorusu, arduino_dijital, arduino_analog,
hata_bulma, sinif_uye_metot, bellek_isaretci, sinif_tanimlama`). Yalnızca
**görev-türü ipucu** olarak kullanılır; kural tabanı çelişkide kazanır. Model
yoksa ajan çalışmaya devam eder.

### 2.8 Veri seti şeması (`data_agent/`)
`tools/generate_agent_dataset.py` 35 kayıtlık **örnek/tohum** set üretir
(8 kategori: geçerli üretim, geçersiz pin, eksik bilgi, desteklenmeyen modül/kart,
debug, kavram, selamlama). Alanlar `data_agent/schema.md`'de tanımlıdır. Split:
train 16 / val 10 / test 9; **sızıntı yok** (`leakage: []`). Beklenen alanlar
mevcut ajanın **donmuş** çıktısıdır. **Bu set ile eğitim YAPILMADI.**

---

## 3. Gerçekten çalıştırılan testler ve sonuçları

### 3.1 Birim testleri — `python3 -m unittest discover -s tests -v`
**32/32 GEÇTİ** (2,7 s). Kapsam: kart pin aralıkları (Uno/Mega farkı, ESP32
kısıtları, negatif pin), Intent Router, Requirement Parser (negatif pin, pin
listesi, `GPIO 18`'in `ESP32` kelimesiyle karışmaması, bilinmeyen sensör),
kod üretimi + pin koruma, geçersiz pin reddi, PWM olmayan pin reddi, kart
sorulması, desteklenmeyen kart/varyant reddi, Mega'da Wi-Fi reddi, kütüphane
`#include` üretimi, debug pin çakışması, 5K sınıflandırıcı köprüsü.

### 3.2 Kabul senaryoları — `python3 examples/demo.py` → **19/19 GEÇTİ**

| # | İstek | Beklenen | Sonuç |
|---|---|---|---|
| 1 | Arduino Uno'da 7. pindeki LED'i yak. | ok, pin=7 | ok (host derleme ✓) |
| 2 | Arduino Uno'da -1 numaralı pindeki LED'i yak. | hata, kod yok | error ✓ |
| 3 | Arduino Mega'da iki butonla iki LED'i kontrol et. | ok | ok (varsayılan pinler bildirildi) |
| 4 | ESP32'de GPIO 18'deki LED'i 500 ms aralıklarla yakıp söndür. | ok, pin=18 | ok (host derleme ✓) |
| 5 | ESP32'de Wi-Fi üzerinden HTTP isteği yap. | soru sor | needs_info (URL/SSID/sifre) ✓ |
| 6 | A0 pinindeki potansiyometre değerini seri monitöre yazdır. | kart sor | needs_info ✓ |
| 7 | Bu kodda pin çakışması var mı? | kod iste | needs_info ✓ |
| 8 | Merhaba. | selamlama | greeting ✓ |
| 9 | Bilinmeyen bir sensörü oku. | ret | unsupported ✓ |
| 10 | Uno'da 9. pinde PWM | ok | ok (host derleme ✓) |
| 11 | Uno'da A0 potansiyometre | ok | ok (host derleme ✓) |
| 12 | Mega'da 44 numaralı pinde PWM | ok | ok (Uno'da yok olan pin) |
| 13 | Mega'da A15 sensör | ok | ok |
| 14 | ESP32'de GPIO 34 potansiyometre | ok | ok (ADC1, input-only pin) |
| 15 | ESP32'de GPIO 18'de PWM | ok | ok (`ledcWrite`) |
| 16 | ESP32'de A0 sensörü oku | hata | error ✓ (ESP32'de A0 yok) |
| 17 | ESP32-S3'te GPIO 5 LED | ret | unsupported ✓ |
| 18 | Mega'da Wi-Fi HTTP | hata, kod yok | error ✓ |
| 19 | Mevcut kodda pin çakışması (pinMode 7 OUTPUT+INPUT) | bulgu | çakışma bulundu ✓ |

Ayrıntılar: `examples/demo_results.json`.

### 3.3 Host derleme doğrulaması
Üretilen geçerli kodlar `g++ -fsyntax-only` ile **başarıyla** derlendi
(stub başlıklar). Bu **gerçek AVR/ESP32 derlemesi DEĞİLDİR** ve öyle sunulmaz.

---

## 4. Henüz desteklenmeyen özellikler

- **Gerçek hedef derleme/yükleme:** `arduino-cli`/`avr-gcc`/`platformio` yok →
  AVR/ESP32 için gerçek derleme ve donanım doğrulaması yapılamaz.
- **Donanım testi:** hiçbir kod gerçek Uno/Mega/ESP32 üzerinde çalıştırılmadı.
- **Desteklenmeyen kartlar:** ESP8266, RP2040/Pico, ESP32 varyantları (S2/S3/C3/
  S1/P4), Arduino Nano/Micro/Leonardo, ESP-IDF framework'ü.
- **Desteklenmeyen modüller/kütüphaneler:** OLED/TFT/LED matris, step motor,
  röle/MOSFET, SD kart, RTC, MQTT/WebServer/BLE (registry'de API'si yok → kod
  uydurulmaz), EEPROM bellek yönetimi, yazılımsal seri.
- **Çok modüllü üretim:** tek seferde birden fazla farklı modül (ör. buton + DHT +
  LCD) birleştirilmiyor; tek modül/tek aile destekleniyor.
- **Kod dönüştürme (transform):** başlık var ama tam uygulanmadı; istek kod
  analizi (debug) ile karşılanır.
- **Serbest kod üretimi:** 5K/4.990 parametreli modeller **genel amaçlı kod
  üretim modeli olarak kullanılmaz**; üretim kural/şablon tabanlıdır.
- **Ağa bağlı (Wi-Fi) kod:** yalnızca ESP32 ve yalnızca `WiFi`/`HTTPClient`;
  POST/bearer/gövde yönetimi, MQTT, WebServer yok.
- **Gerçek elektriksel doğrulama:** gerilim/akım hesapları yalnızca uyarı
  seviyesindedir, ölçüm yapılmaz.

---

## 5. Eğitim gerekip gerekmediği

- **Eğitim yapılmadı ve gerekli değildi.** Ajan kural, doğrulanmış bilgi kaydı ve
  şablonlarla çalışır; yeni model eğitimi gerektirmez.
- Mevcut **5K sınıflandırıcı korunmuştur** ve yalnızca görev-türü ipucu için
  salt-okunur kullanılır. v2 raporları göstermiştir ki ~5K parametre **serbest
  C/C++ üretimi için yetersizdir** (tam eşleşme ~%6,8; kod derlenebilirliği %0)
  ve **kısıtlı görev sınıflandırması için yeterlidir** (test doğruluğu %93,4).
- Yeni `data_agent/` şeması **eğitim için kullanılmadı**; yalnızca tohum örnek
  üretir.

**Daha büyük/kapsamlı bir model gerekirse (onay alınmadan başlatılmaz):**

| Seçenek | Yaklaşık boyut | Donanım | Not |
|---|---|---|---|
| Mevcut 5K | 4,9K param | CPU, dakikalar | Yalnızca sınıflandırma/ipucu; üretim için yetersiz |
| Küçük SLM (0.5–1B, 4-bit QLoRA) | ~0.5–1B | 1×16–24 GB GPU, saatler | Gömülü kod üretimi; lisans/veri gerekir |
| Orta SLM (7B, LoRA) | 7B | 1×24–48 GB GPU, günler | Belirgin kod kalitesi; maliyet yüksek |
| Harici API (bulut LLM) | — | İnternet | En yüksek kalite; gizlilik/maliyet ve bağımlılık riski |

Eğitim başlatmak için **açık onay** gerekir; her seçeneğin veri, lisans, maliyet
ve gizlilik etkileri ayrıca değerlendirilmelidir.

---

## 6. Sonraki geliştirme adımları

1. **Gerçek derleme:** `arduino-cli` + `arduino:avr` ve `esp32:esp32` çekirdekleri
   kurulup Build Validator'a gerçek hedef derleme modu eklenmeli.
2. **Çok modüllü üretim:** birden fazla modülü birleştiren (pin çakışma çözümlü)
   proje üretici.
3. **Modül kapsamını genişletme:** OLED/TFT, step motor, röle, SD/RTC, MQTT/BLE
   (yalnızca doğrulanmış API kayıtlarıyla).
4. **Kod dönüştürme (transform)** ve hata düzeltmede otomatik yama önerisi.
5. **Veri seti:** `data_agent/` şemasını gerçek üretim/test sonuçlarıyla besleyip
   büyütme; pin doğruluğu, derleme başarısı, davranış doğruluğu, doğru ret ve
   soru-sorma isabetini **ayrı** ölçme (tek skor yok).
6. **Round-trip değerlendirme:** üretilen kodu derleyip (mümkünse) simüle ederek
   davranış doğrulaması; başarısızlık nedenlerini sınıflandırma.
7. **5K modeli:** yalnızca Uno görev-türü ipucu olarak kalmalı; kart-özel
   sınıflandırma (Uno/Mega/ESP32) gerekirse ayrı ve dürüst metriklerle eğitilmeli.

---

## 7. Düzeltme turu — HTTP niyeti ve parametre koruma (2026-10-16)

Üç hata minimal, test odaklı değişikliklerle giderildi.

**Değişen dosyalar (yalnızca `awa_agent/` + `tests/`):**
- `awa_agent/requirement_parser.py`: `Requirements.unsupported_features` alanı;
  HTTP **sunucu** tespiti (`sunucu`/`server`/`cevap veren`) → istemciden ayrılır;
  `_extract_wifi_creds()` / `_extract_url()` ile **SSID/şifre/URL artık `Action.params`'a
  yazılır** (kullanıcı değeri aynen korunur).
- `awa_agent/agent.py`: `_capability_problems()` — kart/özellik uyumsuzluğu
  **eksik parametre sorularından önce** raporlanır; `_mask()` ile şifre teşhis
  alanlarında maskelenir (kod bloğu kullanıcının istediği çıktıyı korur).
- `tests/test_agents.py`: `TestHttpIntentAndParams` (5 yeni regresyon testi).
- `data_agent/*.jsonl`: üretilen örnek set yeni davranışla yeniden dondu­ruldu
  (sızıntı yok).

**Hata 1 — HTTP sunucusu/istemcisi ayrımı:** `wifi_http_get` (istemci) yalnızca
istemci isteklerinde üretilir; "sunucu" istekleri `unsupported` döner, `HTTPClient`
kodu **sunucu olarak sunulmaz**.

**Hata 2 — parametre koruma:** verilen `SSID`, şifre ve URL parser→generator
boyunca taşınır; kodda `TEST_WIFI` / `TEST_PASSWORD` / `https://example.com`
korunur; gereksiz `needs_info` dönmez. Şifre log/rapor alanlarında maskelenir.

**Hata 3 — Uno ret gerekçesi:** kart Uno kalır, ESP32 kodu üretilmez; gerekçe
"Uno Wi-Fi donanımına sahip değildir, kart değiştirilmedi" olarak **eksik
parametre sorularından önce** verilir.

**Test sonuçları:** birim **37/37 geçti** (32 mevcut + 5 yeni), kabul senaryoları
**19/19 geçti**. Derleme yine yalnızca **host sözdizimi** (gerçek ESP32 derlemesi
yapılmadı; iddia edilmez).

---

## 8. Türkçe sohbet ve kavram açıklama katmanı (2026-10-16)

Kodlama yeteneği korunarak ajanın **genel Türkçe sohbet** ve **doğrulanmış kavram
açıklama** yeteneği eklendi. Katman **kural tabanlıdır**; 5K modeli burada
kullanılmaz ve genel sohbet modeli olarak sunulmaz.

**Değişen/eklenen dosyalar:**
- **Yeni** `awa_agent/chat_knowledge.py`: Türkçe, modüler bilgi kaynağı (14 konu) +
  kimlik/yetenek/dürüstlük metinleri. Yeni konu = yeni `Topic` kaydı.
- `awa_agent/intent_router.py`: `IDENTITY` ve `GENERAL_CHAT` intent'leri; kullanıcıya
  dönük `category` alanı (`greeting`, `identity`, `general_chat`,
  `concept_explanation`, `embedded_coding`, `unsupported`); kimlik/nezaket tespiti
  kodlama tespitinden **önce**. 5K ipucu yalnızca gömülü/kavram görevlerinde çalışır.
- `awa_agent/agent.py`: `_identity_response()`, `_smalltalk_response()`; kavram
  yanıtı önce `chat_knowledge`, sonra mevcut gömülü API açıklamalarına düşer;
  kapsam dışında **uydurmaz**, sınırı bildirir. Selamlama ve `unsupported` yanıtları
  doğal Türkçeye çevrildi (kart/modül sorusuna dönüşmez).
- `awa_agent/requirement_parser.py`: `_interval_ms()` artık "bir saniye"/"yarım
  saniye" gibi Türkçe sayı sözcüklerini de anlar.
- `tests/test_chat.py`: **17 yeni regresyon testi** (yönlendirme + davranış).
- `README.md`, `REPORT.md`: güncellendi.

**Desteklenen konular:** CPU/işlemci, RAM, GPU, işletim sistemi; Arduino ile ESP32
farkları; dijital giriş/çıkış, ADC, PWM; I2C, SPI, UART; HTTP sunucusu–istemcisi
farkı; temel matematik ve elektrik/fizik (Ohm yasası, güç). Ayrıca kimlik, yetenek,
nezaket ve dürüstlük yanıtları.

**Desteklenmeyenler:** Bu listelerin dışındaki kavramlar (ör. kuantum fiziği),
güncel olaylar ve serbest yaratıcı metin → `needs_info`/`unsupported`; bilgi
uydurulmaz. HTTP **sunucusu** (WebServer) hâlâ desteklenmez.

**Test sonuçları:** birim **54/54 geçti** (37 önceki + 17 sohbet), kabul senaryoları
**19/19 geçti**. Derleme yine yalnızca **host sözdizimi**; gerçek ESP32 derlemesi
yapılmadı ve iddia edilmez. Eğitim **yapılmadı**. `model/`, checkpoint'ler,
`train/validation/test.jsonl`, `experiments/`, `experiments_v2/` **değiştirilmedi**.

---

## 9. Sohbet yönlendirmesi ve genel sohbet düzeltmesi (2026-10-16)

Bildirilen altı girdi `unsupported` dönüyordu; kök nedenler ve içerik tabanlı
düzeltmeler aşağıdadır. Yönlendirme, **anahtar sözcük ekleyerek gizlenmedi**;
gerekçe düzeyinde düzeltildi.

**Kök nedenler:**
1. `"bugün"` → norm `"bugun"`, `"bug"` alt dizgesiyle eşleşip yanlış `DEBUG` sinyali
   üretiyordu → `"bug"` artık yalnızca **tam sözcük** (`\bbug\b`) olarak aranır.
2. "Merhaba ... nasılsın?" gibi **selamlama + nezaket** ifadeleri yalnızca salt
   selamlamayla sınırlıydı → selam/nezaket belirteci içeren ve donanım/eylem
   içermeyen mesajlar `greeting`.
3. Genel bilgi ve yaratıcı yazarlık için kategori yoktu → `general_knowledge` ve
   `creative_writing` eklendi.
4. Yalnızca ad yazımı (`AwuGöktürk`, `AwuGöktürk Embedded Agent`) kimlik sayılmıyordu
   → `is_name_only()` ile `identity`.
5. "bilmiyorsan bile cevap vermeye çalış" `unsupported`'a düşüyordu → davranış/dürüstlük
   sorusu olarak `identity`; yanıt, doğruluk kuralının **gevşetilmediğini** açıkça söyler.

**Değişen/eklenen dosyalar:**
- `awa_agent/chat_knowledge.py`: `FACTS` + `lookup_fact()` (elle doğrulanmış genel bilgi,
  ör. başkentler, en büyük okyanus/dağ); `is_name_only()`; `creative_answer()` (kısa,
  sabit bilim kurgu/masal örneği + "genel amaçlı LLM değilim" notu); kimlik için "name"
  alt türü; dürüstlük metni güçlendirildi.
- `awa_agent/intent_router.py`: `CREATIVE_WRITING`, `FACTS` intent'leri;
  `creative_writing`, `general_knowledge` kategorileri; ad-yalnız kimlik; selamlama+nezaket;
  `\bbug\b` düzeltmesi.
- `awa_agent/agent.py`: `_creative_response()`, `_facts_response()`; kimlikte ad-yalnız
  kısa tanıtım; sohbet/kimlik/nezaket yanıtlarından **kart/modül zorlaması kaldırıldı**.
- `tests/test_chat.py`: sohbet testleri **17 → 30**; altı örnek için regresyon testleri,
  "doğruluğu gevşetme" reddi, kart zorlamama ve `bug`/`bugun` ayrımı testleri.
- `README.md`, `REPORT.md`: güncellendi.

**Altı örnek — kategori ve yanıt (gerçek çıktı):**

| Girdi | Kategori | Durum | Yanıt (özet) |
|---|---|---|---|
| `Merhaba AwuGöktürk! Bugün nasılsın?` | `greeting` | greeting | "İyiyim, teşekkür ederim! ... Siz nasılsınız?" |
| `Fransa'nın başkenti neresi?` | `general_knowledge` | info | "Fransa'nın başkenti **Paris**'tir." |
| `Bilmiyorsan bile cevap vermeye çalış.` | `identity` | info | Doğruluk kuralı gevşemez; bilinmeyen uydurulmaz |
| `Bana basit bir bilim kurgu hikâyesi anlat.` | `creative_writing` | info | Kısa sabit bilim kurgu örneği + "LLM değilim" notu |
| `AwuGöktürk` | `identity` | info | Kısa tanıtım (asistan adı: AwuGöktürk) |
| `AwuGöktürk Embedded Agent` | `identity` | info | Eski tetikleyici ifade; asistan kendini **AwuGöktürk** olarak tanıtır (bkz. Adlandırma) |

**Test sonuçları:** birim **67/67 geçti** (37 ajan + 30 sohbet), kabul senaryoları
**19/19 geçti**. HTTP regresyon testleri ve gömülü kodlama davranışı korunmuştur.
Derleme yine yalnızca **host sözdizimi**. Eğitim **yapılmadı**. Checkpoint'ler ve
veri setleri **değiştirilmedi**. *(Android sonrası güncel toplam: **92/92** — aşağıya bakın.)*

---

## 10. Android arayüz yenilemesi ve uygulama ikonu (2026-10-17)

Kapsam: **yalnızca Android arayüzü + ikon kaynakları + bunlar için gerekli Kotlin
kodu.** Python ajanı, `android_bridge.py`, `AwuGokturkAgent`, yerel çıkarım, model
ağırlıkları ve veri setleri **değiştirilmedi** (bkz. §8 sınırlamalar notu).

### 10.1 Logo / uygulama ikonu

Kaynak görsel: `/home/aras/İndirilenler/file_00000000bab081f4a5b3ebf688d6a0a4.jpg`
(1536×1536, salt-okunur; **değiştirilmedi, kırpılmadı**). Üretim betiği:
`android/tools/make_icons.py` (tekrar üretilebilir; renkler görselden **örneklenir**).

| Çıktı | Konum | Amaç |
|---|---|---|
| `ic_launcher.png` | `mipmap-{mdpi..xxxhdpi}` | legacy kare simge (48/72/96/144/192) |
| `ic_launcher_round.png` | `mipmap-{mdpi..xxxhdpi}` | legacy yuvarlak simge |
| `ic_launcher_foreground.png` | `mipmap-{mdpi..xxxhdpi}` | adaptive ön plan (108/162/216/324/432) |
| `ic_launcher.xml`, `ic_launcher_round.xml` | `mipmap-anydpi-v26` | adaptive icon tanımı |
| `ic_launcher_background.xml` | `drawable` | adaptive arka plan (`@color/awu_logo_background` `#D94A25`) |
| `ic_awu_logo.png`, `ic_awu_avatar.png` | `drawable-nodpi` | uygulama içi logo / asistan avatarı |

* Ana konu (beyaz çerçeve + harf serisi) **kırpılmadan** korunur; arka plandan
  **parlaklık eşiğiyle** ayıklanır.
* Ön plan, çerçeve köşe yarıçapı **66dp güvenli daireye** sığacak biçimde ölçeklenir
  (ölçülen 32,6 ≤ 33) → yuvarlak/kare/squircle **tüm maskelerde okunaklı**.
* Manifest: `android:icon="@mipmap/ic_launcher"`,
  `android:roundIcon="@mipmap/ic_launcher_round"`, `windowSoftInputMode="adjustResize"`.
* **APK içinden doğrulandı:** `aapt2 dump badging` →
  `application: label='AwuGöktürk' icon='res/mipmap-anydpi-v26/ic_launcher.xml'`;
  `unzip -l` ile tüm `ic_launcher*`/`ic_awu*` kaynakları mevcut.

### 10.2 Sohbet deneyimi (yeniden tasarlandı)

* Üst çubuk: **logo (sol)** + "AwuGöktürk" + yeşil durum noktası + alt başlık
  `Microcontroller:5K`; sağda **yeni sohbet** ve **geçmiş** düğmeleri.
* Boş durum: ortada logo; **"Merhaba, ben AwuGöktürk."**,
  **"Arduino ve gömülü sistem projelerinde yardımcı olabilirim."** ve dört örnek
  istem (birebir): `Arduino Uno'da LED yak.` · `ESP32 ile Wi-Fi bağlantısı oluştur.` ·
  `C++ kodumu açıkla.` · `Pin 14'ün Uno'da ne olduğunu açıkla.`
* Mesajlar: kullanıcı = turkuaz→mavi degrade, sağa dayalı, yuvarlatılmış; asistan =
  sabit avatar + kenarlıklı balon. Balon kuyrukları ile ayrım net.
* Kod üretimi **sohbetin içinde**: kart adı + dürüst "derleme/donanım testi:
  yapılmadı" satırı + sözdizimi renklendirmesi + **Kopyala**/**Paylaş**; altında
  kompakt **AwuGuard** etiketi ve açılabilir ayrıntı ("geçmek doğruluk kanıtı
  değildir" uyarısıyla). Kod blokları yatay kaydırılır → **taşma yok**.
* "Yazıyor…" animasyonlu üç nokta göstergesi; hata ve üretim durumları görünür.
* Giriş alanı: çok satırlı (5 satıra kadar), `adjustResize` + `imePadding()` ile
  **klavye açıkken görünür kalır**, alt gezinme **klavye açıkken gizlenir**; boş
  mesaj gönderilemez; art arda gönderim `busy` ile kilitlenir.

### 10.3 Gezinme, geçmiş ve ayarlar

* **Sohbet** (ana ekran) · **Kod** · **Ayarlar** — küçük net simgeler + kısa
  etiketler; her sekme gerçekten çalışır (dekoratif düğme yok).
* **Gerçek çok oturumlu geçmiş:** `chat_sessions.json` (yeni sohbet / oturum aç /
  sil / tümünü temizle). Eski `chat_history.json` ilk açılışta sessizce içe aktarılır
  — emülatörde gerçekten doğrulandı ("Önceki sohbet").
* **Kod sekmesi** kod üretimine odaklanır; kart seçimi buradadır, sohbette zorunlu
  değildir. **Ayarlar**: tema, model bilgisi, çevrimdışı durum, yerel veri, derleme
  araçları, gizlilik.
* `Core Material` simgeleri + küçük özel vektörler (`ic_copy`, `ic_history`,
  `ic_tab_chat`, `ic_tab_code`) — **yeni bağımlılık eklenmedi**.

### 10.4 Bu turda çalıştırılan testler

| Test | Komut | Sonuç |
|---|---|---|
| Python birim testleri | `python3 -m unittest discover -s tests` | **92 test — OK** |
| Kabul senaryoları | `python3 examples/demo.py` | **19/19 — OK** |
| Derleme | `gradle :app:assembleDebug` | **BUILD SUCCESSFUL** |
| Kotlin derleme | `gradle :app:compileDebugKotlin` | **hata yok** |
| Arayüz turu (emülatör) | `android/tools/verify_ui.sh` | **9 ekran görüntüsü**, çökme yok |
| Çevrimdışı | uçak modu + sohbet | `Active default network: none`, yanıt üretildi |

Bu turda bulunan ve düzeltilen gerçek hatalar: (1) özel vektörlerde
`?attr/colorControlNormal` AppCompat gerektirdiği için kaynak bağlama hatası →
kaldırıldı; (2) `Icon(...)` içinde `ImageVector`/`Painter` dallarının tip
uyuşmaması → dallar ayrıldı; (3) Ayarlar'da ağırlıklı etiket sıfır genişliğe
düşüp satırı aşırı uzatıyordu → `KeyVal`/`KeyValBlock` ile düzeltildi.

**Test EDİLMEYENLER (dürüstçe):** gerçek AVR/ESP32 derlemesi ve fiziksel donanım
testi yapılmadı (araç/cihaz yok); fiziksel telefonda çalıştırılmadı.

---

## 11. Model güncelleme sistemi (GitHub Releases) — 2026-10-17

Kapsam: **yeni bir güncelleme altyapısı.** Mevcut model ağırlıkları, eğitim verisi,
sohbet/kod üretimi ve tokenizer **değiştirilmedi**; uygulama yeniden yazılmadı.
**Uygulama sürümü ile model sürümü birbirinden bağımsızdır** (arayüz bunu açıkça yazar).

### 11.1 Mimari ayrımı (mevcut kural korunur: iş mantığı Python'da)

| Katman | Dosya | Görev |
|---|---|---|
| İş mantığı (Python) | `awa_agent/model_updater.py` **(yeni)** | sürüm kontrolü, indirme, doğrulama, etkinleştirme, geri dönüş, kalıcı durum |
| Köprü (JSON) | `awa_agent/android_bridge.py` **(+8 fonksiyon)** | `configure_models`, `update_status/check/download_start/progress/cancel/rollback/set_auto` |
| Kotlin durum | `ModelUpdate.kt` **(yeni)** | JSON → Kotlin veri modeli (uydurma yok, alan eşlemesi) |
| Kotlin köprü | `PythonBridge.kt` | Chaquopy çağrıları |
| Kotlin arayüz | `ui/ModelUpdateScreen.kt` **(yeni)**, `ui/SettingsScreen.kt`, `MainActivity.kt`, `AwuViewModel.kt` | "Model Güncellemeleri" ekranı + bölüm + otomatik kontrol anahtarı |
| Yayımlama | `tools/make_model_manifest.py` **(yeni)**, `model/README.md` **(yeni)** | manifest üretimi + yayımlama kılavuzu |
| Test | `tests/test_model_updater.py` **(yeni, 70 test)** | 10 zorunlu senaryo + güvenlik |

Gerekçe: **tüm karar mantığı Python'da** kalır; Kotlin yalnızca arayüz ve ilerleme
yoklamasıdır. Böylece zorunlu senaryolar **ağ olmadan, sahte taşıma katmanıyla**
(gerçek `urllib` yolu korunarak) tekrarlanabilir biçimde test edilir. Taşıma katmanı
`set_transport()` / `set_load_probe()` dikişleriyle değiştirilebilir.

### 11.2 Sürüm kontrol mekanizması (nasıl çalışır)

1. **Kontrol:** `api.github.com/repos/Awulokune/AwuGokturk-Android/releases` (izinli adres).
   Taslak/ön sürüm Release'ler **yok sayılır**. Her sürümün `awu-model-manifest.json`
   varlığı okunur, doğrulanır; **en yüksek geçerli `model_version`** seçilir.
   Sürüm karşılaştırması **sayısal parçalara göre** yapılır (`5K-1.10.0` > `5K-1.9.0`).
2. **Uyumluluk:** `format`/`architecture`/`tokenizer_version`/`min_app_version` ve
   `vocab_size`/`labels`/`emb`/`hidden` denetlenir. Uyumsuz sürüm **indirilmez**;
   gerekçe dürüstçe gösterilir (ör. "bu sürüm daha yeni bir uygulama gerektiriyor").
3. **İndirme:** geçici dosyaya (`awu_models/downloads/<ad>.part`), 64 KiB parçalarla;
   yüzde + inen/toplam/kalan gösterilir; **iptal** ve **yeniden deneme** var.
4. **Doğrulama:** boyut → **SHA-256** → yapı (JSON, format, dizi boyutları, vocab/sınıf
   tutarlılığı) → **fiili yükleme denemesi** (ayrı bir `LiteClassifier` örneğiyle).
   **Doğrulama geçmeden hiçbir şey etkinleştirilmez.**
5. **Etkinleştirme (atomik):** önce mevcut model **yedeklenir**; yeni dosya hedefe
   taşınır; yükleme denemesi başarısız olursa **otomatik geri dönüş** (yedek geri
   yüklenir, durum düzeltilir). `os.replace` + durum dosyası **tmp→replace** ile yazılır.
6. **Kilitlenme güvenliği:** etkinleştirme öncesi `pending` işaretlenir. Uygulama
   indirme sırasında kapanırsa, sonraki açılışta `pending` **yarım sayılır**, tüm
   `*.part` dosyaları silinir ve **paket içi model** kullanılır. Bozuk/eksik/SHA
   uyuşmayan güncelleme dosyası **sessizce paket içi modele düşer**.

Kalıcı durum: `filesDir/awu_models/model_state.json` (kurulu sürüm, yol, SHA, yedek,
son kontrol sonucu, otomatik kontrol anahtarı, geçmiş). Paket içi model
`filesDir/classifier5k.json` olarak **hiç üzerine yazılmaz** (referans kopya).

### 11.3 Güvenlik

* Yalnızca **HTTPS**; yalnızca izin listesindeki ana bilgisayarlar
  (`api.github.com`, `github.com`, `objects.githubusercontent.com`,
  `release-assets.githubusercontent.com`, `raw.githubusercontent.com`,
  `codeload.github.com`) **ve** yol `.../Awulokune/AwuGokturk-Android` ile başlamalı.
  Her **yönlendirme adımı** ayrıca doğrulanır (en fazla 5).
* Dosya adı yalnızca **basit ad** olabilir (`..`, `/`, `\` reddedilir).
* Sınırlar: ağırlık **8 MiB**, manifest 256 KiB, sürüm listesi 2 MiB; ayrıca
  **disk alanı marjı 8 MiB** (yer yoksa indirme başlamaz).
* Manifestte bildirilmeyen veya Release'te yayımlanmayan dosya **çalıştırılmaz**.
* **Gömülü token/parola/anahtar YOKTUR**; kimlik doğrulama istenmez. Genel API
  limiti aşılırsa (`403/429`, `X-RateLimit-Remaining: 0`) durum **`rate_limit`**
  olarak raporlanır.
* Model dosyası **veri** olarak işlenir (kod yürütülmez); yine de dosya yalnızca
  doğrulandıktan sonra etkinleştirilir.

### 11.4 Arayüz

`Ayarlar → Model Güncellemeleri` (tam ekran, geri tuşu destekli):

* **Yüklü Model**: sürüm, kaynak ("uygulamayla gelen sürüm" / "indirilmiş sürüm"),
  model adı, 5K sınıflandırıcı durumu.
* **Sunucudaki Sürüm**: son kontrol zamanı, en son uyumlu sürüm, dürüst mesaj,
  **"Güncellemeleri kontrol et"** düğmesi.
* Yeni sürüm varsa: sürüm, **boyut**, en az uygulama sürümü, tokenizer, mimari,
  sürüm notları ve **"İndir ve yükselt"** (onay) + "yalnızca bu düğmeye basınca indirilir"
  notu.
* İşlem sürerken: aşama (İndiriliyor/Doğrulanıyor/Etkinleştiriliyor), **yüzde**,
  inen/toplam/kalan, **iptal**.
* Sonuç kartı: tamamlandı / başarısız (**geri alındı** bilgisiyle) / iptal edildi.
* **"Önceki modele dön"** (yedek varsa etkin).
* **Otomatik kontrol** anahtarı (varsayılan açık): **günde en fazla bir kez yalnızca
  küçük metadata** ister; **asla kendiliğinden indirmez**.
* **Güvenlik ve Gizlilik** listesi.

Model güncellemesi, **uygulama güncellemesi ile karıştırılmaz** (başlıkta yazar).

### 11.5 Bu turda çalıştırılan testler (gerçek sonuçlar)

| Test | Komut | Sonuç |
|---|---|---|
| Tüm Python testleri | `python3 -m unittest discover -s tests` | **162 test — OK** (önceki 92 korundu, +70 yeni) |
| Güncelleme testleri | `python3 -m unittest tests.test_model_updater` | **70 test — OK** |
| Canlı GitHub API (opt-in) | `AWU_LIVE_UPDATE_TEST=1 python3 -m unittest tests.test_model_updater.TestLiveGitHub` | **OK** (`reason=no_published_model`) |
| Kabul senaryoları | `python3 examples/demo.py` | **19/19 — OK** |
| Derleme | `gradle :app:assembleDebug` | **BUILD SUCCESSFUL** (uyarı yok) |

Zorunlu senaryolar (`tests/test_model_updater.py`, sahte taşıma katmanı):

| # | Senaryo | Test | Sonuç |
|---|---|---|---|
| 1 | Yeni sürüm var | `test_01_yeni_surum_var` | ✅ |
| 2 | Yeni sürüm yok | `test_02_yeni_surum_yok`, `test_02b_daha_eski_surum_yayinda` | ✅ |
| 3 | İnternet yok | `test_03_internet_yok` (+ yerel model çalışmaya devam eder) | ✅ |
| 4 | İndirme yarıda kesildi | `test_04_indirme_yarida_kalir` (`.part` temizlenir) | ✅ |
| 5 | SHA-256 uyuşmazlığı | `test_05_sha256_uyusmaz`, `test_05b_indirilen_boyut_uyusmaz` | ✅ |
| 6 | Uyumsuz biçim | `test_06_bicim_uyumsuz_dosya` (+ manifest biçim denetimi) | ✅ |
| 7 | Disk alanı yetersiz | `test_07_disk_alanı_yetersiz` (indirme hiç başlamaz) | ✅ |
| 8 | Yeni model yüklenemez | `test_08_yeni_model_yuklenemez_geri_donulur` | ✅ |
| 9 | Geri dönüş başarılı | `test_09_onceki_modele_geri_donme` | ✅ |
| 10 | Yeniden başlatmada doğru model | `test_10_yeniden_baslatmada_dogru_model` (+ 4 varyant) | ✅ |

Ek güvenlik/politika testleri: izin listesi & HTTPS, gömülü `..` ad reddi, manifest
alan denetimi, Release varlık adı/adres uyuşmazlığı, `min_app_version`, API limiti,
HTTP 403/500 çevirisi, iptal, ilerleme, 24 saat önbelleği, otomatik kontrolün indirme
başlatmaması, atomik durum yazımı, bozuk durum dosyasına güvenli varsayılan, köprü
(`AB.configure_models`/`update_*`) uçtan uca, yayımlama aracı ↔ motor uyumu.

### 11.6 Cihazda gerçekten doğrulananlar (emülatör, API 34 x86_64)

| Adım | Sonuç |
|---|---|
| `INTERNET` izni APK'da | ✅ `uses-permission: android.permission.INTERNET` |
| Açılışta **otomatik kontrol** (gerçek GitHub API, Chaquopy) | ✅ `ok=true`, `reason=no_published_model`, dürüst mesaj |
| **Manuel kontrol** (ağ açık) | ✅ yeşil mesaj, "Son kontrol: az önce", "En son uyumlu sürüm: —" |
| **Uçak modu** kontrol | ✅ `Ağ hatası: sunucuya ulaşılamadı…` + **yerel model bozulmadı** (`5K-1.0.0`, `source=bundled`, `pending=null`) |
| Durum dosyası cihazda | ✅ `files/awu_models/model_state.json` yazıldı |
| Sohbet/kod üretimi (güncelleme sonrası) | ✅ kod üretildi, AwuGuard geçti (regresyon yok) |
| Çökme/istisna (logcat) | ✅ kritik hata yok |
| APK içi ağırlık dosyası | ✅ kaynakla **byte-aynı** (`7e434691…`) |
| APK içi motor | ✅ `assets/chaquopy/app.imy` → `awa_agent/model_updater.pyc` |

Ekran görüntüleri: `android/screenshots/10_model_guncelleme.png`,
`11_model_kontrol.png`, `12_cevrimdisi_kontrol.png`,
`13_model_kontrol_online.png`, `14_model_kontrol_cevrimdisi.png`.

### 11.7 Test EDİLMEYENLER (dürüstçe)

* **Gerçek bir Release'ten indirme yapılmadı** — çünkü
  `github.com/Awulokune/AwuGokturk-Android` deposunda **henüz yayımlanmış bir sürüm
  yoktur** (canlı kontrol bunu doğruladı: `no_published_model`). İndirme → doğrulama
  → etkinleştirme → geri dönüş zinciri **sahte taşıma katmanıyla** host'ta uçtan uca
  test edilmiştir; **gerçek Release ile denenmemiştir**.
* Gerçek cihazda **başarılı bir yükseltme** (ağırlık değişimi) gösterilemedi; yalnızca
  "yayımlanmış sürüm yok" ve "ağ hatası" yolları cihazda görüldü.
* Uygulama indirme sırasında **gerçekten öldürülüp** yeniden başlatılmadı (bu yol
  birim testlerinde `pending` + `.part` temizliği ile doğrulandı).
* Ölçüm: gerçek indirme hızı/süresi ölçülmedi (indirilecek yayımlanmış dosya yok).
* Fiziksel telefonda test edilmedi (kullanıcı onayı olmadan cihaza dokunulmadı).

---

## Dürüstlük özeti

- Hiçbir sonuç "halüsinasyonsuz" veya "%100 doğru" olarak sunulmaz.
- Derleme doğrulaması **host sözdizimidir**, gerçek derleme değildir.
- Donanım testi **yapılmadı**; üretilen kod örnek niteliğindedir.
- Sohbet/kavram yanıtları **kural tabanlı yerel bilgi kaynağından** gelir; 5K modeli
  genel sohbet için kullanılmaz.
- 5K modeli genel kod üretim modeli **değildir**.
- Mevcut model/veri/deneyler **korunmuştur**; hiçbir checkpoint üzerine yazılmadı.
- HTTP sunucusu modülü **yoktur**; sunucu istekleri desteklenmiyor olarak reddedilir.
- Model güncelleme sistemi **gerçek yayımlanmış bir sürümle denenmedi** (depoda Release
  yok); indirme/doğrulama/geri dönüş zinciri **sahte taşıma katmanıyla** host'ta
  test edildi (§11.7).

---

## Android uygulaması — AwuGöktürk (çevrimdışı APK)

**Durum: debug APK gerçekten derlendi.** (Uydurma yok; aşağıdaki yol/ boyut/hash
disk üzerindeki gerçek dosyadan alınmıştır.)

| Öğe | Değer |
|---|---|
| APK | `android/app/build/outputs/apk/debug/AwuGokturk-debug.apk` |
| Boyut | **43.585.994 bayt** (~41,6 MiB) |
| SHA-256 | `38c7dec3fc1240a76b4ff64110c710260e34ba6bf1f583f1d9d9591c8dc29dc0` |
| Paket | `com.awulokune.awugokturk` · sürüm 1.0.0 (versionCode 1) |
| Etiket | `AwuGöktürk` (başlatıcı: `com.awulokune.awugokturk.MainActivity`) |
| Simge | `@mipmap/ic_launcher` — **adaptive icon** (API 26+) + legacy PNG'ler |
| minSdk / targetSdk | 24 / 34 |
| ABI | `arm64-v8a`, `x86_64` |
| İzin | `INTERNET` **var** — **yalnızca isteğe bağlı model güncellemesi** için (bkz. §11); sohbet/kod üretimi hâlâ tamamen çevrimdışı |

### Mimari (mevcut kod korunur)

Kotlin + Jetpack Compose arayüz, iş mantığını **yeniden yazmaz**; mevcut Python
paketi `awa_agent/` **Chaquopy** ile cihazda çalışır ve Kotlin JSON köprüsüyle
konuşur. `app/build.gradle.kts` içindeki `copyPython` görevi paketi derleme anında
kopyalar; ikinci bir doğruluk kaynağı oluşturulmaz.

* Ekranlar: **Sohbet** (asistan kimliği + model sürümü başlığı, çevrimdışı
  göstergesi, üretim göstergesi, gerçek çok oturumlu yerel geçmiş), **Kod** (kart
  seçimi, doğal dil, renklendirilmiş C++, kopyala/paylaş, kart/pin/zamanlama,
  **derleme** ve **gerçek donanım testi** ayrı ayrı), **AwuGuard** (mevcut güvenlik
  kontrolleri + "geçmek doğruluk kanıtı değildir"), **Ayarlar** (tema, model
  bilgisi, çevrimdışı durum, geçmişi temizle, gizlilik, sürüm).
* Model: `AwuGöktürk-Microcontroller:5K`.

### Arayüz yenilemesi ve uygulama ikonu (2026-10-17) — ayrıntı §10

Arayüz **yeniden tasarlandı** (yalnızca renk değişimi değil): gerçek bir AI asistanı
sohbeti hiyerarşisi, mesaj sunumu, giriş alanı ve gezinme bütün olarak elden
geçirildi. Kullanıcının verdiği görsel **gerçek uygulama ikonu** (adaptive + legacy)
ve **uygulama içi asistan avatarı/logo** olarak entegre edildi.

### 5K modeli cihazda (torch YOK)

PyTorch Android'de yoktur. Bu yüzden **doğrulanmış** bir dönüşüm yolu kullanıldı:

1. `tools/export_classifier5k.py` — `experiments_v2/exp_B_classification/model.pt`
   (**salt-okunur**) → `android/app/src/main/assets/classifier5k.json` (~100 KB).
2. `awa_agent/classifier5k_lite.py` — aynı mimariyi (Embedding→GRU→Linear) **saf
   Python** ile uygular.
3. `tests/test_android_bridge.py::test_lite_matches_torch` — saf-Python çıkarımı
   PyTorch ile **aynı etiket** ve **< 1e-3** olasılık farkı verir (ölçülen ~5e-5).

Kotlin, asset'i `filesDir`'a kopyalar ve `set_model_path()` çağırır; model **lite-json**
arka ucuyla, **4.893 parametre** ile yüklenir. 5K yalnızca **ipucu** olarak kullanılır.

### Adlandırma (kullanıcı kuralı uygulandı)

* Asistan/uygulama adı: **AwuGöktürk**.
* Model adı: **AwuGöktürk-Microcontroller:5K**.
* Model artık **"AwuGöktürk Embedded Agent" olarak adlandırılmaz**; bu ifade yalnızca
  eski bir tetikleyici olarak tanınır ve kimlik yanıtlarında geçmez
  (`tests/test_android_bridge.py::test_identity_names_model_correctly`).

### Bulunan ve düzeltilen gerçek hata

`requirement_parser._interval_ms` saniye ifadelerini yalnızca `(saniye|sn|s)\b` ile
yakalıyordu; Türkçe **hal eki** almış **"saniyede"** biçiminde `\b` başarısız oluyor ve
süre **500 ms varsayılanına düşüyordu** — yani istenen "500 ms vs 5000 ms karışmaması"
kuralı ihlal ediliyordu. Düzeltildi:

* Öncesi: `"5 saniyede bir"` → `INTERVAL_MS = 500` ❌
* Sonrası: `"5 saniyede bir"` → `INTERVAL_MS = 5000` ✅ (ve `"500 ms"` → `500` ✅)

Doğrulama, **APK içindeki gerçek bytecode** (`assets/chaquopy/app.imy`) doğrudan
içe aktarılarak yapıldı.

### Testler (bu teslimattaki gerçek sonuçlar)

```bash
cd embedded_agent
python3 -m unittest discover -s tests      # 162 test — hepsi GEÇTİ (1 atlandı: canlı ağ)
python3 examples/demo.py                   # 19/19 senaryo GEÇTİ
# Android çalışma zamanı simülasyonu (Python 3.11, torch YOK):
/home/aras/tools/python311/bin/python3 -m unittest discover -s tests   # 162 test (torch paritesi atlanır)
```

* `tests/test_model_updater.py` **(yeni)** — model güncelleme motoru: 10 zorunlu
  senaryo + izin listesi/manifest/limit/iptal/kilitlenme güvenliği. **70 test.**
* `tests/test_arduino_accuracy.py` — istenen **beş** doğruluk senaryosu (süre 5000 ms;
  A0↔14 etiket/numara; Uno Wi-Fi reddi; ESP32 HTTP GET kapsamı; bilinmeyen özellikte
  kod uydurulmaması). **12 test, hepsi geçti.**
* `tests/test_android_bridge.py` — köprü + lite paritesi + adlandırma. **13 test.**
* Önceki testler **silinmedi/zayıflatılmadı**; tamamı hâlâ geçiyor.

### Emülatörde çalıştırma testi (GERÇEK — yapıldı)

`/dev/kvm` bulunduğu için başsız (headless) bir **Android 14 (API 34, x86_64)**
emülatörü kurulup APK gerçekten çalıştırıldı (`android/emulator_test.sh`):

| Adım | Sonuç |
|---|---|
| `adb install` | **Success** |
| `am start` MainActivity | **Status: ok** (COLD, ~4,4 sn) |
| Süreç ayakta | **Evet** (`pidof` döndü) |
| Python/Chaquopy başladı | **Evet** |
| Boş sohbet (yeni tasarım) | ✅ logo + "Merhaba, ben AwuGöktürk." + 4 örnek istem + giriş alanı |
| Örnek istem → sohbette kod | ✅ balonlar + **kod kartı** (Kopyala/Paylaş) + AwuGuard etiketi |
| Geçmiş paneli | ✅ alt sayfa; oturum aç/sil; eski `chat_history.json` içe aktarıldı |
| Kod sekmesi | ✅ kart seçimi + gerçek üretim (`kod üretildi`, `INTERVAL_MS = 5000`) |
| Ayarlar | ✅ "5K sınıflandırıcı — yüklü (4893 parametre)" |
| Başlatıcı ikonu | ✅ uygulama çekmecesinde **dairesel maskede okunaklı** |
| **Uçak modu (ağ YOK)** | ✅ `Active default network: none` iken sohbet/kod **çalışmaya devam etti** |
| **Model Güncellemeleri ekranı** | ✅ açıldı; "Yüklü Model", "Sunucudaki Sürüm", "Önceki Modele Dön", "Otomatik Kontrol", "Güvenlik ve Gizlilik" bölümleri |
| **Gerçek GitHub kontrolü (ağ açık)** | ✅ `no_published_model` — dürüst mesaj, "En son uyumlu sürüm: —" |
| **Uçak modunda kontrol** | ✅ "Ağ hatası: sunucuya ulaşılamadı…"; **yerel model bozulmadı** |

Ekran görüntüleri: `android/screenshots/` (`01_sohbet_bos`, `02_sohbet_kod`,
`03_gecmis`, `04_kod_bos`, `05_kod_sonuc`, `06_ayarlar`, `07_ana_ekran`,
`08_uygulama_cekmecesi`, `09_cevrimdisi`, `10_model_guncelleme`,
`11_model_kontrol`, `12_cevrimdisi_kontrol`, `13_model_kontrol_online`,
`14_model_kontrol_cevrimdisi`).

> Bu, APK'nın gerçekten **açıldığını** ve **gerçek 5K modelinin cihazda yüklendiğini**
> kanıtlar. **Fiziksel telefonda test edilmedi**: ortamda bağlı bir telefon (Redmi Note 8
> Pro) vardı ancak **kullanıcı onayı olmadan cihaza dokunulmadı**; test yalnızca emülatörde
> yapıldı.

### Test EDİLMEYENLER (dürüstçe)

* **Gerçek donanım derlemesi/yüklemesi yapılmadı** (cihaz/`arduino-cli`/`avr-gcc` yok).
  Bu yüzden derleme ve donanım testi arayüzde ayrı ayrı ve "yapılmadı" olarak gösterilir.
* 5K modeli **genel sohbet/kod üretimi** için değildir; yalnızca sınıflandırma ipucudur.
* HTTP sunucusu (WebServer) modülü **desteklenmez**.
* APK iki ABI ile sınırlıdır (`arm64-v8a`, `x86_64`).

Derleme/detay talimatları: **`android/README_ANDROID.md`**.
