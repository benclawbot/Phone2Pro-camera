#!/usr/bin/env python3
"""Shared helpers for immutable firmware/package version-matrix records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class MatrixError(ValueError):
    """Raised when a version matrix cannot be loaded or queried."""


def load_matrix(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        matrix = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MatrixError(f"unable to read matrix {source}: {error}") from error
    if not isinstance(matrix, dict) or matrix.get("schemaVersion") != 1:
        raise MatrixError("unsupported or missing matrix schemaVersion")
    builds = matrix.get("builds")
    if not isinstance(builds, list):
        raise MatrixError("matrix builds must be an array")
    return matrix


def build_index(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    builds = matrix.get("builds")
    if not isinstance(builds, list):
        raise MatrixError("matrix builds must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, build in enumerate(builds):
        if not isinstance(build, dict):
            raise MatrixError(f"builds[{index}] must be an object")
        build_id = build.get("id")
        if not isinstance(build_id, str) or not build_id:
            raise MatrixError(f"builds[{index}] has no valid id")
        if build_id in result:
            raise MatrixError(f"duplicate build id: {build_id}")
        result[build_id] = build
    return result


def get_build(matrix: dict[str, Any], build_id: str) -> dict[str, Any]:
    try:
        return build_index(matrix)[build_id]
    except KeyError as error:
        raise MatrixError(f"unknown build id: {build_id}") from error


def identity_payload(build: dict[str, Any]) -> dict[str, Any]:
    platform = build.get("platform")
    packages = build.get("cameraPackages")
    if not isinstance(platform, dict) or not isinstance(packages, list):
        raise MatrixError("build identity requires platform and cameraPackages")
    fingerprint = platform.get("buildFingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise MatrixError("build identity requires platform.buildFingerprint")

    normalized_packages: list[dict[str, str]] = []
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            raise MatrixError(f"cameraPackages[{index}] must be an object")
        normalized: dict[str, str] = {}
        for field in ("packageName", "versionName", "sha256"):
            value = package.get(field)
            if not isinstance(value, str) or not value:
                raise MatrixError(f"cameraPackages[{index}].{field} is required for identity")
            normalized[field] = value
        normalized_packages.append(normalized)
    normalized_packages.sort(key=lambda item: (item["packageName"], item["versionName"], item["sha256"]))
    return {
        "buildFingerprint": fingerprint,
        "cameraPackages": normalized_packages,
    }


def identity_sha256(build: dict[str, Any]) -> str:
    encoded = json.dumps(
        identity_payload(build),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _compare_values(before: Any, after: Any, path: str, changes: list[dict[str, Any]]) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before) | set(after))
        for key in keys:
            child = f"{path}.{key}" if path else key
            if key not in before:
                changes.append({"path": child, "change": "added", "before": None, "after": after[key]})
            elif key not in after:
                changes.append({"path": child, "change": "removed", "before": before[key], "after": None})
            else:
                _compare_values(before[key], after[key], child, changes)
        return
    if before != after:
        changes.append({"path": path, "change": "modified", "before": before, "after": after})


def _keyed_array(items: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise MatrixError(f"{label} must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise MatrixError(f"{label}[{index}] must be an object")
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise MatrixError(f"{label}[{index}].{key} must be a non-empty string")
        if value in result:
            raise MatrixError(f"{label} has duplicate {key}: {value}")
        result[value] = item
    return result


def _diff_keyed_array(
    before_items: Any,
    after_items: Any,
    key: str,
    label: str,
    ignored_fields: set[str] | None = None,
) -> list[dict[str, Any]]:
    before = _keyed_array(before_items, key, f"before {label}")
    after = _keyed_array(after_items, key, f"after {label}")
    ignored = ignored_fields or set()
    changes: list[dict[str, Any]] = []
    for value in sorted(set(before) | set(after)):
        if value not in before:
            changes.append({"id": value, "change": "added", "before": None, "after": after[value]})
            continue
        if value not in after:
            changes.append({"id": value, "change": "removed", "before": before[value], "after": None})
            continue
        field_changes: list[dict[str, Any]] = []
        before_value = {field: content for field, content in before[value].items() if field not in ignored}
        after_value = {field: content for field, content in after[value].items() if field not in ignored}
        _compare_values(before_value, after_value, "", field_changes)
        if field_changes:
            changes.append({"id": value, "change": "modified", "fields": field_changes})
    return changes


def diff_builds(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    general_changes: list[dict[str, Any]] = []
    for section in ("status", "device", "platform", "firmware"):
        _compare_values(before.get(section), after.get(section), section, general_changes)

    package_changes = _diff_keyed_array(
        before.get("cameraPackages"),
        after.get("cameraPackages"),
        "packageName",
        "cameraPackages",
        ignored_fields={"evidence", "artifactHandling"},
    )
    diagnostic_changes = _diff_keyed_array(
        before.get("diagnosticBuilds"),
        after.get("diagnosticBuilds"),
        "id",
        "diagnosticBuilds",
        ignored_fields={"notes", "sourceArtifacts"},
    )
    return {
        "schemaVersion": 1,
        "from": {
            "id": before.get("id"),
            "identitySha256": before.get("identitySha256"),
        },
        "to": {
            "id": after.get("id"),
            "identitySha256": after.get("identitySha256"),
        },
        "summary": {
            "generalChanges": len(general_changes),
            "cameraPackageChanges": len(package_changes),
            "diagnosticBuildChanges": len(diagnostic_changes),
            "firmwareOrPlatformChanged": any(
                change["path"].startswith(("platform", "firmware"))
                for change in general_changes
            ),
            "cameraPackageChanged": bool(package_changes),
        },
        "generalChanges": general_changes,
        "cameraPackageChanges": package_changes,
        "diagnosticBuildChanges": diagnostic_changes,
    }
