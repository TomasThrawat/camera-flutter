# CircleCI build trigger

CircleCI is connected to this repository through the GitHub App. API-triggered pipelines are not supported for this project type, so pushes to `main` are the supported trigger route.

The project config at `.circleci/config.yml` formats and analyzes Dart, runs Flutter tests, and builds `android-arm64` release APK output as `camera-arm64-release.apk`.
