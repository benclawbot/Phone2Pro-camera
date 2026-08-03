#!/usr/bin/env python3
"""Compare two immutable entries in the firmware/package version matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from version_matrix import MatrixError, diff_builds, get_build, load_matrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diff platform, firmware, camera-package and diagnostic-build state."
    )
    parser.add_argument(
        "--matrix",
        default=str(
            Path(__file__).resolve().parents[2]
            / "data"
            / "builds"
            / "version-matrix.json"
        ),
        help="version matrix JSON",
    )
    parser.add_argument("--from", dest="from_id", required=True, help="source build ID")
    parser.add_argument("--to", dest="to_id", required=True, help="target build ID")
    parser.add_argument("--json", dest="json_path", help="write the JSON report to this path")
    parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="exit 1 when any material change is found",
    )
    return parser


def render_text(report: dict[str, object]) -> str:
    source = report["from"]
    target = report["to"]
    summary = report["summary"]
    assert isinstance(source, dict)
    assert isinstance(target, dict)
    assert isinstance(summary, dict)
    lines = [
        f"Version matrix diff: {source.get('id')} -> {target.get('id')}",
        "",
        f"General changes: {summary.get('generalChanges')}",
        f"Camera package changes: {summary.get('cameraPackageChanges')}",
        f"Diagnostic build changes: {summary.get('diagnosticBuildChanges')}",
        f"Firmware/platform changed: {summary.get('firmwareOrPlatformChanged')}",
        f"Camera package changed: {summary.get('cameraPackageChanged')}",
    ]
    for section_name, title in (
        ("generalChanges", "General"),
        ("cameraPackageChanges", "Camera packages"),
        ("diagnosticBuildChanges", "Diagnostic builds"),
    ):
        changes = report.get(section_name)
        if not isinstance(changes, list) or not changes:
            continue
        lines.extend(["", f"{title}:"])
        for change in changes:
            if not isinstance(change, dict):
                continue
            identifier = change.get("path", change.get("id", "unknown"))
            lines.append(f"- {change.get('change')}: {identifier}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        matrix = load_matrix(args.matrix)
        before = get_build(matrix, args.from_id)
        after = get_build(matrix, args.to_id)
        report = diff_builds(before, after)
    except MatrixError as error:
        print(f"version matrix diff failed: {error}", file=sys.stderr)
        return 2

    rendered_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_path:
        output = Path(args.json_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered_json, encoding="utf-8")
    sys.stdout.write(render_text(report))

    summary = report["summary"]
    changed = isinstance(summary, dict) and any(
        bool(summary.get(key))
        for key in ("generalChanges", "cameraPackageChanges", "diagnosticBuildChanges")
    )
    return 1 if args.fail_on_change and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
