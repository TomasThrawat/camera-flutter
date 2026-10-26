#!/usr/bin/env python3
from pathlib import Path
import re

manifest = Path("android/app/src/main/AndroidManifest.xml")
if not manifest.exists():
    raise SystemExit("AndroidManifest.xml not found. Run flutter create first.")

text = manifest.read_text()
permissions = [
    '    <uses-permission android:name="android.permission.CAMERA" />',
    '    <uses-permission android:name="android.permission.RECORD_AUDIO" />',
    '    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />',
    '    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />',
    '    <uses-permission android:name="android.permission.READ_MEDIA_VISUAL_USER_SELECTED" />',
    '    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />',
    '    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28" />',
]
for permission in permissions:
    match = re.search(r'android:name="([^"]+)"', permission)
    if match and match.group(1) not in text:
        text = text.replace("    <application", permission + "\n    <application", 1)

text = re.sub(r'android:label="[^"]+"', 'android:label="Camera"', text, count=1)
manifest.write_text(text)

for gradle in (Path("android/app/build.gradle.kts"), Path("android/app/build.gradle")):
    if gradle.exists():
        contents = gradle.read_text()
        contents = contents.replace("minSdk = flutter.minSdkVersion", "minSdk = 24")
        contents = contents.replace("minSdkVersion flutter.minSdkVersion", "minSdkVersion 24")
        gradle.write_text(contents)
