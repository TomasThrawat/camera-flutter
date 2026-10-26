#!/usr/bin/env python3
"""Make photo_manager use its documented built-in Kotlin path in this Android CI build.

The app explicitly enables AGP's built-in Kotlin. photo_manager 3.12.x already
supports that mode, but its compatibility fallback contains a literal
'kotlin-android' application that Flutter's static migration check flags even
when the built-in path is selected. This CI-only patch removes that unused
legacy fallback and its KGP classpath from the resolved pub cache, not from
the checked-in repository.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path.cwd()
GRADLE_PROPERTIES = ROOT / "android" / "gradle.properties"
PACKAGE_CONFIG = ROOT / ".dart_tool" / "package_config.json"

BUILD_SCRIPT_BLOCK = """// Keep this top-level: a conditional buildscript block can run after Gradle
// has resolved the script classpath.
buildscript {
    ext.kotlin_version = '1.9.23'
    repositories {
        google()
        mavenCentral()
    }

    dependencies {
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
    }
}
"""
LEGACY_PLUGIN_BLOCK = """if (!useBuiltInKotlin) {
    apply plugin: 'kotlin-android'
}
"""


def package_path_from_uri(uri: str) -> Path:
    parsed = urlsplit(uri)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path)).resolve()
    if parsed.scheme:
        raise SystemExit(f"Unsupported photo_manager rootUri scheme: {parsed.scheme}")
    return (PACKAGE_CONFIG.parent / unquote(uri)).resolve()


def main() -> None:
    if not GRADLE_PROPERTIES.is_file():
        raise SystemExit("android/gradle.properties was not generated")
    flags = [
        line.strip()
        for line in GRADLE_PROPERTIES.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("android.builtInKotlin=")
    ]
    if flags != ["android.builtInKotlin=true"]:
        raise SystemExit(
            "Refusing to patch photo_manager unless android.builtInKotlin=true "
            "appears exactly once"
        )

    config = json.loads(PACKAGE_CONFIG.read_text(encoding="utf-8"))
    entry = next(
        (item for item in config.get("packages", []) if item.get("name") == "photo_manager"),
        None,
    )
    if entry is None:
        raise SystemExit("photo_manager was not found in .dart_tool/package_config.json")

    package_root = package_path_from_uri(entry["rootUri"])
    pubspec = package_root / "pubspec.yaml"
    gradle_file = package_root / "android" / "build.gradle"
    if not pubspec.is_file() or not gradle_file.is_file():
        raise SystemExit(f"photo_manager Android Gradle file missing at {package_root}")

    version_match = re.search(
        r"(?m)^version:\s*['\"]?([0-9]+\.[0-9]+\.[0-9]+)",
        pubspec.read_text(encoding="utf-8"),
    )
    if not version_match:
        raise SystemExit("Could not determine resolved photo_manager version")
    version = tuple(int(part) for part in version_match.group(1).split("."))
    if version < (3, 10, 0) or version >= (4, 0, 0):
        raise SystemExit(
            f"photo_manager {version_match.group(1)} is outside the verified "
            "built-in Kotlin migration range; review this patch before building"
        )

    source = gradle_file.read_text(encoding="utf-8")
    changed = False
    if BUILD_SCRIPT_BLOCK in source:
        source = source.replace(BUILD_SCRIPT_BLOCK, "", 1)
        changed = True
    elif "kotlin-gradle-plugin" in source:
        raise SystemExit(
            "photo_manager Gradle classpath block changed; refusing to patch an "
            "unrecognized structure"
        )

    if LEGACY_PLUGIN_BLOCK in source:
        source = source.replace(LEGACY_PLUGIN_BLOCK, "", 1)
        changed = True
    elif "apply plugin: 'kotlin-android'" in source:
        raise SystemExit(
            "photo_manager Kotlin fallback block changed; refusing to patch an "
            "unrecognized structure"
        )

    if "kotlin-gradle-plugin" in source or "apply plugin: 'kotlin-android'" in source:
        raise SystemExit("Legacy Kotlin Gradle Plugin references remain after patch")
    if "if (useBuiltInKotlin)" not in source or "compilerOptions" not in source:
        raise SystemExit("Built-in Kotlin compiler configuration was not preserved")

    if changed:
        gradle_file.write_text(source, encoding="utf-8")
    print(
        f"photo_manager {version_match.group(1)}: built-in Kotlin path verified; "
        "legacy KGP fallback removed from CI pub cache"
    )


if __name__ == "__main__":
    main()
