#!/usr/bin/env bash
# AwuGöktürk — EMÜLATÖR duman testi (başsız / headless).
#
# Ne yapar:
#   1) AVD oluşturur (yoksa)
#   2) Emülatörü başsız başlatır (KVM gerekir)
#   3) APK'yı kurar, MainActivity'yi açar
#   4) Uygulamanın çökmediğini ve Python/Chaquopy'nin başladığını doğrular
#   5) Sohbet ekranına "Merhaba" yazıp gönderir ve dönen yanıtı raporlar
#
# Kullanım:
#   ANDROID_HOME=$HOME/Android/Sdk ./emulator_test.sh app/build/outputs/apk/debug/AwuGokturk-debug.apk
#
# Not: x86_64 sistem imajı gerekir: "system-images;android-34;google_apis;x86_64".
set -uo pipefail

SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
AVD="${AWU_AVD:-awu_test}"
IMG="system-images;android-34;google_apis;x86_64"
APK="${1:-app/build/outputs/apk/debug/AwuGokturk-debug.apk}"
PKG=com.awulokune.awugokturk
ACT="$PKG/.MainActivity"

ADB="$SDK/platform-tools/adb"
EMU="$SDK/emulator/emulator"
AVDM="$SDK/cmdline-tools/latest/bin/avdmanager"

[ -x "$ADB" ] || { echo "adb bulunamadi: $ADB"; exit 1; }
[ -x "$EMU" ] || { echo "emulator bulunamadi: $EMU (sdkmanager 'emulator' kurun)"; exit 1; }
[ -f "$APK" ] || { echo "APK bulunamadi: $APK"; exit 1; }

echo "== AVD =="
if ! "$AVDM" list avd 2>/dev/null | grep -q "Name: $AVD"; then
  echo no | "$AVDM" create avd -n "$AVD" -k "$IMG" -d pixel_5 --force || {
    echo "AVD olusturulamadi (sistem imaji kurulu mu?): $IMG"; exit 1; }
fi

echo "== emulator baslatiliyor =="
"$EMU" -avd "$AVD" -no-window -no-audio -no-boot-anim \
       -gpu swiftshader_indirect -no-snapshot -memory 1536 \
       -netdelay none -netspeed full >/tmp/opencode/emulator.log 2>&1 &
EMU_PID=$!
trap 'kill $EMU_PID 2>/dev/null' EXIT

"$ADB" wait-for-device
echo "cihaz bagli; onyukleme bekleniyor..."
for i in $(seq 1 90); do
  BOOT="$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')"
  [ "$BOOT" = "1" ] && break
  sleep 2
done
[ "$BOOT" = "1" ] || { echo "onyukleme tamamlanmadi"; tail -20 /tmp/opencode/emulator.log; exit 1; }
echo "onyukleme tamam"

echo "== APK kuruluyor =="
"$ADB" install -r "$APK" 2>&1 | tail -2

echo "== uygulama aciliyor =="
"$ADB" logcat -c
"$ADB" shell am start -W -n "$ACT" 2>&1 | tail -5
sleep 12

echo "== surec ayakta mi? =="
"$ADB" shell pidof "$PKG" >/dev/null 2>&1 && echo "PID: $("$ADB" shell pidof "$PKG")" \
  || { echo "UYGULAMA CALISMIYOR"; "$ADB" logcat -d | tail -40; exit 1; }

echo "== Chaquopy/Python basladi mi? =="
"$ADB" logcat -d | grep -iE "chaquopy|python|AwuGokturk" | tail -10 || true

echo "== ekran icerigi (ilk) =="
"$ADB" shell uiautomator dump /sdcard/w.xml >/dev/null 2>&1
"$ADB" pull /sdcard/w.xml /tmp/opencode/w1.xml >/dev/null 2>&1
python3 - <<'PY' || true
import re
t = open("/tmp/opencode/w1.xml", encoding="utf-8", errors="ignore").read()
texts = re.findall(r'text="([^"]+)"', t)
descs = re.findall(r'content-desc="([^"]+)"', t)
print("  text    :", [x for x in texts if x.strip()][:12])
print("  desc    :", [x for x in descs if x.strip()][:12])
PY

echo "== sohbet: 'Merhaba' yaz ve gonder =="
# Metin alanina odaklan (yeni arayuzde alan otomatik odaklanmaz) ve yaz.
"$ADB" shell uiautomator dump /sdcard/w.xml >/dev/null 2>&1
"$ADB" pull /sdcard/w.xml /tmp/opencode/w2.xml >/dev/null 2>&1
EDIT_COORD=$(python3 "$(dirname "$0")/tools/find_node.py" edit edit 2>/dev/null)
if [ -n "${EDIT_COORD:-}" ]; then
  echo "  mesaj alani: $EDIT_COORD -> tikla"
  "$ADB" shell input tap $EDIT_COORD
  sleep 1
else
  echo "  mesaj alani bulunamadi (yine de yazmayi deniyorum)"
fi
# ASCII guvenli metin.
"$ADB" shell input text "Merhaba"
sleep 1
# Gonder butonunu content-desc ile bul ve tikla.
"$ADB" shell uiautomator dump /sdcard/w.xml >/dev/null 2>&1
"$ADB" pull /sdcard/w.xml /tmp/opencode/w2.xml >/dev/null 2>&1
COORD=$(python3 - <<'PY'
import re
t = open("/tmp/opencode/w2.xml", encoding="utf-8", errors="ignore").read()
m = re.search(r'content-desc="G[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
if not m:
    m = re.search(r'content-desc="[^"]*(Send|nder)[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', t)
if m:
    x1,y1,x2,y2 = map(int, m.groups()[-4:])
    print((x1+x2)//2, (y1+y2)//2)
PY
)
if [ -n "${COORD:-}" ]; then
  echo "  gonder butonu: $COORD -> tikla"
  "$ADB" shell input tap $COORD
else
  echo "  gonder butonu bulunamadi; Enter ile deniyorum"
  "$ADB" shell input keyevent 66
fi
sleep 10

echo "== yanit (ekranda) =="
"$ADB" shell uiautomator dump /sdcard/w.xml >/dev/null 2>&1
"$ADB" pull /sdcard/w.xml /tmp/opencode/w3.xml >/dev/null 2>&1
python3 - <<'PY' || true
import re
t = open("/tmp/opencode/w3.xml", encoding="utf-8", errors="ignore").read()
texts = [x for x in re.findall(r'text="([^"]+)"', t) if x.strip()]
for x in texts:
    print("  |", x[:160])
PY

echo "== son loglar (hata var mi?) =="
"$ADB" logcat -d | grep -iE "AndroidRuntime|FATAL|chaquopy.*error|Traceback" | tail -15 || echo "  (kritik hata yok)"
echo "== BITTI =="