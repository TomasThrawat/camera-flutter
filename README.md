# Camera

A minimal Android-first Flutter camera app with only two main destinations:

- **Camera** — switch between Photo and Video, capture still images, record clips, toggle the torch, and switch front/back cameras.
- **Gallery** — view photos and videos saved in the device media library, open photos, and play videos.

Visual style: pure black surfaces with white controls. The app icon was made with Flutter Foundry: a pure black background and a centered white circular camera mark.

## Build it locally

Use Flutter stable (Dart 3.12 or later) and Android SDK tools.

1. Run \`bash tool/prepare_android.sh\` to generate the Android platform files, add camera/microphone/media permissions, and restore the generated icon PNG from the checked-in Base64 source.
2. Run \`flutter pub get\`.
3. Run \`dart run flutter_launcher_icons\`.
4. Run \`flutter analyze\` and \`flutter test\`.
5. Build an ARM64 release APK with \`flutter build apk --release --target-platform android-arm64\`.

## CircleCI

The \`.circleci/config.yml\` pipeline prepares the Android project, generates the native launcher icon, formats/analyzes the Dart source, runs tests, and produces an ARM64 APK. The artifact is published as \`camera-arm64-release.apk\`.

## Permissions

The app requests camera access for capture, microphone access for video recording, and media library access to save and display photos/videos. Captures are saved to the device Gallery through \`photo_manager\`.
