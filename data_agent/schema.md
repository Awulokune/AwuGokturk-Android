# AwuGoktürk Embedded Agent — Veri Seti Şeması (`data_agent/`)

Bu şema, **Embedded Agent** sistemini (bkz. `../DESIGN.md`) eğitmek/değerlendirmek
için ayrı bir veri seti tanımlar. **Mevcut `train.jsonl` / `validation.jsonl` /
`test.jsonl` veri seti DEĞİŞTİRİLMEZ ve bu şemaya dâhil edilmez.**

> Bu veri seti **eğitim için henüz KULLANILMAMIŞTIR**. Eğitim başlatmak onay
> gerektirir (bkz. `../REPORT.md` §5). `tools/generate_agent_dataset.py` yalnızca
> küçük bir *örnek/tohum* set üretir ve mevcut ajanın çıktısını "beklenen"
> referans olarak donmuş biçimde kaydeder.

## Kayıt alanları (JSONL, satır başına bir nesne)

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | str | Benzersiz kimlik (`agent_<kategori>_<n>`). |
| `split` | str | `train` / `validation` / `test`. Aynı `instruction_tr` yalnızca bir split'te bulunur (sızıntı yok). |
| `category` | str | Aşağıdaki kategorilerden biri. |
| `instruction_tr` | str | Türkçe doğal dil komutu. |
| `paraphrases` | list[str] | Aynı isteğin eşdeğer farklı ifadeleri (eğitim çeşitliliği için). |
| `board` | str\|null | Hedef kart anahtarı (`arduino_uno`, `arduino_mega2560`, `esp32`) veya `null` (belirtilmemiş). |
| `framework` | str\|null | `arduino` / `arduino-esp32` / `null`. |
| `structured_requirements` | object | Pinler, parametreler, kütüphaneler, modüller (Requirement Parser çıktısı). |
| `expected_status` | str | `ok` / `needs_info` / `unsupported` / `error` / `greeting` / `info`. |
| `expected_code` | str\|null | Beklenen kod (varsa). Mevcut ajanın donmuş çıktısı. |
| `expected_libraries` | list[str] | Beklenen kütüphaneler. |
| `valid_pins` | list | Bu kayıtta geçerli örnek pinler. |
| `invalid_pins` | list | Reddedilmesi gereken pinler (negatif/aralık dışı/kullanılamaz). |
| `guard_expectations` | list | AwuGuard'ın bulması beklenen bulgular (`{level, code, message}`). |
| `compile_expected` | str | `host_syntax_ok` / `host_syntax_fail` / `not_applicable`. |
| `notes` | str | Kısıtlar, varsayımlar, bilinen sınırlar. |

## Kategoriler

1. `code_generation_valid` — geçerli pin/parametre ile kod üretimi beklenir (`expected_status=ok`).
2. `invalid_pin` — negatif veya aralık dışı pin; **reddedilir, kod üretilmez** (`error`).
3. `missing_info` — kart veya zorunlu parametre eksik; **soru sorulur** (`needs_info`).
4. `unsupported_module` — tanınmayan sensör/modül; **kod uydurulmaz** (`unsupported`).
5. `unsupported_board` — ESP8266/RP2040/ESP32 varyantı; **dürüst ret** (`unsupported`).
6. `debug` — mevcut kodda hata/pin çakışması bulma (`info`/`error`).
7. `concept` — kavram sorusu (`info`).
8. `greeting` — selamlama (`greeting`).

## Ölçüm (eğitim yapılırsa)

Başarı **yalnızca eğitim kaybıyla** ölçülmez. Ayrı test kümesinde:
- **Pin doğruluğu:** istenen pinlerin koda aynen yansıması.
- **Derleme başarısı:** `host_syntax_ok` oranı (gerçek AVR/ESP32 derlemesi ayrı raporlanır).
- **Davranış doğruluğu:** beklenen modül/parametrelerin üretilmesi.
- **Doğru ret oranı:** `unsupported`/`error` beklenenlerin doğru reddedilmesi.
- **Soru sorma isabeti:** `needs_info` beklenenlerde net soru üretilmesi.

Bu metrikler **tek bir skorda birleştirilmez.**
