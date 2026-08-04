#!/usr/bin/env python3
"""Validate the generated Galaga MediaTek/Nothing vendor API reference."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/vendor-tags/api-reference.v1.json"
BUILDER = ROOT / "tools/build-vendor-api-reference.py"
CONFIDENCE = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}
WRITE_DIRECTIONS = {"request", "session", "physical-request"}
REQUIRED_FIELDS = {
    "name",
    "family",
    "directions",
    "type",
    "values",
    "ordering",
    "dependencies",
    "effect",
    "errors",
    "buildScope",
    "safety",
    "sampleConfiguration",
    "stockCallSites",
    "evidence",
}


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain an object")
    return value


def build() -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(BUILDER), "--root", str(ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(process.stdout)
    if not isinstance(value, dict):
        raise AssertionError("builder output must be an object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_record(record: dict[str, Any], manifest: dict[str, Any]) -> None:
    name = record.get("name", "<unknown>")
    require(REQUIRED_FIELDS <= set(record), f"{name}: missing required fields")
    require(isinstance(record["directions"], list) and record["directions"], f"{name}: empty directions")

    type_info = record["type"]
    require(isinstance(type_info, dict), f"{name}: type must be an object")
    require(type_info.get("confidence") in CONFIDENCE, f"{name}: invalid type confidence")
    require("byteLayoutStatus" in type_info, f"{name}: missing byte-layout status")

    values = record["values"]
    require(isinstance(values, dict), f"{name}: values must be an object")
    require(values.get("confidence") in CONFIDENCE, f"{name}: invalid value confidence")
    require(values.get("writeValueStatus"), f"{name}: missing write-value status")

    ordering = record["ordering"]
    require(isinstance(ordering, list), f"{name}: ordering must be a list")
    ordered_directions = {item.get("direction") for item in ordering if isinstance(item, dict)}
    require(set(record["directions"]) <= ordered_directions, f"{name}: missing direction ordering")
    for item in ordering:
        require(item.get("confidence") in CONFIDENCE, f"{name}: invalid ordering confidence")

    dependencies = record["dependencies"]
    require(isinstance(dependencies, list) and dependencies, f"{name}: dependencies missing")
    require(any(item.get("kind") == "EXACT_BUILD" for item in dependencies), f"{name}: exact-build dependency missing")

    effect = record["effect"]
    require(effect.get("confidence") in CONFIDENCE, f"{name}: invalid effect confidence")
    require("measurementRequired" in effect, f"{name}: effect measurement flag missing")

    errors = record["errors"]
    require(isinstance(errors.get("possible"), list) and errors["possible"], f"{name}: failure taxonomy missing")
    for failure in errors["possible"]:
        require(failure.get("confidence") in CONFIDENCE, f"{name}: invalid failure confidence")

    scope = record["buildScope"]
    for field in ("device", "model", "firmwareBuild", "fingerprint"):
        require(scope.get(field), f"{name}: build scope missing {field}")

    safety = record["safety"]
    classification = safety.get("classification")
    require(
        classification in {"PRODUCTION_ENABLED", "UNSAFE_OR_UNSUPPORTED_WRITE", "READ_ONLY_REFERENCE"},
        f"{name}: invalid safety classification",
    )
    write_capable = bool(set(record["directions"]) & WRITE_DIRECTIONS)
    sample = record["sampleConfiguration"]

    if write_capable and classification != "PRODUCTION_ENABLED":
        require(not safety.get("writeAllowed"), f"{name}: unsupported write marked allowed")
        require(sample.get("status") == "NOT_AVAILABLE", f"{name}: unsupported write exposes a sample")
        require(safety.get("fallback") == manifest["productionPolicy"]["fallback"], f"{name}: fallback mismatch")

    if classification == "PRODUCTION_ENABLED":
        require(name in manifest["productionPolicy"]["currentProductionWriteKeys"], f"{name}: not allowlisted")
        require(safety.get("writeAllowed") is True, f"{name}: enabled write not allowed")
        require(sample.get("status") == "AVAILABLE", f"{name}: enabled write lacks sample")
        require(type_info.get("confidence") == "VERIFIED", f"{name}: enabled write type not verified")
        require(values.get("confidence") == "VERIFIED", f"{name}: enabled write value not verified")
        require(effect.get("confidence") == "VERIFIED", f"{name}: enabled write effect not verified")

    evidence = record["evidence"]
    require(isinstance(evidence.get("sourceRefs"), list), f"{name}: source refs missing")


def main() -> int:
    manifest = load_json(MANIFEST)
    reference = build()
    second = build()
    require(reference == second, "reference generation is not deterministic")
    require(reference.get("issue") == 97, "wrong issue linkage")
    require(reference.get("referenceVersion") == manifest.get("referenceVersion"), "reference version mismatch")
    records = reference.get("records")
    require(isinstance(records, list) and records, "reference contains no records")
    names = [record.get("name") for record in records]
    require(len(names) == len(set(names)), "duplicate vendor-key records")
    require(reference["summary"]["recordCount"] == len(records), "record count mismatch")
    require(
        reference["summary"]["productionWriteKeyCount"]
        == len(manifest["productionPolicy"]["currentProductionWriteKeys"]),
        "production write count mismatch",
    )

    for source in (
        manifest["sourceDatabaseManifest"],
        manifest["sourceDatabaseBuilder"],
        manifest["builder"],
        manifest["validator"],
        manifest["document"],
    ):
        require((ROOT / source).is_file(), f"missing source file: {source}")

    for record in records:
        require(isinstance(record, dict), "record must be an object")
        validate_record(record, manifest)

    print(
        f"validated vendor API reference: {len(records)} records, "
        f"{reference['summary']['productionWriteKeyCount']} production write keys"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
