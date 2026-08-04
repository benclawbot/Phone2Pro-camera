#!/usr/bin/env python3
"""Generate the Galaga MediaTek/Nothing vendor API reference."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import subprocess
import sys
from typing import Any

MANIFEST_PATH = pathlib.Path("data/vendor-tags/api-reference.v1.json")
DATABASE_BUILDER = pathlib.Path("tools/build-vendor-tag-database.py")
WRITE_DIRECTIONS = {"request", "session", "physical-request"}
CONFIDENCE = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def generated_database(root: pathlib.Path) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(root / DATABASE_BUILDER), "--root", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(process.stdout)
    if not isinstance(value, dict):
        raise ValueError("typed vendor-tag builder did not return an object")
    return value


def confidence_for_type(status: Any) -> str:
    text = str(status or "UNKNOWN").upper()
    if text in {"VERIFIED", "TARGET_VERIFIED", "TARGET_RUNTIME_VERIFIED"}:
        return "VERIFIED"
    if "UNVERIFIED" in text or "PUBLIC_SOURCE" in text or "PARTIAL" in text:
        return "PARTIALLY_VERIFIED"
    if "HYPOTHESIS" in text or "INFERRED" in text:
        return "HYPOTHESIS"
    return "UNKNOWN"


def ordering_for(directions: list[str], profiles: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for direction in sorted(set(directions)):
        profile = profiles.get(direction)
        if isinstance(profile, dict):
            result.append({"direction": direction, **copy.deepcopy(profile)})
        else:
            result.append(
                {
                    "direction": direction,
                    "phase": "UNKNOWN",
                    "rule": "No target-verified ordering rule is available.",
                    "confidence": "UNKNOWN",
                }
            )
    return result


def value_reference(record: dict[str, Any]) -> dict[str, Any]:
    routing = record.get("routingPriority")
    observed: dict[str, Any] = {}
    if isinstance(routing, dict):
        if routing.get("characteristicValue") is not None:
            observed["characteristicValue"] = copy.deepcopy(routing["characteristicValue"])
        if routing.get("observedValue") is not None:
            observed["observedValue"] = copy.deepcopy(routing["observedValue"])
    advertised = copy.deepcopy(record.get("advertisedValues", {}))
    return {
        "advertisedByCameraId": advertised,
        "observedRoutingValues": observed,
        "enumOrBitfieldStatus": "UNKNOWN" if not observed else "PARTIALLY_VERIFIED",
        "writeValueStatus": "UNSUPPORTED_UNTIL_TARGET_VERIFIED",
        "confidence": "VERIFIED" if advertised else ("PARTIALLY_VERIFIED" if observed else "UNKNOWN"),
    }


def dependency_reference(record: dict[str, Any]) -> list[dict[str, Any]]:
    context = record.get("buildContext", {})
    advertised = record.get("advertisedValues", {})
    return [
        {
            "kind": "EXACT_BUILD",
            "value": context.get("fingerprint"),
            "confidence": "VERIFIED",
        },
        {
            "kind": "CAMERA_IDS",
            "value": copy.deepcopy(record.get("cameraIds", [])),
            "confidence": "PARTIALLY_VERIFIED",
        },
        {
            "kind": "ADVERTISEMENT",
            "value": bool(advertised),
            "confidence": "VERIFIED" if advertised else "UNKNOWN",
        },
        {
            "kind": "STOCK_CALL_SITE",
            "value": record.get("callSiteStatus", "UNRESOLVED"),
            "confidence": "VERIFIED" if record.get("stockCallSites") else "UNKNOWN",
        },
    ]


def effect_reference(record: dict[str, Any]) -> dict[str, Any]:
    routing = record.get("routingPriority")
    if isinstance(routing, dict) and routing.get("objective"):
        return {
            "status": "CANDIDATE_EFFECT_NOT_CAUSALLY_VERIFIED",
            "description": routing["objective"],
            "confidence": "HYPOTHESIS",
            "measurementRequired": True,
        }
    return {
        "status": "UNKNOWN",
        "description": "No target-verified causal image-pipeline, routing or metadata effect is recorded.",
        "confidence": "UNKNOWN",
        "measurementRequired": True,
    }


def safety_reference(record: dict[str, Any], manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    directions = set(record.get("directions", []))
    write_capable = bool(directions & WRITE_DIRECTIONS)
    production_status = record.get("productionStatus", "DISABLED")
    enabled = production_status == "ENABLED" and record["name"] in set(
        manifest["productionPolicy"]["currentProductionWriteKeys"]
    )

    if enabled:
        safety = {
            "classification": "PRODUCTION_ENABLED",
            "writeAllowed": True,
            "reason": "The key passed the exact-build production policy.",
            "fallback": manifest["productionPolicy"]["fallback"],
        }
        sample = {
            "status": "AVAILABLE",
            "kind": "WRITE_CONFIGURATION",
            "guidance": "Apply only at the direction-specific phase and retain the public Camera2 fallback.",
        }
    elif write_capable:
        safety = {
            "classification": "UNSAFE_OR_UNSUPPORTED_WRITE",
            "writeAllowed": False,
            "reason": record.get("writePolicy", "NO_WRITE_WITHOUT_TARGET_TYPE_AND_STOCK_VALUE"),
            "fallback": manifest["productionPolicy"]["fallback"],
        }
        sample = {
            "status": "NOT_AVAILABLE",
            "kind": "WRITE_CONFIGURATION",
            "reason": "Target-verified type, value, causal effect, rollback and exact-build probe evidence are incomplete.",
        }
    else:
        safety = {
            "classification": "READ_ONLY_REFERENCE",
            "writeAllowed": False,
            "reason": "The committed evidence supports read-only discovery or result inspection only.",
            "fallback": manifest["productionPolicy"]["fallback"],
        }
        sample = {
            "status": "AVAILABLE",
            "kind": "READ_ONLY_INTROSPECTION",
            "guidance": "Resolve the key from the matching CameraCharacteristics or CaptureResult collection and preserve the raw typed value.",
        }
    return safety, sample


def materialize_record(record: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    directions = sorted(set(record.get("directions", [])))
    safety, sample = safety_reference(record, manifest)
    context = copy.deepcopy(record.get("buildContext", {}))
    type_confidence = confidence_for_type(record.get("typeStatus"))
    return {
        "name": record["name"],
        "family": record.get("family"),
        "directions": directions,
        "type": {
            "javaType": record.get("javaType"),
            "nativeType": record.get("nativeType"),
            "vendorId": record.get("vendorId"),
            "tagId": record.get("tagId"),
            "status": record.get("typeStatus", "UNKNOWN"),
            "byteLayoutStatus": record.get("byteLayoutStatus", "UNKNOWN_LAYOUT"),
            "byteLayoutDescription": record.get("byteLayoutDescription"),
            "confidence": type_confidence,
        },
        "values": value_reference(record),
        "ordering": ordering_for(directions, manifest["orderingProfiles"]),
        "dependencies": dependency_reference(record),
        "effect": effect_reference(record),
        "errors": {
            "observed": [],
            "possible": copy.deepcopy(manifest["failureTaxonomy"]),
            "confidence": "UNKNOWN",
        },
        "buildScope": context,
        "safety": safety,
        "sampleConfiguration": sample,
        "stockCallSites": copy.deepcopy(record.get("stockCallSites", [])),
        "evidence": {
            "sourceRefs": sorted(set(record.get("sourceRefs", []))),
            "externalSourceRefs": sorted(set(record.get("externalSourceRefs", []))),
            "sourceInventoryStatus": record.get("sourceInventoryStatus"),
        },
    }


def build_reference(root: pathlib.Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_json(root / MANIFEST_PATH)
    database = generated_database(root)
    records = [
        materialize_record(record, manifest)
        for record in database.get("records", [])
        if isinstance(record, dict) and isinstance(record.get("name"), str)
    ]

    safety_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {value: 0 for value in sorted(CONFIDENCE)}
    for record in records:
        safety = record["safety"]["classification"]
        safety_counts[safety] = safety_counts.get(safety, 0) + 1
        confidence_counts[record["type"]["confidence"]] += 1

    return {
        "schemaVersion": manifest["schemaVersion"],
        "referenceVersion": manifest["referenceVersion"],
        "issue": manifest["issue"],
        "status": manifest["status"],
        "buildScope": copy.deepcopy(database.get("buildContext", {})),
        "sourceDatabaseVersion": database.get("databaseVersion"),
        "summary": {
            "recordCount": len(records),
            "directionCounts": copy.deepcopy(database.get("summary", {}).get("directionCounts", {})),
            "safetyCounts": safety_counts,
            "typeConfidenceCounts": confidence_counts,
            "productionWriteKeyCount": sum(
                1 for record in records if record["safety"]["classification"] == "PRODUCTION_ENABLED"
            ),
        },
        "productionPolicy": copy.deepcopy(manifest["productionPolicy"]),
        "interpretationRules": copy.deepcopy(manifest["interpretationRules"]),
        "records": records,
        "sourceFiles": {
            "manifest": str(MANIFEST_PATH),
            "databaseManifest": manifest["sourceDatabaseManifest"],
            "databaseBuilder": manifest["sourceDatabaseBuilder"],
            "builder": manifest["builder"],
            "validator": manifest["validator"],
            "document": manifest["document"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    payload = json.dumps(build_reference(args.root), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
