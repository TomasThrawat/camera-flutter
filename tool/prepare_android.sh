#!/usr/bin/env bash
set -euo pipefail

flutter create --platforms=android --project-name black_camera .

# Flutter 3.47 creates an AGP 9 project but preserves legacy Kotlin by default.
# photo_manager 3.10+ supports built-in Kotlin, so enable it for this app.
python3 - <<'PY'
from pathlib import Path

path = Path("android/gradle.properties")
lines = path.read_text(encoding="utf-8").splitlines()
found = False
updated = []
for line in lines:
    if line.startswith("android.builtInKotlin="):
        updated.append("android.builtInKotlin=true")
        found = True
    else:
        updated.append(line)

if not found:
    updated.append("android.builtInKotlin=true")

path.write_text("\n".join(updated) + "\n", encoding="utf-8")
if path.read_text(encoding="utf-8").splitlines().count("android.builtInKotlin=true") != 1:
    raise SystemExit("Failed to enable built-in Kotlin exactly once")
PY

python3 tool/patch_android_manifest.py
base64 --decode assets/camera_app_icon.png.b64 > assets/camera_app_icon.png
