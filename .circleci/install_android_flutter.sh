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
flutter --version

echo "== Resolve latest Linux Android command-line tools =="
ANDROID_HOME="$HOME/android-sdk"
ANDROID_SDK_ROOT="$ANDROID_HOME"
export ANDROID_HOME ANDROID_SDK_ROOT

REPOSITORY_XML="$(mktemp)"
curl --fail --silent --show-error --location --retry 3 \
  "https://dl.google.com/android/repository/repository2-1.xml" \
  --output "$REPOSITORY_XML"

CMDLINE_URL="$(python3 - "$REPOSITORY_XML" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
for package in root.iter():
    if package.tag.rsplit("}", 1)[-1] != "remotePackage":
        continue
    if package.attrib.get("path") != "cmdline-tools;latest":
        continue
    for archive in package.iter():
        if archive.tag.rsplit("}", 1)[-1] != "archive":
            continue
        host_os = next(
            (node.text for node in archive.iter()
             if node.tag.rsplit("}", 1)[-1] == "host-os"),
            None,
        )
        if host_os != "linux":
            continue
        for node in archive.iter():
            if node.tag.rsplit("}", 1)[-1] != "complete":
                continue
            url = next(
                (child.text for child in node
                 if child.tag.rsplit("}", 1)[-1] == "url"),
                None,
            )
            if url:
                print(url)
                raise SystemExit(0)
raise SystemExit("Could not find the latest Linux Android command-line tools URL")
PY
)"
echo "Android command-line tools archive: $CMDLINE_URL"
curl --fail --location --retry 3 \
  "https://dl.google.com/android/repository/$CMDLINE_URL" \
  --output /tmp/android-command-line-tools.zip
mkdir -p "$ANDROID_HOME/cmdline-tools/latest" /tmp/android-command-line-tools
unzip -q /tmp/android-command-line-tools.zip -d /tmp/android-command-line-tools
cp -a /tmp/android-command-line-tools/cmdline-tools/. "$ANDROID_HOME/cmdline-tools/latest/"

export PATH="$HOME/flutter/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
{
  echo "$HOME/flutter/bin"
  echo "$ANDROID_HOME/cmdline-tools/latest/bin"
  echo "$ANDROID_HOME/platform-tools"
} >> "$GITHUB_PATH"
{
  echo "ANDROID_HOME=$ANDROID_HOME"
  echo "ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
} >> "$GITHUB_ENV"

echo "== Accept SDK licenses and install SDK packages =="
yes | sdkmanager --sdk_root="$ANDROID_HOME" --licenses >/dev/null || true
sdkmanager --sdk_root="$ANDROID_HOME" \
  "platform-tools" \
  "platforms;android-35" \
  "platforms;android-36" \
  "build-tools;35.0.0" \
  "build-tools;36.0.0"

flutter config --android-sdk "$ANDROID_HOME"
yes | flutter doctor --android-licenses || true
flutter doctor -v
