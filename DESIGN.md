# AwuGöktürk Embedded Agent AI — Tasarım ve Kapsam

Bu belge, mevcut `awu-gokturk-coder-5k` projesinin üzerine kurulan **modüler
gömülü sistem kodlama ajanının** mimarisini, kart desteğini ve dürüst kapsam
sınırlarını tanımlar. Tüm yeni kod `embedded_agent/` altındadır; mevcut
`model.pt`, veri setleri, `experiments/` ve `experiments_v2/` **değiştirilmez**.

## 1. Mevcut projenin durumu (incelendi)

- **Veri seti:** `train.jsonl` 4000 / `validation.jsonl` 500 / `test.jsonl` 500;
  kategoriler: `c_basics, cpp_basics, arduino, code_explain_complete, debug_fix,
  turkish_qa, uncertainty`.
- **Üretim modeli:** `model/checkpoints/best_fp32.pt` — char-level GRU, 4.990
  parametre, **serbest üretimde başarısız** (v1/v2 raporları: tam eşleşme %6,8;
  kod derlenebilirliği %0).
- **5K sınıflandırıcı:** `experiments_v2/exp_B_classification/model.pt` —
  `Embedding(103→8) → GRU(8→31) → Linear(31→8)`, **4.893 parametre**, 8 sınıf
  (`kod_cikti, kavram_sorusu, arduino_dijital, arduino_analog, hata_bulma,
  sinif_uye_metot, bellek_isaretci, sinif_tanimlama`); kendi test dağılımında
  doğruluk %93,4. **Yalnızca görev-türü sinyali olarak** kullanılır.
- **Araç zinciri:** `gcc/g++` 16.2 var; **`arduino-cli`, `avr-gcc`, `platformio`
  YOK.** Bu nedenle gerçek AVR/ESP32 derlemesi yapılamaz.

### 5K modelinin rolü (dürüst sınır)

5K sınıflandırıcı **yalnızca Arduino Uno odaklı görev-türü sınıflandırıcısıdır.**
- ESP32/Mega için *çalışan* bir model değildir; bu kartlar için yalnızca **kod
  üretilir**.
- Genel amaçlı kod üretim modeli **değildir**; genel kod üretimi kurallar,
  doğrulanmış bilgi kaydı (registry) ve şablonlarla yapılır.
- Çıktısı bir **ipucu** olarak kullanılır; kesin doğruluk kanıtı sayılmaz
  (softmax güveni kanıt değildir).

## 2. Modüler mimari

```
awa_agent (paket)
  agent.py               -> AwuGokturkAgent: tüm boru hattını yönetir
  intent_router.py       -> Intent Router (kural + 5K sinyali)
  board_resolver.py      -> Board Resolver (kart/varyant/framework, eksikse sorar)
  requirement_parser.py  -> Requirement Parser (yapılandırılmış gereksinimler)
  knowledge_registry.py  -> Knowledge/Library Registry (modül+kütüphane API kaydı)
  code_generator.py      -> Code Generator (kart profiline göre tam program)
  awu_guard.py           -> AwuGuard (pin/API/kütüphane/çakışma/eksik kontrolü)
  build_validator.py     -> Build Validator (host syntax derleme; arduino-cli yok)
  test_generator.py      -> Test Generator (mantık+derleme testi, donanım planı)
  response_handler.py    -> Response Handler (kod+açıklama+bağımlılık+doğrulama)
  classifier5k.py        -> Mevcut 5K sınıflandırıcıyı yükler (salt-okunur)
  boards/                -> Kart profilleri (bağımsız, genişletilebilir)
    base.py              -> BoardProfile + pin doğrulama altyapısı
    arduino_uno.py, arduino_mega2560.py, esp32.py
    __init__.py          -> kayıt (registry)
  stubs/                 -> Host derleme için Arduino/ESP32 başlık taklidi
```

**Genişletilebilirlik:** Yeni kart = `boards/` altına yeni bir `BoardProfile`
döndüren modül + `register()`. Çekirdek kod değişmez. RP2040 vb. bu yolla
eklenebilir (şu an kapsam dışı).

## 3. Kart profilleri (doğrulanmış sınırlar)

