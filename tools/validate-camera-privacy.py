#!/usr/bin/env python3
"""Validate production camera privacy and no-network invariants."""

from __future__ import annotations

import argparse
import pathlib
import sys
import xml.etree.ElementTree as ET

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
FORBIDDEN_PERMISSIONS = {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.CHANGE_NETWORK_STATE",
}
FORBIDDEN_SOURCE_MARKERS = (
    "import java.net.",
    "import javax.net.",
    "import okhttp3.",
    "import retrofit2.",
    "import io.ktor.",
    "import com.android.volley.",
    "import io.grpc.",
)
FORBIDDEN_DEPENDENCY_MARKERS = (
    "okhttp",
    "retrofit",
    "ktor-client",
    "volley",
    "grpc-okhttp",
)


def validate(root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    app_root = root / "camera-app" / "app"
    manifest = app_root / "src" / "main" / "AndroidManifest.xml"
    if not manifest.is_file():
        return [f"missing production manifest: {manifest}"]

    tree = ET.parse(manifest)
    manifest_root = tree.getroot()
    permissions = {
        element.attrib.get(ANDROID_NS + "name", "")
        for element in manifest_root.findall("uses-permission")
    }
    for permission in sorted(FORBIDDEN_PERMISSIONS & permissions):
        errors.append(f"forbidden production permission: {permission}")

    application = manifest_root.find("application")
    if application is None:
        errors.append("production manifest has no application element")
    else:
        if application.attrib.get(ANDROID_NS + "allowBackup") != "false":
            errors.append("production application must set android:allowBackup=\"false\"")
        if application.attrib.get(ANDROID_NS + "usesCleartextTraffic") != "false":
            errors.append(
                "production application must set android:usesCleartextTraffic=\"false\""
            )

    java_root = app_root / "src" / "main" / "java"
    for source in sorted(java_root.rglob("*.java")) if java_root.is_dir() else []:
        text = source.read_text(encoding="utf-8")
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker in text:
                errors.append(f"network API marker {marker!r} in {source.relative_to(root)}")

    for build_file_name in ("build.gradle", "build.gradle.kts"):
        build_file = app_root / build_file_name
        if not build_file.is_file():
            continue
        lowered = build_file.read_text(encoding="utf-8").lower()
        for marker in FORBIDDEN_DEPENDENCY_MARKERS:
            if marker in lowered:
                errors.append(
                    f"network dependency marker {marker!r} in {build_file.relative_to(root)}"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Camera privacy validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
