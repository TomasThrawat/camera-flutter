#!/usr/bin/env bash
set -euo pipefail

flutter create --platforms=android --project-name black_camera .

# Flutter 3.47 creates an AGP 9 project but preserves the legacy Kotlin path by
# default for migration safety. photo_manager 3.10+ supports built-in Kotlin;
# enable it so the plugin does not fall back to the deprecated Kotlin Gradle Plugin.
python3 - <<'PY'
from pathlib import Path
import re

path = Path("android/gradle.properties")
text = path.read_text(encoding="utf-8")
pattern = re.compile(r"(?m)^android\\.builtInKotlin=.*$")
if pattern.search(text):
    text = pattern.sub("android.builtInKotlin=true", text)
else:
    text = text.rstrip() + "\\nandroid.builtInKotlin=true\\n"
path.write_text(text, encoding="utf-8")
if "android.builtInKotlin=true" not in path.read_text(encoding="utf-8"):
    raise SystemExit("Failed to enable built-in Kotlin")
PY

python3 tool/patch_android_manifest.py
base64 --decode assets/camera_app_icon.png.b64 > assets/camera_app_icon.png
