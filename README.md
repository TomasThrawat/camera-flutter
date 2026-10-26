# Camera

A minimal Android-first Flutter camera app with two primary destinations: Camera (photo/video capture) and Gallery (local photos/videos).

Design: pure black surfaces, white controls, and a Flutter Foundry-generated icon with a pure black background and centered white circular camera mark.

## Current CircleCI setup

The existing CircleCI pipeline definition is currently reported by the CircleCI API as the gha workflow. Its config source path is .circleci/config.yml, so that file contains a GitHub Actions-compatible workflow that CircleCI can execute through its GitHub App pipeline integration.

The standard CircleCI-native configuration is preserved separately at .circleci/native-config.yml.

The pipeline prepares Android platform files, restores the generated icon from Base64, resolves packages, formats and analyzes Dart, runs Flutter tests, builds an ARM64 release APK, and uploads camera-arm64-release.apk as the camera-arm64-release artifact.

## Build locally

Use Flutter stable (Dart 3.12 or later) and Android SDK tools.

1. Run bash tool/prepare_android.sh.
2. Run flutter pub get.
3. Run dart run flutter_launcher_icons.
4. Run dart format lib test, then flutter analyze and flutter test.
5. Run flutter build apk --release --target-platform android-arm64.

## Permissions

The app requests camera access for photo/video capture, microphone access for video, and media-library access to save and show photos and videos.
