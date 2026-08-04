#!/usr/bin/env python3
"""Validate the versioned Galaga firmware camera interface reference."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

REFERENCE_PATH = pathlib.Path("research/firmware/galaga-camera-interface-reference.v1.json")
CONFIDENCE = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}
CATEGORIES = {"FRAMEWORK", "APPLICATION", "PROVIDER_HAL", "VENDOR_METADATA", "NATIVE_LIBRARY", "CONFIGURATION", "KERNEL", "PERMISSION", "SELINUX", "ISP_TUNING"}
FIELDS = {"id", "category", "layer", "owner", "process", "interfaceType", "methodOrSymbol", "direction", "identityRequirements", "status", "confidence", "buildScope", "description", "evidence", "opaqueBoundary", "replacementUse", "versionDifferences"}
FORBIDDEN_UNKNOWN_USES = {"PUBLIC_BACKEND_REFERENCE", "FAIL_CLOSED_VENDOR_ADAPTER", "DIRECT_CALL", "PRODUCTION_WRITE"}


class ValidationError(ValueError):
    pass


def text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{where} must be a non-empty string")
    return value


def load_reference(root: pathlib.Path) -> dict[str, Any]:
    value = json.loads((root / REFERENCE_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError("reference root must be an object")
    files = value.get("interfaceFiles")
    if not isinstance(files, list) or not files:
        raise ValidationError("interfaceFiles must be a non-empty array")
    merged: list[dict[str, Any]] = []
    for index, relative in enumerate(files):
        relative = text(relative, f"interfaceFiles[{index}]")
        part = json.loads((root / relative).read_text(encoding="utf-8"))
        if not isinstance(part, dict):
            raise ValidationError(f"{relative} must contain an object")
        if part.get("schemaVersion") != value.get("schemaVersion") or part.get("referenceVersion") != value.get("referenceVersion"):
            raise ValidationError(f"{relative} version mismatch")
        interfaces = part.get("interfaces")
        if not isinstance(interfaces, list) or not interfaces:
            raise ValidationError(f"{relative} must contain interfaces")
        merged.extend(interfaces)
    value["interfaces"] = merged
    return value


def validate_build(scope: Any) -> None:
    if not isinstance(scope, dict):
        raise ValidationError("targetBuild must be an object")
    for field in ("matrixEntryId", "device", "model", "androidRelease", "buildNumber", "fingerprint", "status"):
        text(scope.get(field), f"targetBuild.{field}")
    package = scope.get("cameraPackage")
    if not isinstance(package, dict):
        raise ValidationError("targetBuild.cameraPackage must be an object")
    for field in ("packageName", "versionName", "sha256"):
        text(package.get(field), f"targetBuild.cameraPackage.{field}")
    digest = package["sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValidationError("targetBuild.cameraPackage.sha256 must be lowercase SHA-256")


def validate_reference(reference: dict[str, Any], root: pathlib.Path, *, check_paths: bool = True) -> None:
    if reference.get("schemaVersion") != 1 or reference.get("issue") != 98:
        raise ValidationError("schemaVersion must be 1 and issue must be 98")
    text(reference.get("referenceVersion"), "referenceVersion")
    if reference.get("confidenceVocabulary") != ["VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"]:
        raise ValidationError("confidenceVocabulary must preserve project ordering")
    validate_build(reference.get("targetBuild"))
    target_id = reference["targetBuild"]["matrixEntryId"]

    source = reference.get("sourceReleaseScope")
    if not isinstance(source, dict) or source.get("relationship") != "BUILD_MISMATCH":
        raise ValidationError("sourceReleaseScope must retain the build mismatch")
    for field in ("officialRelease", "observedBuild", "notes"):
        text(source.get(field), f"sourceReleaseScope.{field}")

    files = reference.get("interfaceFiles")
    if not isinstance(files, list) or not files or len(files) != len(set(files)):
        raise ValidationError("interfaceFiles must be unique and non-empty")
    for index, relative in enumerate(files):
        relative = text(relative, f"interfaceFiles[{index}]")
        if check_paths and not (root / relative).is_file():
            raise ValidationError(f"interfaceFiles[{index}] does not exist: {relative}")

    if set(reference.get("categories", [])) != CATEGORIES:
        raise ValidationError("categories must exactly cover every required layer")

    registry = reference.get("evidenceRegistry")
    if not isinstance(registry, dict) or not registry:
        raise ValidationError("evidenceRegistry must be non-empty")
    for evidence_id, item in registry.items():
        text(evidence_id, "evidence id")
        if not isinstance(item, dict):
            raise ValidationError(f"evidenceRegistry.{evidence_id} must be an object")
        path = text(item.get("path"), f"evidenceRegistry.{evidence_id}.path")
        if item.get("classification") not in CONFIDENCE:
            raise ValidationError(f"evidenceRegistry.{evidence_id}.classification is invalid")
        text(item.get("supports"), f"evidenceRegistry.{evidence_id}.supports")
        if check_paths and not (root / path).is_file():
            raise ValidationError(f"evidenceRegistry.{evidence_id}.path does not exist: {path}")

    interfaces = reference.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        raise ValidationError("interfaces must be non-empty")
    ids: set[str] = set()
    covered: set[str] = set()
    opaque = 0
    for index, item in enumerate(interfaces):
        where = f"interfaces[{index}]"
        if not isinstance(item, dict):
            raise ValidationError(f"{where} must be an object")
        missing = FIELDS - set(item)
        if missing:
            raise ValidationError(f"{where} missing fields: {sorted(missing)}")
        interface_id = text(item["id"], f"{where}.id")
        if interface_id in ids:
            raise ValidationError(f"duplicate interface id: {interface_id}")
        ids.add(interface_id)
        category = text(item["category"], f"{where}.category")
        if category not in CATEGORIES:
            raise ValidationError(f"{where}.category is unsupported")
        covered.add(category)
        for field in ("layer", "owner", "process", "interfaceType", "methodOrSymbol", "direction", "status", "description", "replacementUse", "versionDifferences"):
            text(item[field], f"{where}.{field}")
        identity = item["identityRequirements"]
        if not isinstance(identity, list) or not identity:
            raise ValidationError(f"{where}.identityRequirements must be non-empty")
        for n, requirement in enumerate(identity):
            text(requirement, f"{where}.identityRequirements[{n}]")
        confidence = item["confidence"]
        if confidence not in CONFIDENCE:
            raise ValidationError(f"{where}.confidence is invalid")
        if text(item["buildScope"], f"{where}.buildScope") != target_id:
            raise ValidationError(f"{where} uses a different target build")
        evidence = item["evidence"]
        if not isinstance(evidence, list) or not evidence or len(evidence) != len(set(evidence)):
            raise ValidationError(f"{where}.evidence must contain unique IDs")
        for evidence_id in evidence:
            if evidence_id not in registry:
                raise ValidationError(f"{where} references unknown evidence: {evidence_id}")
        if not isinstance(item["opaqueBoundary"], bool):
            raise ValidationError(f"{where}.opaqueBoundary must be boolean")
        opaque += int(item["opaqueBoundary"])
        if confidence == "UNKNOWN" and not item["opaqueBoundary"]:
            raise ValidationError(f"{where} UNKNOWN interfaces must be opaque")
        if confidence == "UNKNOWN" and item["replacementUse"] in FORBIDDEN_UNKNOWN_USES:
            raise ValidationError(f"{where} enables an UNKNOWN interface")

    if covered != CATEGORIES:
        raise ValidationError(f"interfaces do not cover categories: {sorted(CATEGORIES - covered)}")
    if opaque < 5:
        raise ValidationError("reference must retain the major opaque boundaries")

    differences = reference.get("firmwareDifferences")
    if not isinstance(differences, list) or len(differences) < 2:
        raise ValidationError("firmwareDifferences must retain target and source records")
    if not any(isinstance(item, dict) and item.get("relationshipToTarget") == "PREDATES_TARGET" for item in differences):
        raise ValidationError("source release must remain marked as predating the target")

    boundaries = reference.get("opaqueBoundaries")
    if not isinstance(boundaries, list) or len(boundaries) < 5:
        raise ValidationError("opaqueBoundaries must list unresolved proprietary areas")

    maintenance = reference.get("maintenance")
    if not isinstance(maintenance, dict):
        raise ValidationError("maintenance must be an object")
    for field in ("validator", "document"):
        path = text(maintenance.get(field), f"maintenance.{field}")
        if check_paths and not (root / path).is_file():
            raise ValidationError(f"maintenance.{field} path does not exist: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    reference = load_reference(root)
    validate_reference(reference, root)
    print(f"validated {len(reference['interfaces'])} firmware camera interfaces for {reference['targetBuild']['matrixEntryId']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
