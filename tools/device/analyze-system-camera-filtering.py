#!/usr/bin/env python3
"""Classify public, system-only, and unknown camera IDs from diagnostic JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

SYSTEM_ONLY_RE = re.compile(r"system only device\s+(\S+)", re.IGNORECASE)
UNKNOWN_DEVICE_RE = re.compile(r"unknown device\s+(\S+)", re.IGNORECASE)
CONNECT_REJECT_RE = re.compile(r"No camera device with ID .* available", re.IGNORECASE)


class AnalysisError(ValueError):
    pass


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Analyze system-camera filtering evidence")
    p.add_argument("input", help="camera_open JSON or a larger JSON containing it")
    p.add_argument("--json", dest="json_path", help="write JSON report")
    p.add_argument("--markdown", dest="markdown_path", help="write Markdown report")
    return p


def find_camera_open(value: Any, path: tuple[str, ...] = ()) -> tuple[dict[str, Any], tuple[str, ...]]:
    if isinstance(value, dict):
        if isinstance(value.get("publicCameraIds"), list) and isinstance(value.get("probes"), list):
            return value, path
        for key, child in value.items():
            try:
                return find_camera_open(child, path + (str(key),))
            except AnalysisError:
                pass
    elif isinstance(value, list):
        for index, child in enumerate(value):
            try:
                return find_camera_open(child, path + (str(index),))
            except AnalysisError:
                pass
    raise AnalysisError("no object containing publicCameraIds and probes was found")


def error_message(probe: dict[str, Any], key: str) -> str:
    error = probe.get(key)
    if isinstance(error, dict):
        for field in ("message", "string", "type"):
            value = error.get(field)
            if isinstance(value, str) and value:
                return value
    if isinstance(error, str):
        return error
    return ""


def classify_characteristics(probe: dict[str, Any]) -> tuple[str, str]:
    if probe.get("characteristicsReadable") is True:
        return "READABLE", "VERIFIED"
    message = error_message(probe, "characteristicsError")
    if SYSTEM_ONLY_RE.search(message):
        return "SYSTEM_ONLY_REJECTED", "VERIFIED"
    if UNKNOWN_DEVICE_RE.search(message):
        return "UNKNOWN_DEVICE", "VERIFIED"
    if message:
        return "ERROR_OTHER", "VERIFIED"
    return "UNKNOWN", "UNKNOWN"


def classify_open(probe: dict[str, Any], characteristics_state: str) -> tuple[str, str]:
    if probe.get("openOutcome") == "opened":
        return "OPENED", "VERIFIED"
    open_message = error_message(probe, "openError")
    characteristics_message = error_message(probe, "characteristicsError")
    if (
        open_message
        and characteristics_message
        and open_message == characteristics_message
        and "getCameraCharacteristics" in open_message
    ):
        return "BLOCKED_BY_CHARACTERISTICS_PREFLIGHT", "VERIFIED"
    if CONNECT_REJECT_RE.search(open_message):
        return "CONNECT_REJECTED", "VERIFIED"
    if open_message:
        if characteristics_state == "SYSTEM_ONLY_REJECTED":
            return "ERROR_AFTER_SYSTEM_ONLY_CLASSIFICATION", "PARTIALLY_VERIFIED"
        return "ERROR_OTHER", "VERIFIED"
    if probe.get("openCompleted") is False:
        return "INCOMPLETE", "VERIFIED"
    return "UNKNOWN", "UNKNOWN"


def classify_probe(probe: dict[str, Any], public_ids: set[str]) -> dict[str, Any]:
    camera_id = str(probe.get("cameraId", probe.get("id", "")))
    if not camera_id:
        raise AnalysisError("probe is missing cameraId")
    listed = probe.get("publiclyListed")
    if not isinstance(listed, bool):
        listed = camera_id in public_ids
    characteristics_state, characteristics_confidence = classify_characteristics(probe)
    open_state, open_confidence = classify_open(probe, characteristics_state)
    if listed and characteristics_state == "READABLE":
        kind = "PUBLIC"
        kind_confidence = "VERIFIED"
    elif characteristics_state == "SYSTEM_ONLY_REJECTED":
        kind = "SYSTEM_ONLY_CAMERA"
        kind_confidence = "VERIFIED"
    elif characteristics_state == "UNKNOWN_DEVICE":
        kind = "UNKNOWN_DEVICE"
        kind_confidence = "VERIFIED"
    else:
        kind = "UNKNOWN"
        kind_confidence = "UNKNOWN"
    return {
        "cameraId": camera_id,
        "deviceKind": kind,
        "deviceKindClassification": kind_confidence,
        "enumeration": {
            "state": "PUBLICLY_LISTED" if listed else "NOT_PUBLICLY_LISTED",
            "classification": "VERIFIED",
        },
        "characteristics": {
            "state": characteristics_state,
            "classification": characteristics_confidence,
            "error": error_message(probe, "characteristicsError") or None,
        },
        "open": {
            "state": open_state,
            "classification": open_confidence,
            "error": error_message(probe, "openError") or None,
            "connectIndependentlyReached": open_state in {"OPENED", "CONNECT_REJECTED", "ERROR_AFTER_SYSTEM_ONLY_CLASSIFICATION"},
        },
    }


def build_report(document: dict[str, Any]) -> dict[str, Any]:
    data, path = find_camera_open(document)
    public_ids = {str(item) for item in data["publicCameraIds"]}
    probes = [classify_probe(item, public_ids) for item in data["probes"] if isinstance(item, dict)]
    if not probes:
        raise AnalysisError("camera-open object contains no valid probes")
    system_ids = [item["cameraId"] for item in probes if item["deviceKind"] == "SYSTEM_ONLY_CAMERA"]
    unknown_ids = [item["cameraId"] for item in probes if item["deviceKind"] == "UNKNOWN_DEVICE"]
    preflight_ids = [
        item["cameraId"]
        for item in probes
        if item["open"]["state"] == "BLOCKED_BY_CHARACTERISTICS_PREFLIGHT"
    ]
    connect_reached = [
        item["cameraId"]
        for item in probes
        if item["open"]["connectIndependentlyReached"]
    ]
    return {
        "schemaVersion": 1,
        "sourceObjectPath": list(path),
        "publicCameraIds": sorted(public_ids),
        "probes": probes,
        "summary": {
            "systemOnlyCameraIds": system_ids,
            "unknownCameraIds": unknown_ids,
            "openBlockedByCharacteristicsPreflightIds": preflight_ids,
            "connectIndependentlyReachedIds": connect_reached,
        },
        "aospContract": {
            "providerClassification": {
                "type": "CameraProviderManager::SystemCameraKind",
                "values": ["PUBLIC", "SYSTEM_ONLY_CAMERA", "HIDDEN_SECURE_CAMERA"],
                "source": "frameworks/av/services/camera/libcameraservice/common/CameraProviderManager.h",
            },
            "enumeration": {
                "methods": [
                    "CameraProviderManager::collectDeviceIdsLocked",
                    "CameraService::shouldSkipStatusUpdates",
                ],
                "condition": "SYSTEM_ONLY_CAMERA is omitted for callers without system-camera access.",
            },
            "characteristics": {
                "method": "CameraService::shouldRejectSystemCameraConnection",
                "condition": "A non-cameraserver, non-HAL caller needs android.permission.SYSTEM_CAMERA for SYSTEM_ONLY_CAMERA.",
            },
            "connect": {
                "methods": [
                    "CameraService::connectHelper",
                    "CameraService::shouldRejectSystemCameraConnection",
                ],
                "condition": "Unauthorized SYSTEM_ONLY_CAMERA connection is rejected independently of enumeration.",
            },
        },
        "evidenceBoundary": {
            "verified": "Enumeration and characteristics outcomes are classified directly from the diagnostic fields and exact errors.",
            "partiallyVerified": "The AOSP path explains the matching target error but does not prove an unobserved OEM branch is byte-identical.",
            "unknown": "When open repeats the getCameraCharacteristics error, the diagnostic did not independently reach or observe CameraService connect enforcement.",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# System-camera filtering report",
        "",
        "| ID | Device kind | Enumeration | Characteristics | Open/connect |",
        "|---:|---|---|---|---|",
    ]
    for item in report["probes"]:
        lines.append(
            f"| `{item['cameraId']}` | {item['deviceKind']} | "
            f"{item['enumeration']['state']} | {item['characteristics']['state']} | "
            f"{item['open']['state']} |"
        )
    summary = report["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- System-only IDs: `{', '.join(summary['systemOnlyCameraIds']) or 'none'}`",
        f"- Unknown IDs: `{', '.join(summary['unknownCameraIds']) or 'none'}`",
        f"- Open probes blocked by characteristics preflight: `{', '.join(summary['openBlockedByCharacteristicsPreflightIds']) or 'none'}`",
        f"- IDs whose connect stage was independently reached: `{', '.join(summary['connectIndependentlyReachedIds']) or 'none'}`",
        "",
        "## Evidence boundary",
        "",
        f"- **VERIFIED:** {report['evidenceBoundary']['verified']}",
        f"- **PARTIALLY VERIFIED:** {report['evidenceBoundary']['partiallyVerified']}",
        f"- **UNKNOWN:** {report['evidenceBoundary']['unknown']}",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        document = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise AnalysisError("input root must be a JSON object")
        report = build_report(document)
    except (OSError, json.JSONDecodeError, AnalysisError) as error:
        print(f"system-camera analysis failed: {error}", file=sys.stderr)
        return 2
    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)
    if args.json_path:
        Path(args.json_path).write_text(json_text, encoding="utf-8")
    if args.markdown_path:
        Path(args.markdown_path).write_text(markdown_text, encoding="utf-8")
    if not args.json_path and not args.markdown_path:
        sys.stdout.write(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
