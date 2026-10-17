#!/usr/bin/env bash
# AwuGöktürk — debug APK derleme betiği.
#
# Bu betik, root gerektirmeyen (HOME içi) bir araç kurulumu varsayar:
#   - JDK 17            $JAVA_HOME
#   - Android SDK       $ANDROID_HOME (cmdline-tools + platform 34 + build-tools 34)
#   - Python 3.13       $AWU_BUILD_PYTHON (Chaquopy 'buildPython')
#   - Gradle 8.7        $GRADLE
#
# Ortam değişkenlerini kendi kurulumunuza göre ayarlayın.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

: "${ANDROID_HOME:=$HOME/Android/Sdk}"
: "${AWU_BUILD_PYTHON:=$HOME/tools/python313/bin/python3}"

# JAVA_HOME/GRADLE verilmediyse HOME içindeki kurulumu otomatik bul.
if [ -z "${JAVA_HOME:-}" ]; then
  JAVA_HOME="$(ls -d "$HOME"/tools/jdk-17* 2>/dev/null | head -1)"
fi
if [ -z "${GRADLE:-}" ]; then
  GRADLE="$(ls -d "$HOME"/tools/gradle-*/bin/gradle 2>/dev/null | head -1)"
fi
: "${JAVA_HOME:?JDK 17 bulunamadı; JAVA_HOME ayarlayın}"
: "${GRADLE:?Gradle bulunamadı; GRADLE ayarlayın}"

export JAVA_HOME ANDROID_HOME AWU_BUILD_PYTHON
export PATH="$JAVA_HOME/bin:$PATH"

echo "JAVA_HOME        = $JAVA_HOME"
echo "ANDROID_HOME     = $ANDROID_HOME"
echo "AWU_BUILD_PYTHON = $AWU_BUILD_PYTHON"
echo "GRADLE           = $GRADLE"

# 5K ağırlık JSON'unu yeniden üret (torch gerekir; yoksa mevcut asset kullanılır).
if python3 "$HERE/../tools/export_classifier5k.py" 2>/dev/null; then
  echo "5K ağırlıkları güncellendi."
else
  echo "UYARI: ağırlık JSON'u üretilemedi (torch yok?); mevcut asset kullanılacak."
fi

cd "$HERE"
"$GRADLE" --no-daemon :app:assembleDebug -PbuildPython="$AWU_BUILD_PYTHON"

APK="$HERE/app/build/outputs/apk/debug/AwuGokturk-debug.apk"
echo
echo "APK: $APK"
ls -la "$APK" 2>/dev/null || echo "APK bulunamadı — derleme çıktısını kontrol edin."
