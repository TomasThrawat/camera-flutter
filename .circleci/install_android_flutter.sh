#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(pwd)"
LOG_FILE="$ROOT/camera-ci.log"
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "== Install base tools =="
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3 unzip xz-utils zip libglu1-mesa

echo "== Resolve latest stable Flutter archive =="
RELEASE_JSON="$(mktemp)"
curl --fail --silent --show-error --location --retry 3 \
  "https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json" \
  --output "$RELEASE_JSON"

FLUTTER_ARCHIVE="$(python3 - "$RELEASE_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    data = json.load(stream)
stable_hash = data["current_release"]["stable"]
release = next(
    item for item in data["releases"]
    if item.get("hash") == stable_hash and item.get("channel") == "stable"
)
print(release["archive"])
PY
)"
echo "Flutter archive: $FLUTTER_ARCHIVE"
curl --fail --location --retry 3 \
  "https://storage.googleapis.com/flutter_infra_release/releases/$FLUTTER_ARCHIVE" \
  --output /tmp/flutter-stable.tar.xz
tar -xf /tmp/flutter-stable.tar.xz -C "$HOME"
export PATH="$HOME/flutter/bin:$PATH"
echo "$HOME/flutter/bin" >> "$GITHUB_PATH"
flutter --version

echo "== Install the current Android CLI in a writable user directory =="
ANDROID_HOME="$HOME/android-sdk"
ANDROID_SDK_ROOT="$ANDROID_HOME"
ANDROID_CLI_BIN="$HOME/android-cli/bin"
mkdir -p "$ANDROID_HOME" "$ANDROID_CLI_BIN"
curl --fail --silent --show-error --location --retry 3 \
  "https://dl.google.com/android/cli/latest/linux_x86_64/android" \
  --output "$ANDROID_CLI_BIN/android"
chmod 755 "$ANDROID_CLI_BIN/android"
export ANDROID_HOME ANDROID_SDK_ROOT
export PATH="$ANDROID_CLI_BIN:$HOME/flutter/bin:$PATH"
{
  echo "$ANDROID_CLI_BIN"
  echo "$HOME/flutter/bin"
} >> "$GITHUB_PATH"
{
  echo "ANDROID_HOME=$ANDROID_HOME"
  echo "ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
} >> "$GITHUB_ENV"

echo "== Install Android SDK packages with the supported Android CLI =="
set +o pipefail
yes | android --no-metrics --sdk="$ANDROID_HOME" sdk install \
  cmdline-tools/latest \
  platform-tools \
  platforms/android-35 \
  platforms/android-36 \
  build-tools/35.0.0 \
  build-tools/36.0.0
set -o pipefail

flutter config --android-sdk "$ANDROID_HOME"
flutter doctor -v