| | Arduino Uno R3 | Arduino Mega 2560 | ESP32 (klasik, WROOM-32) |
|---|---|---|---|
| MCU | ATmega328P | ATmega2560 | ESP32-D0WD |
| Dijital | 0–13 | 0–53 | GPIO 0–39 (kısıtlı) |
| Analog giriş | A0–A5 (14–19) | A0–A15 (54–69) | ADC1: 32–39; ADC2: 0,2,4,12–15,25–27 |
| PWM | 3,5,6,9,10,11 | 2–13,44,45,46 | LEDC: tüm çıkış GPIO'ları |
| Kesme | 2,3 | 2,3,18,19,20,21 | tüm giriş GPIO'ları |
| UART | Serial(0,1) | Serial(0,1),1(19,18),2(17,16),3(15,14) | UART0(1,3), UART2(16,17) |
| I2C | A4,A5 | 20,21 | 21,22 (varsayılan) |
| Gerilim | 5 V | 5 V | **3,3 V (5V toleranslı değil)** |
| Kullanılamaz | — | — | 6–11 (flash), 34–39 giriş-only |

ESP32 varyantları (S2/S3/C3/S1) **desteklenmez**; istek gelirse dürüstçe
belirtilir ve model bilgisi istenir. "ESP32" denip varyant belirtilmezse
**klasik ESP32 varsayıldığı açıkça bildirilir**.

## 4. Desteklenen modüller (registry tabanlı)

İlk sürümde **doğrulanmış** modüller: dijital LED (sabit/blink), buton+debounce,
iki buton+iki LED, analog okuma→seri (potansiyoter/LDR), PWM fade, servo,
HC-SR04 ultrasonik mesafe, buzzer/tone, DHT sıcaklık-nem, ESP32 Wi-Fi bağlantı,
ESP32 HTTP (GET/POST). Çok modüllü birleşim ve pin çakışma kontrolü desteklenir.

**Desteklenmeyen/uyarılan:** tanınmayan sensör/modül, ESP32 varyantları, ağ
görevlerinde Uno/Mega, doğrulanmamış kütüphaneler → **kod uydurulmaz**, açık
ret veya net soru.

Tam durum tablosu çalışma zamanında `awa_agent/response_handler.py` içindeki
`support_matrix()` ile üretilir ve rapora yazılır.

## 5. AwuGuard kontrolleri

Geçersiz/kullanılamaz pin, istenen pinin değiştirilmesi, pin çakışması, çıkış
pinine analog okuma, giriş-only pine yazma, PWM olmayan pinde analogWrite, ADC2
pininin Wi-Fi ile kullanımı, tanımsız sembol, eksik `#include`, kart-kütüphane
uyumsuzluğu, eksik zorunlu parametre (örn. HTTP URL), belirsiz/çelişkili
gereksinim, desteklenmeyen donanım özelliği.

## 6. Build doğrulama (dürüst sınır)

- Gerçek `arduino-cli`/`avr-gcc` **yok** → AVR/ESP32 hedef derlemesi yapılamaz.
- Yapılabilen: **host syntax doğrulaması** — `g++ -fsyntax-only` ile, Arduino
  API'sini ve kullanılan kütüphaneleri taklit eden stub başlıklarla.
- Bu, *gerçek donanım derlemesi değildir*; her yanıtta böyle etiketlenir.

## 7. Veri seti ve eğitim planı

- Yeni şema: `data_agent/schema.md` (Türkçe komut, eşdeğer ifadeler, kart/
  framework, yapılandırılmış gereksinim, beklenen kod, geçerli/geçersiz pin,
  eksik/çelişkili gereksinim, hata ayıklama, desteklenmeyen istek+ret,
  derleme/test sonucu) ve `tools/generate_agent_dataset.py` ile **küçük örnek**
  veri üretimi (train/val/test ayrık, sızıntısız).
- **Eğitim başlatılmaz.** Daha büyük model seçenekleri ve donanım maliyetleri
  `REPORT.md`'de raporlanır; onay olmadan eğitim yapılmaz.

## 8. Test planı

`tests/` altında: kart profilleri, pin doğrulama, intent yönlendirme,
gereksinim ayrıştırma, AwuGuard, kod üretimi, uçtan uca kabul senaryoları
(bkz. `tests/README.md`). Testler `pytest` ve bağımsız betikle çalıştırılır.
