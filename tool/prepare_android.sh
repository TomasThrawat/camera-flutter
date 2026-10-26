#!/usr/bin/env bash
set -euo pipefail

flutter create --platforms=android --project-name black_camera .
python3 tool/patch_android_manifest.py
base64 --decode assets/camera_app_icon.png.b64 > assets/camera_app_icon.png
