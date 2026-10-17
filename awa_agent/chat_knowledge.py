"""Sohbet ve kavram bilgi kaynagi (Turkce).

Bu modul AwuGöktürk'un **sohbet / kavram aciklama** katmanidir.
Yalnizca burada tanimli, dogrulanmis konular aciklanir; kapsam disi sorulara
cevap UYDURULMAZ (bkz. `concept_miss_message`).

Tasarim ilkeleri:
  * Kural tabanli, yerel ve seffaf: 5K modeli bu katmanda KULLANILMAZ.
  * Anahtar kelimeler ASCII'ye indirgenmis (Turkce karakterler sadelesir) halde
    saklanir; arama da ayni sekilde normalise edilir.
  * Yeni konu eklemek = yeni bir `Topic` kaydi; cekirdek kod degismez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜâÂîÎûÛ", "cgiosuCGIOSUaAiIuU")


def norm(text: str) -> str:
    return text.translate(_TR_MAP).lower()


@dataclass
class Topic:
    key: str
    title: str
    keywords: list            # normalise (kucuk harf, Turkce karaktersiz) anahtar sozcukler
    answer: str
    related: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Konular (dogrulanmis, Turkce)
# ---------------------------------------------------------------------------
TOPICS: list[Topic] = [
    Topic(
        "cpu", "Islemci (CPU)",
        ["cpu", "islemci", "mikroislemci", "merkezi islem birimi"],
        "İşlemci (CPU – Merkezî İşlem Birimi), bir bilgisayarın komutları yürüten ana "
        "birimidir. Çalışması kısaca şu döngüye dayanır: komutu bellekten getirir "
        "(fetch), çözümler (decode) ve yürütür (execute); sonucu gerekirse yazmaçlara ya "
        "da belleğe yazar. Saat frekansı (örneğin 3 GHz) saniyedeki çevrim sayısını, "
        "çekirdek sayısı ise aynı anda yürütülebilen bağımsız iş akışı sayısını belirtir. "
        "Arduino/ESP32 gibi gömülü sistemlerde de benzer bir işlemci çekirdeği bulunur "
        "(Uno/Mega'da AVR, klasik ESP32'de Xtensa); ancak bellek ve saat hızı çok daha "
        "küçüktür.",
        related=["RAM", "işletim sistemi"],
    ),
    Topic(
        "ram", "Bellek (RAM)",
        ["ram", "rastgele erisimli bellek", "ana bellek", "gecici bellek"],
        "RAM (Rastgele Erişimli Bellek), işlemcinin çalışma sırasında geçici olarak veri "
        "ve program tuttuğu hızlı bellektir. Uçucudur: güç kesildiğinde içeriği silinir. "
        "Kalıcı veri için disk/SSD (ya da Arduino'da EEPROM/flash) kullanılır. RAM "
        "büyüklüğü, aynı anda çalıştırılabilecek program ve veri miktarını sınırlar. "
        "Örneğin Arduino Uno'da yalnızca 2 KB SRAM vardır; bu yüzden büyük dizilerden ve "
        "String birleştirmelerden kaçınılmalıdır.",
        related=["CPU", "işletim sistemi"],
    ),
    Topic(
        "gpu", "Grafik islemci (GPU)",
        ["gpu", "ekran karti", "grafik islemci", "grafik birimi"],
        "GPU (Grafik İşlem Birimi / ekran kartı), görüntü ve matris işlemlerini çok "
        "sayıda küçük çekirdekle aynı anda (paralel) yapan birimdir. CPU az sayıda güçlü "
        "çekirdekle sıralı işlere, GPU ise binlerce basit çekirdekle paralel işlere "
        "uygundur. Bu nedenle görüntü işleme ve yapay zekâ gibi yoğun hesaplarda tercih "
        "edilir. Arduino/ESP32 sınıfı kartlarda ayrı GPU bulunmaz.",
        related=["CPU", "RAM"],
    ),
    Topic(
        "os", "Isletim sistemi",
        ["isletim sistemi", "operating system", "windows", "linux", "macos", "isletim"],
        "İşletim sistemi (OS), donanım ile uygulamalar arasında aracı olan yazılımdır. "
        "İşlemci zamanını (süreç/zamanlama), belleği, dosyaları ve çevre birimlerini "
        "(sürücüler aracılığıyla) yönetir. Örnekler: Windows, Linux, macOS. "
        "Arduino/ESP32 gibi kartlarda genellikle tam bir işletim sistemi yoktur; kod "
        "doğrudan donanım üzerinde (bare-metal) ya da FreeRTOS gibi hafif bir çekirdekle "
        "çalışır.",
        related=["CPU", "RAM"],
    ),
    Topic(
        "arduino_vs_esp32", "Arduino ve ESP32 farki",
        ["arduino ve esp32", "arduino ile esp32", "esp32 ve arduino",
         "arduino-esp32", "arduino ile esp32 arasindaki fark"],
        "Arduino ve ESP32 farklı sınıflardır. Arduino Uno R3 (ATmega328P) 8 bit, 16 MHz, "
        "yaklaşık 2 KB SRAM ve 14 dijital / 6 analog girişe sahiptir; dahili Wi-Fi veya "
        "Bluetooth yoktur. Arduino Mega 2560 (ATmega2560) daha çok pin ve bellek sunar. "
        "Klasik ESP32 ise 32 bit çift çekirdeklidir, çok daha yüksek hızda çalışır ve "
        "dahili Wi-Fi + Bluetooth içerir; lojik seviyesi 3,3 V'tur. Kısaca: basit "
        "giriş/çıkış işleri için Uno/Mega yeterlidir; ağ (Wi-Fi/BLE) veya daha fazla "
        "işlem gücü gerektiğinde klasik ESP32 uygundur. Pin numaraları ve gerilim "
        "seviyeleri kartlar arasında farklıdır.",
        related=["dijital giriş/çıkış", "ADC", "PWM"],
    ),
    Topic(
        "digital_io", "Dijital giris/cikis",
        ["dijital giris/cikis", "dijital giris-cikis", "dijital giris cikis",
         "dijital giris", "dijital cikis", "dijital sinyal", "dijital pin"],
        "Dijital giriş/çıkış, bir pinin iki durumundan (LOW = 0 veya HIGH = 1) yararlanır. "
        "Çıkış olarak kullanıldığında pin, bağlı elemana gerilim uygular (örneğin LED "
        "yakmak için HIGH). Giriş olarak kullanıldığında pin, dışarıdan gelen 0/1 "
        "seviyesini okur (örneğin buton). Arduino'da yön `pinMode(pin, OUTPUT / INPUT / "
        "INPUT_PULLUP)` ile belirlenir; `digitalWrite` yazar, `digitalRead` okur.",
        related=["ADC", "PWM"],
    ),
    Topic(
        "adc", "ADC (Analog-Dijital Cevirici)",
        ["adc", "analog-dijital", "analog dijital cevirici", "analog okuma",
         "analogread", "analog giris"],
        "ADC (Analog-Dijital Çevirici), sürekli bir analog gerilimi sayısal bir değere "
        "dönüştürür. Arduino Uno'da `analogRead` 0–1023 arası (10 bit) değer verir ve "
        "genelde 0–5 V ölçülür; klasik ESP32'de ise 0–4095 (12 bit) ve referans gerilimi "
        "yaklaşık 3,3 V'tur. Örnek: 5 V referansta ölçülen 2,5 V, Uno'da yaklaşık 512 "
        "değerine karşılık gelir. Bazı ESP32 pinleri yalnızca giriş (input-only) olarak "
        "kullanılabilir.",
        related=["dijital giriş/çıkış", "PWM"],
    ),
    Topic(
        "pwm", "PWM (Darbe Genisligi Modulasyonu)",
        ["pwm", "darbe genisligi", "analogwrite", "parlaklik kontrolu"],
        "PWM (Darbe Genişliği Modülasyonu), bir dijital çıkışı çok hızlı açıp kapatarak "
        "ortalama gerilimi ayarlar. Görev döngüsü (duty cycle) arttıkça ortalama gerilim, "
        "dolayısıyla LED parlaklığı veya motor hızı artar. AVR tabanlı Arduino'larda "
        "`analogWrite` 0–255 arası değer alır ve yalnızca PWM destekli pinlerde çalışır "
        "(Uno: 3, 5, 6, 9, 10, 11). Klasik ESP32'de PWM, LEDC donanımıyla "
        "(`ledcSetup`/`ledcWrite`) üretilir ve neredeyse tüm çıkış pinlerinde "
        "kullanılabilir.",
        related=["ADC", "dijital giriş/çıkış"],
    ),
    Topic(
        "i2c", "I2C",
        ["i2c", "twi", "sda", "scl"],
        "I2C, iki hatlı (SDA = veri, SCL = saat) senkron seri haberleşme protokolüdür. "
        "Aynı hatta bir ana (master) ve birden çok köle (slave) cihaz bağlanabilir; her "
        "cihazın 7 bitlik bir adresi vardır. Az kablo gerektirir, hızı görece düşüktür "
        "(tipik 100–400 kbit/s). Arduino Uno'da SDA = A4, SCL = A5; Mega 2560'ta SDA = 20, "
        "SCL = 21'dir. LCD, RTC ve birçok sensör I2C kullanır.",
        related=["SPI", "UART"],
    ),
    Topic(
        "spi", "SPI",
        ["spi", "miso", "mosi", "sck", "ss hatti"],
        "SPI, dört hatlı (SCK = saat, MOSI = ana→köle, MISO = köle→ana, SS/CS = seçim) "
        "senkron seri protokolüdür. I2C'ye göre daha hızlıdır ve tam çift yönlüdür; ancak "
        "her köle için ayrı bir SS hattı gerekir. Ekranlar, SD kartlar ve yüksek hızlı "
        "sensörlerde sık kullanılır.",
        related=["I2C", "UART"],
    ),
    Topic(
        "uart", "UART",
        ["uart", "seri haberlesme", "seri port", "seri iletisim", "baud"],
        "UART, iki hatlı (TX = gönderim, RX = alım) asenkron seri haberleşmedir. Ortak "
        "bir saat hattı yoktur; iki taraf önceden aynı baud hızını (örneğin 9600 veya "
        "115200) kullanmalıdır. Arduino'da bilgisayarla haberleşme `Serial` (UART0) "
        "üzerinden yapılır; Mega 2560 ek olarak Serial1/2/3, klasik ESP32 ise Serial ve "
        "Serial2 sunar.",
        related=["I2C", "SPI"],
    ),
    Topic(
        "http_server_client", "HTTP sunucusu ve istemcisi farki",
        ["http sunucu", "http istemci", "http server", "http client",
         "sunucu ile istemci", "istemci ile sunucu", "sunucu ve istemci"],
        "HTTP'de istemci (client) ve sunucu (server) iki ayrı roldür. İstemci, isteği "
        "başlatan taraftır: bir adrese (URL) bağlanıp GET/POST isteği gönderir ve dönen "
        "yanıtı okur. Sunucu ise gelen istekleri bekleyen, karşılayan ve yanıt üreten "
        "taraftır: belirli bir portu dinler (örneğin 80) ve istek yoluna göre cevap "
        "döner. Klasik ESP32'de istemci için `HTTPClient` (http.begin + http.GET), sunucu "
        "için `WebServer` sınıfı kullanılır. Yani 'sunucudan veri çekmek' ile 'sunucu "
        "oluşturmak' birbirinden farklı işlerdir ve aynı kodla yapılmaz. Önemli not: bu "
        "ajan şu anda ESP32 için HTTP **istemcisi** kodu üretir; HTTP **sunucusu** "
        "(WebServer) modülü desteklenmemektedir.",
        related=["UART", "Arduino ve ESP32 farkı"],
    ),
    Topic(
        "math", "Temel matematik",
        ["matematik", "ortalama", "yuzde", "oran", "denklem", "karekok", "us alma"],
        "Temel matematik kavramları: **ortalama**, bir değer kümesinin toplamının eleman "
        "sayısına bölümüdür: (a + b + … + n) / n. **Yüzde**, bir oranı 100 üzerinden "
        "ifade eder; bir sayının %20'si, o sayının 0,20 ile çarpımıdır. **Denklem** "
        "çözmede amaç bilinmeyeni yalnız bırakmaktır (örneğin 2x + 3 = 11 → x = 4). "
        "Gömülü sistemlerde ADC ortalama alma, ölçekleme (0–1023 → 0–255 gibi) ve oran "
        "hesapları sık kullanılır.",
        related=["fizik"],
    ),
    Topic(
        "physics", "Temel fizik / elektrik",
        ["fizik", "ohm", "gerilim", "akim", "direnc", "guc", "volt", "amper", "watt",
         "kirchhoff"],
        "Temel elektrik bağıntıları: **Ohm yasası** V = I × R (gerilim = akım × direnç). "
        "**Güç** P = V × I (birimi watt). Seri bağlı dirençler toplanır "
        "(R_toplam = R1 + R2 + …); paralel bağlı dirençlerde 1/R_toplam = 1/R1 + 1/R2 + … . "
        "Örnek: 5 V kaynağa 220 Ω direnç bağlanırsa I = V / R = 5 / 220 ≈ 0,023 A "
        "(23 mA) olur. LED'lerde akımı sınırlamak için seri direnç kullanılır.",
        related=["matematik", "ADC"],
    ),
]


def lookup(text: str) -> Topic | None:
    """Metne en iyi uyan dogrulanmis konuyu dondurur; yoksa None (uydurma yok)."""
    n = norm(text)
    best, best_score = None, 0
    for t in TOPICS:
        hits = [k for k in t.keywords if k in n]
        if not hits:
            continue
        score = sum(len(k) for k in hits)
        if score > best_score:
            best, best_score = t, score
    return best


def topic_keys() -> list[str]:
    return [t.key for t in TOPICS]


# ---------------------------------------------------------------------------
# Genel dogrulanmis bilgi (fact) kaynagi
#
# Uydurma YOK: yalnizca burada tanimli, elle dogrulanmis kayitlar yanitlanir.
# Her kayit, birlikte bulunmasi gereken sozcuk gruplarindan olusan bir anahtar
# listesi tasir. Yeni bilgi eklemek = yeni bir Fact kaydi.
# ---------------------------------------------------------------------------
@dataclass
class Fact:
    key: str
    keywords: list            # [ [sozcuk, sozcuk...], ... ] gruplarindan biri tamamen bulunmali
    answer: str


FACTS: list[Fact] = [
    Fact("capital_tr", [["turkiye", "baskent"], ["turkiye", "neresi"], ["ankara"]],
         "Türkiye'nin başkenti **Ankara**'dır."),
    Fact("capital_fr", [["fransa", "baskent"], ["fransa", "neresi"], ["paris"]],
         "Fransa'nın başkenti **Paris**'tir."),
    Fact("capital_de", [["almanya", "baskent"], ["almanya", "neresi"], ["berlin"]],
         "Almanya'nın başkenti **Berlin**'dir."),
    Fact("capital_jp", [["japonya", "baskent"], ["japonya", "neresi"], ["tokyo"]],
         "Japonya'nın başkenti **Tokyo**'dur."),
    Fact("capital_it", [["italya", "baskent"], ["italya", "neresi"], ["roma"]],
         "İtalya'nın başkenti **Roma**'dır."),
    Fact("capital_es", [["ispanya", "baskent"], ["ispanya", "neresi"], ["madrid"]],
         "İspanya'nın başkenti **Madrid**'tir."),
    Fact("capital_uk", [["ingiltere", "baskent"], ["birlesik krallik", "baskent"],
                        ["londra"]],
         "Birleşik Krallık'ın başkenti **Londra**'dır."),
    Fact("capital_us", [["abd", "baskent"], ["amerika birlesik devletleri", "baskent"],
                        ["washington"]],
         "ABD'nin başkenti **Washington, D.C.**'dir."),
    Fact("capital_ru", [["rusya", "baskent"], ["rusya", "neresi"], ["moskova"]],
         "Rusya'nın başkenti **Moskova**'dır."),
    Fact("capital_gr", [["yunanistan", "baskent"], ["atina"]],
         "Yunanistan'ın başkenti **Atina**'dır."),
    Fact("ocean_largest", [["en buyuk okyanus"], ["buyuk okyanus"]],
         "Dünya'nın en büyük okyanusu **Pasifik Okyanusu**'dur."),
    Fact("mountain_highest", [["en yuksek dag"], ["everest"]],
         "Dünya'nın en yüksek dağı **Everest**'tir (8.848 m)."),
]


def lookup_fact(text: str) -> Fact | None:
    """Metne uyan dogrulanmis genel bilgiyi dondurur; yoksa None (uydurma yok)."""
    n = norm(text)
    for f in FACTS:
        for group in f.keywords:
            if all(w in n for w in group):
                return f
    return None


# ---------------------------------------------------------------------------
# Kimlik tespiti: kullanici yalnizca adi (veya ad + agent) yazabilir
# ---------------------------------------------------------------------------
_KEEP_ALNUM = re.compile(r"[^a-z0-9]+")
_NAME_ONLY_RE = re.compile(r"^(awu\s*)?gokturk(\s+embedded)?(\s+agent)?$")


def _name_core(text: str) -> str:
    return " ".join(_KEEP_ALNUM.sub(" ", norm(text)).split())


def is_name_only(text: str) -> bool:
    """Metin, neredeyse yalnizca 'AwuGöktürk [Embedded Agent]' ifadesinden olusuyor mu?"""
    core = _name_core(text)
    return bool(core) and bool(_NAME_ONLY_RE.match(core))


# ---------------------------------------------------------------------------
# Yaratıcı yazarlık: kisa, sabit ornek metinler (genel amacli LLM DEGIL)
# ---------------------------------------------------------------------------
CREATIVE_DISCLAIMER = (
    "Not: Bu, yaratıcı yazarlık için hazırlanmış kısa ve **sabit** bir örnektir. "
    "Genel amaçlı bir dil modeli değilim; bu yüzden istek üzerine sınırsız/yeni "
    "hikâye üretemem."
)

_SCIFI_STORY = (
    "2140 yılında Mars'taki toz fırtınaları dinmeye başladığında teknisyen Elif, "
    "istasyonun eski iletişim panelinde beklenmedik bir sinyal yakaladı. Sinyal, "
    "yörüngedeki terk edilmiş bir uydudan geliyordu ve içinde yalnızca üç kelime "
    "vardı: \"Geri dönmeyin.\" Elif mesajı Dünya'ya iletti; ancak gelen cevap, aynı üç "
    "kelimeyi yineliyordu. O gece istasyonun penceresinden bakan ekip, gökyüzünde "
    "yeni bir yıldız gibi parlayan ve yavaşça yaklaşan bir cismi fark etti."
)

_TALE_STORY = (
    "Küçük bir kasabada, her sabah şehrin saat kulesini kuran yaşlı bir saatçi "
    "yaşardı. Bir gün kurmayı unuttu ve kasaba, zamanın yavaş aktığı tuhaf bir güne "
    "uyandı. İnsanlar acele etmeyi bıraktıkça birbirlerini dinlemeye başladı; akşam "
    "olduğunda saatçi kuleyi yeniden kurdu. Kasaba o günü \"dinleme günü\" olarak "
    "hatırladı."
)


def creative_answer(text: str) -> tuple[str, str]:
    """(mesaj, tur) dondurur. Birkaç sabit ornekten uygun olani secer."""
    n = norm(text)
    if any(w in n for w in ["bilim kurgu", "bilimkurgu", "uzay", "robot", "gelecek",
                            "sci-fi", "scifi"]):
        story = _SCIFI_STORY
    else:
        story = _TALE_STORY
    return story + "\n\n" + CREATIVE_DISCLAIMER, ("bilim_kurgu" if story is _SCIFI_STORY
                                                  else "masal")


# ---------------------------------------------------------------------------
# Kimlik / yetenek / durustluk metinleri
# ---------------------------------------------------------------------------
# ADLANDIRMA KURALI (kullanici karari):
#   * Uygulama/asistan adi  : "AwuGöktürk"
#   * Model adi             : "AwuGöktürk-Microcontroller:5K"
#   * Model ASLA "AwuGöktürk Embedded Agent" olarak ADLANDIRILMAZ.
#   * "AwuGöktürk Embedded Agent" yalnizca eski bir tetikleyici ifade olarak
#     taninir (bkz. _NAME_ONLY_RE); model/uygulama adi olarak kullanilmaz.
IDENTITY_NAME = "AwuGöktürk"
MODEL_NAME = "AwuGöktürk-Microcontroller:5K"
SUPPORTED_BOARDS = "Arduino Uno R3, Arduino Mega 2560 ve klasik ESP32"


def identity_answer(subtype: str = "who") -> str:
    """Kimlik sorularina, sabit tek cumle yerine duruma uygun dogal Turkce yanit."""
    if subtype == "name":
        return (
            "Ben " + IDENTITY_NAME + " adlı gömülü sistem yardımcısıyım. " +
            SUPPORTED_BOARDS + " için kod üretebilir, mevcut kodu inceleyebilir ve temel "
            "bilgisayar/elektronik kavramlarını Türkçe açıklayabilirim. Kullandığım model "
            + MODEL_NAME + "'dir (yaklaşık 5.000 parametreli, yalnızca Arduino Uno için "
            "görev-türü ipucu veren küçük bir sınıflandırıcı); genel amaçlı bir dil modeli "
            "değildir. Size nasıl yardımcı olabilirim?"
        )
    if subtype == "capabilities":
        return (
            "Şunları yapabilirim: (1) Arduino Uno R3, Arduino Mega 2560 ve klasik ESP32 "
            "için desteklenen gömülü kodları üretmek (dijital giriş/çıkış, buton ve "
            "debounce, analog/ADC, PWM, servo, ultrasonik mesafe, buzzer, DHT, I2C LCD, "
            "I2C tarama; klasik ESP32'de ayrıca Wi-Fi ve HTTP istemcisi). (2) Verdiğiniz "
            "kodu inceleyip pin çakışması gibi sorunları bulmak. (3) Eksik bilgide size "
            "soru sormak ve desteklenmeyen istekleri gerekçesiyle reddetmek. (4) CPU, RAM, "
            "GPU, işletim sistemi, ADC, PWM, I2C/SPI/UART ve temel matematik/fizik gibi "
            "konuları Türkçe açıklamak. Kod istediğinizde hedef kartı belirtmeniz yeterli; "
            "sohbet veya kavram sorusunda kart şart değil."
        )
    if subtype == "role":
        return (
            "Görevim gömülü sistem kodlamasına yardımcı olmak: " + SUPPORTED_BOARDS +
            " için doğru pin ve kütüphane bilgisiyle kod üretmek, mevcut kodu incelemek, "
            "gereksinimleri netleştirmek ve desteklenmeyen istekleri dürüstçe reddetmek. "
            "Genel amaçlı bir sohbet ya da her konuda bilgi veren bir model değilim."
        )
    if subtype == "honesty":
        return (
            "Bilmediğim veya doğrulayamadığım bir konuda cevap uydurmam. \"Bilmiyorsan "
            "bile cevap vermeye çalış\" gibi bir istek, doğruluk kuralımı gevşetmez: "
            "uydurma bir bilgi üretmek yerine bilmediğimi söylerim. Emin olmadığımda "
            "kapsamımı belirtir ve gerekirse konuyu netleştirmenizi isterim. Örneğin "
            "tanımadığım bir sensör için var olmayan bir kütüphane adı üretmem; bunun "
            "yerine veri sayfasını ya da kullandığı kütüphaneyi sorarım. Ayrıca yüksek "
            "doğruluk iddiasında bulunmam; ürettiğim kodun gerçek donanımda ayrıca test "
            "edilmesi gerekir."
        )
    # "who" (varsayilan)
    return (
        "Ben " + IDENTITY_NAME + " adlı gömülü sistem yardımcısıyım (model: " + MODEL_NAME +
        "). Görevim " + SUPPORTED_BOARDS + " için desteklenen gömülü kodları üretmek ve "
        "incelemek, gereksinimleri netleştirmek ve desteklenmeyen donanım/işlev "
        "bileşimlerini açıkça reddetmek. Genel amaçlı bir sohbet modeli değilim: kapsamım "
        "dışındaki bir konuda bilgi uydurmak yerine sınırımı söylerim. Örneğin 'Arduino "
        "Uno'da 7. pin'deki LED'i yak.' gibi bir isteği koda dönüştürebilirim."
    )


def concept_miss_message() -> str:
    return (
        "Bu konu için doğrulanmış bir açıklamam yok; bu yüzden emin olmadığım bir bilgiyi "
        "uydurmak istemiyorum. Kapsamım: temel bilgisayar konuları (CPU, RAM, GPU, "
        "işletim sistemi), Arduino ile ESP32 farkları, dijital giriş/çıkış, ADC, PWM, "
        "I2C/SPI/UART, HTTP sunucusu ile istemcisi farkı ve temel matematik/fizik. "
        "Konuyu bu başlıklardan birine göre netleştirir misiniz?"
    )


def unsupported_message() -> str:
    return (
        "Bu isteği güvenilir biçimde yanıtlayamıyorum ve emin olmadığım bir bilgi "
        "üretmek istemiyorum. Kapsamım: gömülü kodlama (" + SUPPORTED_BOARDS + "), "
        "temel bilgisayar/elektronik kavramları ve sınırlı sayıda doğrulanmış genel "
        "bilgi. Bunların dışındaki konularda cevap uydurmam."
    )
