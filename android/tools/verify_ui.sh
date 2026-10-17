#!/usr/bin/env bash
# AwuGöktürk — EMÜLATÖR arayüz doğrulaması + ekran görüntüleri (başsız).
#
# Ne yapar:
#   1) Emülatörü başsız başlatır (KVM gerekir).
#   2) APK'yı kurar ve açar.
#   3) Yenilenen arayüzü gez: boş sohbet -> kod üretimi (sohbette) -> geçmiş
#      paneli -> Kod sekmesi -> Ayarlar -> başlatıcı ikonu.
#   4) Her adımda ekran görüntüsü kaydeder (screenshots/).
#   5) Çökme/istisna var mı diye logcat'i tarar.
#
# Kullanım (android/ dizininden):
#   ANDROID_HOME=$HOME/Android/Sdk ./tools/verify_ui.sh app/build/outputs/apk/debug/AwuGokturk-debug.apk
#
# Not: x86_64 sistem imajı gerekir: "system-images;android-34;google_apis;x86_64".
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.." || exit 1

SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
# avdmanager/sdkmanager Java ister; yerel JDK varsa otomatik kullan.
if [ -z "${JAVA_HOME:-}" ]; then
  for j in "$HOME"/tools/jdk-17*; do
    [ -x "$j/bin/java" ] && export JAVA_HOME="$j" && break
  done
fi
AVD="${AWU_AVD:-awu_test}"
IMG="system-images;android-34;google_apis;x86_64"
APK="${1:-app/build/outputs/apk/debug/AwuGokturk-debug.apk}"
PKG=com.awulokune.awugokturk
ACT="$PKG/.MainActivity"
OUT="screenshots"
TMP=/tmp/opencode

ADB="$SDK/platform-tools/adb"
EMU="$SDK/emulator/emulator"
AVDM="$SDK/cmdline-tools/latest/bin/avdmanager"

mkdir -p "$OUT" "$TMP"
[ -x "$ADB" ] || { echo "adb bulunamadi: $ADB"; exit 1; }
[ -x "$EMU" ] || { echo "emulator bulunamadi: $EMU"; exit 1; }
[ -f "$APK" ] || { echo "APK bulunamadi: $APK"; exit 1; }

shot() { "$ADB" exec-out screencap -p > "$OUT/$1.png" 2>/dev/null; echo "  [ekran] $OUT/$1.png"; }
dump() { "$ADB" shell uiautomator dump /sdcard/w.xml >/dev/null 2>&1; "$ADB" pull /sdcard/w.xml "$TMP/w.xml" >/dev/null 2>&1; }

tap() { # $1 mod, $2 hedef
  dump
  local c
  c=$(python3 "$HERE/find_node.py" "$1" "$2")
  if [ -n "$c" ]; then
    echo "  [tap:$1] '$2' -> $c"
    "$ADB" shell input tap $c
  else
    echo "  [tap:$1] BULUNAMADI: '$2'"
    python3 "$HERE/find_node.py" list "" | head -30
    return 1
  fi
}

echo "== AVD =="
if ! "$AVDM" list avd 2>/dev/null | grep -q "Name: $AVD"; then
  echo no | "$AVDM" create avd -n "$AVD" -k "$IMG" -d pixel_5 --force || {
    echo "AVD olusturulamadi: $IMG"; exit 1; }
fi

echo "== emulator baslatiliyor =="
"$EMU" -avd "$AVD" -no-window -no-audio -no-boot-anim \
       -gpu swiftshader_indirect -no-snapshot -memory 2048 \
       -netdelay none -netspeed full >"$TMP/emulator.log" 2>&1 &
EMU_PID=$!
trap 'kill $EMU_PID 2>/dev/null' EXIT

"$ADB" wait-for-device
BOOT=""
for _ in $(seq 1 120); do
  BOOT="$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')"
  [ "$BOOT" = "1" ] && break
  sleep 2
done
[ "$BOOT" = "1" ] || { echo "onyukleme tamamlanmadi"; tail -20 "$TMP/emulator.log"; exit 1; }
echo "onyukleme tamam"

# Animasyonlari kapat: tiklamalar ve ekran goruntuleri tutarli olsun.
for s in window_animation_scale transition_animation_scale animator_duration_scale; do
  "$ADB" shell settings put global "$s" 0 >/dev/null 2>&1
done

