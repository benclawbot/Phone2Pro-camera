#!/usr/bin/env python3
"""Validate the versioned Galaga firmware camera interface reference."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

REFERENCE_PATH = pathlib.Path(
    "research/firmware/galaga-camera-interface-reference.v1.json"
)
CONFIDENCE = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}
REQUIRED_CATEGORIES = {
    "FRAMEWORK",
    "APPLICATION",
    "PROVIDER_HAL",
    "VENDOR_METADATA",
    "NATIVE_LIBRARY",
    "CONFIGURATION",
    "KERNEL",
    "PERMISSION",
    "SELINUX",
    "ISP_TUNING",
}
REQUIRED_INTERFACE_FIELDS = {
    "id",
    "category",
    "layer",
    "owner",
    "process",
    "interfaceType",
    "methodOrSymbol",
    "direction",
    "identityRequirements",
    "status",
    "confidence",
    "buildScope",
    "description",
    "evidence",
    "opaqueBoundary",
    "replacementUse",
    "versionDifferences",
}
FORBIDDEN_UNKNOWN_USES = {
    "PUBLIC_BACKEND_REFERENCE",
    "FAIL_CLOSED_VENDOR_ADAPTER",
    "DIRECT_CALL",
    "PRODUCTION_WRITE",
}


class ValidationError(ValueError):
    """Raised when the firmware interface reference violates an invariant."""


def load_reference(root: pathlib.Path) -> dict[str, Any]:
    path = root / REFERENCE_PATH
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError("reference root must be an object")
    return value


def require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{location} must be a non-empty string")
    return value


def validate_build_scope(scope: Any, location: str) -> None:
    if not isinstance(scope, dict):
        raise ValidationError(f"{location} must be an object")
    required = {
        "matrixEntryId",
        "device",
        "model",
        "androidRelease",
        "buildNumber",
        "fingerprint",
        "cameraPackage",
        "status",
    }
    missing = required - set(scope)
    if missing:
        raise ValidationError(f"{location} missing fields: {sorted(missing)}")
    for field in required - {"cameraPackage"}:
        require_string(scope[field], f"{location}.{field}")
    package = scope["cameraPackage"]
    if not isinstance(package, dict):
        raise ValidationError(f"{location}.cameraPackage must be an object")
    for field in ("packageName", "versionName", "sha256"):
        require_string(package.get(field), f"{location}.cameraPackage.{field}")
    digest = package["sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValidationError(f"{location}.cameraPackage.sha256 must be lowercase SHA-256")


def validate_evidence_registry(
    registry: Any, root: pathlib.Path, check_paths: bool
) -> dict[str, dict[str, Any]]:
    if not isinstance(registry, dict) or not registry:
        raise ValidationError("evidenceRegistry must be a non-empty object")
    normalized: dict[str, dict[str, Any]] = {}
    for evidence_id, item in registry.items():
        require_string(evidence_id, "evidenceRegistry id")
        location = f"evidenceRegistry.{evidence_id}"
        if not isinstance(item, dict):
            raise ValidationError(f"{location} must be an object")
        path = require_string(item.get("path"), f"{location}.path")
        classification = require_string(
            item.get("classification"), f"{location}.classification"
        )
        if classification not in CONFIDENCE:
            raise ValidationError(
                f"{location}.classification must use confidence vocabulary"
            )
        require_string(item.get("supports"), f"{location}.supports")
        if check_paths and not (root / path).is_file():
            raise ValidationError(f"{location}.path does not exist: {path}")
        normalized[evidence_id] = item
    return normalized


def validate_evidence_ids(
    evidence: Any, registry: dict[str, dict[str, Any]], location: str
) -> None:
    if not isinstance(evidence, list) or not evidence:
        raise ValidationError(f"{location} must contain evidence IDs")
    if len(evidence) != len(set(evidence)):
        raise ValidationError(f"{location} contains duplicate evidence IDs")
    for index, evidence_id in enumerate(evidence):
        require_string(evidence_id, f"{location}[{index}]")
        if evidence_id not in registry:
            raise ValidationError(
                f"{location}[{index}] references unknown evidence: {evidence_id}"
            )


def validate_reference(
    reference: dict[str, Any],
    root: pathlib.Path,
    *,
    check_paths: bool = True,
) -> None:
    if reference.get("schemaVersion") != 1:
        raise ValidationError("schemaVersion must be 1")
    require_string(reference.get("referenceVersion"), "referenceVersion")
    if reference.get("issue") != 98:
        raise ValidationError("issue must be 98")
    if reference.get("confidenceVocabulary") != [
        "VERIFIED",
        "PARTIALLY_VERIFIED",
        "HYPOTHESIS",
        "UNKNOWN",
    ]:
        raise ValidationError("confidenceVocabulary must preserve project ordering")

    target = reference.get("targetBuild")
    validate_build_scope(target, "targetBuild")

    source_scope = reference.get("sourceReleaseScope")
    if not isinstance(source_scope, dict):
        raise ValidationError("sourceReleaseScope must be an object")
    if source_scope.get("relationship") != "BUILD_MISMATCH":
        raise ValidationError("sourceReleaseScope must retain the build mismatch")
    require_string(source_scope.get("officialRelease"), "sourceReleaseScope.officialRelease")
    require_string(source_scope.get("observedBuild"), "sourceReleaseScope.observedBuild")
    require_string(source_scope.get("notes"), "sourceReleaseScope.notes")

    declared_categories = reference.get("categories")
    if not isinstance(declared_categories, list):
        raise ValidationError("categories must be an array")
    if set(declared_categories) != REQUIRED_CATEGORIES:
        raise ValidationError("categories must exactly cover every required layer")

    evidence_registry = validate_evidence_registry(
        reference.get("evidenceRegistry"), root, check_paths
    )

    interfaces = reference.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        raise ValidationError("interfaces must be a non-empty array")

    ids: set[str] = set()
    covered_categories: set[str] = set()
    opaque_count = 0
    for index, interface in enumerate(interfaces):
        location = f"interfaces[{index}]"
        if not isinstance(interface, dict):
            raise ValidationError(f"{location} must be an object")
        missing = REQUIRED_INTERFACE_FIELDS - set(interface)
        if missing:
            raise ValidationError(f"{location} missing fields: {sorted(missing)}")

        interface_id = require_string(interface["id"], f"{location}.id")
        if interface_id in ids:
            raise ValidationError(f"duplicate interface id: {interface_id}")
        ids.add(interface_id)

        category = require_string(interface["category"], f"{location}.category")
        if category not in REQUIRED_CATEGORIES:
            raise ValidationError(f"{location}.category is unsupported: {category}")
        covered_categories.add(category)

        for field in (
            "layer",
            "owner",
            "process",
            "interfaceType",
            "methodOrSymbol",
            "direction",
            "status",
            "description",
            "replacementUse",
            "versionDifferences",
        ):
            require_string(interface[field], f"{location}.{field}")

        identity = interface["identityRequirements"]
        if not isinstance(identity, list) or not identity:
            raise ValidationError(f"{location}.identityRequirements must be non-empty")
        for identity_index, requirement in enumerate(identity):
            require_string(
                requirement,
                f"{location}.identityRequirements[{identity_index}]",
            )

        confidence = require_string(interface["confidence"], f"{location}.confidence")
        if confidence not in CONFIDENCE:
            raise ValidationError(f"{location}.confidence is unsupported")

        build_scope = require_string(interface["buildScope"], f"{location}.buildScope")
        if build_scope != target["matrixEntryId"]:
            raise ValidationError(f"{location} uses a different target build")

        validate_evidence_ids(
            interface["evidence"],
            evidence_registry,
            f"{location}.evidence",
        )

        opaque = interface["opaqueBoundary"]
        if not isinstance(opaque, bool):
            raise ValidationError(f"{location}.opaqueBoundary must be boolean")
        if opaque:
            opaque_count += 1
        if confidence == "UNKNOWN" and not opaque:
            raise ValidationError(f"{location} UNKNOWN interfaces must be opaque")
        if confidence == "UNKNOWN" and interface["replacementUse"] in FORBIDDEN_UNKNOWN_USES:
            raise ValidationError(f"{location} enables an UNKNOWN interface")

    if covered_categories != REQUIRED_CATEGORIES:
        missing = REQUIRED_CATEGORIES - covered_categories
        raise ValidationError(f"interfaces do not cover categories: {sorted(missing)}")
    if opaque_count < 5:
        raise ValidationError("reference must retain the major opaque boundaries")

    differences = reference.get("firmwareDifferences")
    if not isinstance(differences, list) or len(differences) < 2:
        raise ValidationError("firmwareDifferences must retain target and source records")
    difference_ids = {
        require_string(item.get("id"), "firmwareDifferences[].id")
        for item in differences
        if isinstance(item, dict)
    }
    if {"observed-target", "official-source-release"} - difference_ids:
        raise ValidationError("firmwareDifferences must include target and source release")
    if not any(
        isinstance(item, dict)
        and item.get("relationshipToTarget") == "PREDATES_TARGET"
        for item in differences
    ):
        raise ValidationError("source release must remain marked as predating the target")

    opaque_boundaries = reference.get("opaqueBoundaries")
    if not isinstance(opaque_boundaries, list) or len(opaque_boundaries) < 5:
        raise ValidationError("opaqueBoundaries must list unresolved proprietary areas")
    for index, boundary in enumerate(opaque_boundaries):
        require_string(boundary, f"opaqueBoundaries[{index}]")

    maintenance = reference.get("maintenance")
    if not isinstance(maintenance, dict):
        raise ValidationError("maintenance must be an object")
    for field in ("validator", "document"):
        path = require_string(maintenance.get(field), f"maintenance.{field}")
        if check_paths and not (root / path).is_file():
            raise ValidationError(f"maintenance.{field} path does not exist: {path}")
    triggers = maintenance.get("updateTriggers")
    if not isinstance(triggers, list) or not triggers:
        raise ValidationError("maintenance.updateTriggers must be non-empty")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument(
        "--no-path-check",
        action="store_true",
        help="Validate structure without checking repository evidence paths.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    reference = load_reference(root)
    validate_reference(reference, root, check_paths=not args.no_path_check)
    print(
        f"validated {len(reference['interfaces'])} firmware camera interfaces "
        f"for {reference['targetBuild']['matrixEntryId']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
