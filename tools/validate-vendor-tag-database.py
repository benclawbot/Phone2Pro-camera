#!/usr/bin/env python3
"""Validate the materialized Galaga vendor-tag database."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from typing import Any

ROOT_DEFAULT = pathlib.Path(".")
BUILDER_PATH = pathlib.Path("tools/build-vendor-tag-database.py")
DOCUMENT_PATH = pathlib.Path("docs/VENDOR_TAG_DATABASE.md")
MANIFEST_PATH = pathlib.Path("data/vendor-tags/database.v1.json")
VALID_DIRECTIONS = {"characteristic", "request", "result", "session", "physical-request"}
VALID_TYPE_STATUS = {
    "UNKNOWN",
    "PUBLIC_SOURCE_HINT_UNVERIFIED_ON_TARGET",
    "TARGET_RUNTIME_VERIFIED",
    "TARGET_BINARY_VERIFIED",
}
SAFE_PRODUCTION_STATUS = {"DISABLED", "READ_ONLY_DIAGNOSTIC", "VERIFIED_ADAPTER_ONLY"}


def load_builder(root: pathlib.Path):
    path = root / BUILDER_PATH
    spec = importlib.util.spec_from_file_location("build_vendor_tag_database", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(
    root: pathlib.Path,
    *,
    manifest: dict[str, Any] | None = None,
    database: dict[str, Any] | None = None,
    document: str | None = None,
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    try:
        manifest = manifest if manifest is not None else load_json(root / MANIFEST_PATH)
        builder = load_builder(root)
        database = database if database is not None else builder.build_database(root)
        document = document if document is not None else (root / DOCUMENT_PATH).read_text(encoding="utf-8")
        inventory = load_json(root / manifest["sourceFiles"]["inventory"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as error:
        return [f"cannot build vendor-tag database: {error}"]

    if manifest.get("schemaVersion") != 1 or database.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    version = manifest.get("databaseVersion")
    if not text(version) or database.get("databaseVersion") != version:
        errors.append("databaseVersion must be non-empty and consistent")
    if manifest.get("issue") != 55 or database.get("issue") != 55:
        errors.append("issue must be 55")
    if f"**Database version:** `{version}`" not in document:
        errors.append("document database version does not match")

    build = manifest.get("buildContext")
    if not isinstance(build, dict):
        errors.append("buildContext must be an object")
        build = {}
    expected_build = ("Galaga", "A001", "2606151653")
    actual_build = (build.get("device"), build.get("model"), build.get("firmwareBuild"))
    if actual_build != expected_build or not text(build.get("fingerprint")):
        errors.append("buildContext is invalid")
    if build.get("publicCameraIds") != ["0", "1"]:
        errors.append("publicCameraIds must be 0 and 1")
    if database.get("buildContext") != build:
        errors.append("materialized buildContext differs from manifest")

    sources = manifest.get("sourceFiles")
    if not isinstance(sources, dict) or not sources:
        errors.append("sourceFiles must be non-empty")
        sources = {}
    for label, path in sources.items():
        if not text(label) or not text(path) or not (root / str(path)).is_file():
            errors.append(f"source file {label!r} is missing")

    rules = manifest.get("interpretationRules")
    if not isinstance(rules, list) or len(rules) < 6 or not all(text(item) for item in rules):
        errors.append("interpretationRules must contain six explicit boundaries")
    if database.get("interpretationRules") != rules:
        errors.append("materialized interpretation rules differ from manifest")

    required_fields = manifest.get("requiredMaterializedFields")
    if not isinstance(required_fields, list) or len(required_fields) != len(set(required_fields)):
        errors.append("requiredMaterializedFields must be a unique list")
        required_fields = []

    records = database.get("records")
    if not isinstance(records, list):
        errors.append("records must be a list")
        records = []
    names: set[str] = set()
    target_verified_count = 0
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = [field for field in required_fields if field not in record]
        if missing:
            errors.append(f"{prefix} is missing fields: {missing}")
        name = record.get("name")
        if not text(name) or name in names:
            errors.append(f"{prefix}.name must be unique and non-empty")
            continue
        names.add(str(name))
        if not text(record.get("family")):
            errors.append(f"{prefix}.family must be non-empty")
        directions = record.get("directions")
        if (
            not isinstance(directions, list)
            or not directions
            or any(direction not in VALID_DIRECTIONS for direction in directions)
            or directions != sorted(set(directions))
        ):
            errors.append(f"{prefix}.directions is invalid")
        camera_ids = record.get("cameraIds")
        if not isinstance(camera_ids, list) or not camera_ids or any(camera_id not in {"0", "1"} for camera_id in camera_ids):
            errors.append(f"{prefix}.cameraIds is invalid")
        if record.get("buildContext") != build:
            errors.append(f"{prefix}.buildContext must match the manifest")
        advertised = record.get("advertisedValues")
        if not isinstance(advertised, dict) or any(camera_id not in {"0", "1"} for camera_id in advertised):
            errors.append(f"{prefix}.advertisedValues is invalid")
        type_status = record.get("typeStatus")
        if type_status not in VALID_TYPE_STATUS:
            errors.append(f"{prefix}.typeStatus is invalid")
        if type_status in {"TARGET_RUNTIME_VERIFIED", "TARGET_BINARY_VERIFIED"}:
            target_verified_count += 1
            if record.get("javaType") is None and record.get("nativeType") is None:
                errors.append(f"{prefix} verified type requires a concrete type")
        elif record.get("vendorId") is not None or record.get("tagId") is not None:
            errors.append(f"{prefix} unverified type cannot claim vendor/tag IDs")
        if not text(record.get("byteLayoutStatus")) or not text(record.get("byteLayoutDescription")):
            errors.append(f"{prefix} byte-layout uncertainty must be explicit")
        call_status = record.get("callSiteStatus")
        call_sites = record.get("stockCallSites")
        if call_status not in {"UNRESOLVED", "PARTIAL", "VERIFIED"} or not isinstance(call_sites, list):
            errors.append(f"{prefix} call-site record is invalid")
        if call_status == "VERIFIED" and not call_sites:
            errors.append(f"{prefix} verified call site requires evidence")
        for field in ("externalSourceRefs", "sourceRefs"):
            paths = record.get(field)
            if not isinstance(paths, list) or len(paths) != len(set(paths)):
                errors.append(f"{prefix}.{field} must be a unique list")
                continue
            for path in paths:
                if not text(path) or not (root / str(path)).is_file():
                    errors.append(f"{prefix}.{field} references missing path {path!r}")
        if not text(record.get("writePolicy")):
            errors.append(f"{prefix}.writePolicy must be explicit")
        if record.get("productionStatus") not in SAFE_PRODUCTION_STATUS:
            errors.append(f"{prefix}.productionStatus is invalid")
        if record.get("productionStatus") == "VERIFIED_ADAPTER_ONLY" and type_status not in {
            "TARGET_RUNTIME_VERIFIED",
            "TARGET_BINARY_VERIFIED",
        }:
            errors.append(f"{prefix} cannot enable an unverified vendor type")

    inventory_count = inventory.get("summary", {}).get("totalVendorKeys")
    summary = database.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        summary = {}
    if summary.get("inventoryKeyCount") != inventory_count:
        errors.append("inventoryKeyCount must equal the authoritative inventory")
    if summary.get("totalRecordCount") != len(records):
        errors.append("totalRecordCount must equal records length")
    if len(records) < int(inventory_count or 0):
        errors.append("materialized database cannot omit inventory keys")
    direction_counts = summary.get("directionCounts")
    if not isinstance(direction_counts, dict) or set(direction_counts) != VALID_DIRECTIONS:
        errors.append("directionCounts must cover every direction")
    else:
        for direction in VALID_DIRECTIONS:
            actual = sum(direction in record.get("directions", []) for record in records if isinstance(record, dict))
            if direction_counts.get(direction) != actual:
                errors.append(f"direction count drift for {direction}")

    if target_verified_count != 0:
        errors.append("the current database must not claim target-verified types without committed traces")
    if "162" not in document or "UNKNOWN" not in document:
        errors.append("document must state inventory size and unknown-type boundary")
    for path in (str(MANIFEST_PATH), str(BUILDER_PATH)):
        if path not in document:
            errors.append(f"document is missing {path}")

    maintenance = manifest.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        expected = {
            "builder": str(BUILDER_PATH),
            "validator": "tools/validate-vendor-tag-database.py",
            "document": str(DOCUMENT_PATH),
        }
        for field, value in expected.items():
            if maintenance.get(field) != value:
                errors.append(f"maintenance.{field} is incorrect")
        triggers = maintenance.get("updateTriggers")
        if not isinstance(triggers, list) or len(triggers) < 4 or not all(text(item) for item in triggers):
            errors.append("maintenance updateTriggers are incomplete")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=ROOT_DEFAULT)
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Vendor-tag database is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