echo "== APK kuruluyor =="
"$ADB" install -r "$APK" 2>&1 | tail -2

echo "== uygulama verisi temizleniyor (temiz bos ekran icin) =="
"$ADB" shell pm clear "$PKG" >/dev/null 2>&1

echo "== uygulama aciliyor =="
"$ADB" logcat -c
"$ADB" shell am start -W -n "$ACT" 2>&1 | grep -E "Status|TotalTime|Error" || true
sleep 14

echo "== 1) BOS SOHBET (yeni tasarim) =="
shot 01_sohbet_bos

echo "== 2) ORNEK ISTEM (sohbette kod uretimi) =="
tap contains "LED yak" && sleep 16
shot 02_sohbet_kod

echo "== 3) YENI SOHBET + GECMIS PANELI =="
tap exact "Yeni sohbet" && sleep 2
tap exact "Sohbet gecmisi" || tap exact "Sohbet geçmişi"
sleep 3
shot 03_gecmis
"$ADB" shell input keyevent 4 >/dev/null 2>&1
sleep 2

echo "== 4) KOD SEKMESI =="
tap exact "Kod" && sleep 2
shot 04_kod_bos
tap edit "edit" && sleep 1
"$ADB" shell input text "Arduino%sUno%spin%s7%sLED%s5%ssaniye%sblink" && sleep 1
"$ADB" shell input keyevent 111 >/dev/null 2>&1   # ESC: klavyeyi kapat
sleep 1
tap exact "Kod Üret" && sleep 16
shot 05_kod_sonuc

echo "== 5) AYARLAR =="
tap exact "Ayarlar" && sleep 3
shot 06_ayarlar

echo "== 6) BASLATICI IKONU =="
"$ADB" shell input keyevent 3 >/dev/null 2>&1   # HOME
sleep 5
shot 07_ana_ekran
"$ADB" shell input swipe 540 2000 540 600 250 >/dev/null 2>&1  # uygulama cekmecesi
sleep 5
shot 08_uygulama_cekmecesi

echo "== 7) MODEL GUNCELLEMELERI EKRANI =="
"$ADB" shell am start -W -n "$ACT" >/dev/null 2>&1
sleep 8
tap exact "Ayarlar" && sleep 3
# Ayarlar kaydırılabilir; "Model Güncellemeleri" bölümü ekranın altındadır.
"$ADB" shell input swipe 540 1800 540 700 300 >/dev/null 2>&1
sleep 1
"$ADB" shell input swipe 540 1800 540 700 300 >/dev/null 2>&1
sleep 2
tap exact "Güncellemeleri aç" && sleep 3
shot 10_model_guncelleme

echo "== 8) GERCEK GITHUB KONTROLU =="
tap contains "kontrol et" && sleep 15
shot 11_model_kontrol

echo "== 9) CEVRIMDISI KONTROL =="
"$ADB" shell cmd connectivity airplane-mode enable >/dev/null 2>&1 \
  || "$ADB" shell settings put global airplane_mode_on 1 >/dev/null 2>&1
"$ADB" shell svc wifi disable >/dev/null 2>&1
"$ADB" shell svc data disable >/dev/null 2>&1
sleep 6
"$ADB" shell dumpsys connectivity 2>/dev/null | grep -m1 "Active default network" || true
tap contains "kontrol et" && sleep 14
shot 12_cevrimdisi_kontrol
"$ADB" shell cmd connectivity airplane-mode disable >/dev/null 2>&1
sleep 3

echo "== 9b) MODEL DURUM DOSYASI (cihaz) =="
"$ADB" shell run-as "$PKG" ls -la files/ 2>/dev/null | tail -8
"$ADB" shell run-as "$PKG" ls -la files/awu_models 2>/dev/null | tail -8
"$ADB" shell run-as "$PKG" cat files/awu_models/model_state.json 2>/dev/null | head -30

echo "== 10) LOG KONTROLU =="
if "$ADB" logcat -d | grep -E "FATAL EXCEPTION|Traceback \(most recent|E AndroidRuntime" | tail -20; then
  echo "  ^ dikkat: yukaridaki satirlar"
else
  echo "  kritik hata yok"
fi

echo "== surec =="
"$ADB" shell pidof "$PKG" >/dev/null 2>&1 && echo "  PID: $("$ADB" shell pidof "$PKG")" || echo "  UYGULAMA CALISMIYOR"

echo "== BITTI =="
