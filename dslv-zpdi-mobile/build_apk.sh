#!/bin/bash
# DSLV-ZPDI Mobile Node: Native Android APK Build Script
# This script wraps the refined React UI into a native Android APK using Capacitor.
# Run this script on a machine with Android Studio and Gradle installed.

set -e

echo "=========================================================="
echo " DSLV-ZPDI Native Android APK Compiler (Capacitor)"
echo "=========================================================="

echo "[1/4] Installing Capacitor CLI and core..."
npm install @capacitor/core
npm install -D @capacitor/cli @capacitor/android

echo "[2/4] Initializing Capacitor wrapper..."
npx cap init "DSLV-ZPDI C2" "com.dynogator.dslvzpdi" --web-dir dist

echo "[3/4] Building production web assets..."
npm run build

echo "[4/4] Adding Android platform and syncing..."
npx cap add android
npx cap sync android

echo "=========================================================="
echo " [SUCCESS] Android platform generated."
echo " To compile the final .apk file:"
echo " 1. Ensure you have the Android SDK & Gradle installed."
echo " 2. Run: cd android && ./gradlew assembleDebug"
echo " 3. Your APK will be located at:"
echo "    android/app/build/outputs/apk/debug/app-debug.apk"
echo "=========================================================="
