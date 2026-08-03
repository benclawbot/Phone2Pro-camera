#!/usr/bin/env python3
"""Extract requested permissions from an Android APK binary manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from android_binary_xml import BinaryXmlError, parse_manifest, read_manifest_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read AndroidManifest.xml directly from an APK or extracted binary XML "
            "and emit a clean-room permission summary."
        )
    )
    parser.add_argument("input", help="APK or extracted binary AndroidManifest.xml")
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Write the JSON report to this path instead of stdout",
    )
    parser.add_argument(
        "--expect-permission",
        action="append",
        default=[],
        metavar="NAME",
        help="Exit with status 1 when NAME is not requested; may be repeated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.input)
    try:
        manifest, source_kind = read_manifest_input(source)
        summary = parse_manifest(manifest)
    except (OSError, BinaryXmlError) as error:
        print(f"manifest extraction failed: {error}", file=sys.stderr)
        return 2

    requested = list(summary.uses_permissions)
    missing = [name for name in args.expect_permission if name not in requested]
    report = {
        "input": str(source),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_kind": source_kind,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "package_name": summary.package_name,
        "uses_permissions": requested,
        "requested_system_camera": "android.permission.SYSTEM_CAMERA" in requested,
        "missing_expected_permissions": missing,
        "evidence_boundary": {
            "verified": "The named permissions are requested by the binary manifest.",
            "unknown": (
                "A manifest request does not prove install-time grant, package-signature "
                "eligibility, UID assignment, AppOps state, SELinux access, or successful "
                "CameraService authorization."
            ),
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_path:
        output = Path(args.json_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
