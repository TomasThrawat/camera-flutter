#!/usr/bin/env bash
set -euo pipefail

flutter create --platforms=android --project-name black_camera .

# Align the generated Android project with the current stable AGP/Gradle pair.
# AGP 9.4.0 requires Gradle 9.6.0 and supports the current Android SDK metadata.
python3 - <<'PY'
from pathlib import Path
import re

settings = Path("android/settings.gradle.kts")
settings_text = settings.read_text(encoding="utf-8")

agp_pattern = re.compile(
    r'(id\("com\.android\.application"\)\s+version\s+")([0-9.]+)("\s+apply false)'
)
settings_text, agp_count = agp_pattern.subn(r"\g<1>9.4.0\3", settings_text)
if agp_count == 0 and 'id("com.android.application") version "9.4.0" apply false' not in settings_text:
    raise SystemExit("Could not find the Android Gradle Plugin version in settings.gradle.kts")

kotlin_pattern = re.compile(
    r'(id\("org\.jetbrains\.kotlin\.android"\)\s+version\s+")([0-9.]+)("\s+apply false)'
)
settings_text, kotlin_count = kotlin_pattern.subn(r"\g<1>2.4.10\3", settings_text)
if kotlin_count == 0 and 'id("org.jetbrains.kotlin.android") version "2.4.10" apply false' not in settings_text:
    raise SystemExit("Could not find the Kotlin plugin version in settings.gradle.kts")
settings.write_text(settings_text, encoding="utf-8")

wrapper = Path("android/gradle/wrapper/gradle-wrapper.properties")
wrapper_text = wrapper.read_text(encoding="utf-8")
wrapper_url = r"distributionUrl=https\://services.gradle.org/distributions/gradle-9.6.0-all.zip"
url_pattern = re.compile(r"(?m)^distributionUrl=.*gradle-[0-9.]+-(?:all|bin)\.zip$")
wrapper_text, wrapper_count = url_pattern.subn(wrapper_url, wrapper_text)
if wrapper_count == 0 and wrapper_url not in wrapper_text:
    raise SystemExit("Could not find the Gradle wrapper distribution URL")
wrapper.write_text(wrapper_text, encoding="utf-8")

properties = Path("android/gradle.properties")
lines = properties.read_text(encoding="utf-8").splitlines()
updated = []
found_built_in_kotlin = False
found_vfs_watch = False
for line in lines:
    if line.startswith("android.builtInKotlin="):
        if not found_built_in_kotlin:
            updated.append("android.builtInKotlin=true")
            found_built_in_kotlin = True
    elif line.startswith("org.gradle.vfs.watch="):
        if not found_vfs_watch:
            updated.append("org.gradle.vfs.watch=false")
            found_vfs_watch = True
    else:
        updated.append(line)

if not found_built_in_kotlin:
    updated.append("android.builtInKotlin=true")
if not found_vfs_watch:
    # Disable the Gradle filesystem watcher in one-shot CI builds. Flutter's
    # Android included build and project directory can otherwise register the
    # same watched path twice, printing "Already watching path" during release.
    updated.append("org.gradle.vfs.watch=false")

properties.write_text("\n".join(updated) + "\n", encoding="utf-8")

assert 'id("com.android.application") version "9.4.0" apply false' in settings_text
assert 'id("org.jetbrains.kotlin.android") version "2.4.10" apply false' in settings_text
assert wrapper_url in wrapper.read_text(encoding="utf-8")
final_properties = properties.read_text(encoding="utf-8").splitlines()
assert final_properties.count("android.builtInKotlin=true") == 1
assert final_properties.count("org.gradle.vfs.watch=false") == 1
print("Android toolchain pinned: AGP 9.4.0 / Gradle 9.6.0 / built-in Kotlin; Gradle VFS watching disabled for CI")
PY

python3 tool/patch_android_manifest.py
base64 --decode assets/camera_app_icon.png.b64 > assets/camera_app_icon.png

# Apply the final gallery navigation, swipe, and DCIM video-save fix.
python3 tool/fix_camera_back_swipe_and_media_save.py
