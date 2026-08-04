#!/usr/bin/env python3
"""Materialize the Galaga vendor-tag database from committed inventories."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
from typing import Any

import yaml

MANIFEST_PATH = pathlib.Path("data/vendor-tags/database.v1.json")
DIRECTIONS = {"characteristic", "request", "result", "session", "physical-request"}
CAMERAS = {"0": "rear", "1": "front"}


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def load_manifest(root: pathlib.Path) -> dict[str, Any]:
    return load_json(root / MANIFEST_PATH)


def normalize_domains(values: Any) -> list[str]:
    result: set[str] = set()
    if not isinstance(values, list):
        return []
    for value in values:
        if not isinstance(value, str):
            continue
        if value in DIRECTIONS:
            result.add(value)
        else:
            prefix = value.split("-", 1)[0]
            if prefix in DIRECTIONS:
                result.add(prefix)
    return sorted(result)


def inventory_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    families = inventory.get("families", {})
    if not isinstance(families, dict):
        return result
    for family, data in families.items():
        if not isinstance(family, str) or not isinstance(data, dict):
            continue
        rear_only = set(data.get("rearOnly", [])) if isinstance(data.get("rearOnly"), list) else set()
        front_only = set(data.get("frontOnly", [])) if isinstance(data.get("frontOnly"), list) else set()
        for direction, names in data.items():
            if direction not in DIRECTIONS or not isinstance(names, list):
                continue
            for name in names:
                if not isinstance(name, str):
                    continue
                record = result.setdefault(
                    name,
                    {
                        "name": name,
                        "family": family,
                        "directions": set(),
                        "rearOnly": False,
                        "frontOnly": False,
                    },
                )
                record["directions"].add(direction)
                record["rearOnly"] = bool(record["rearOnly"] or name in rear_only)
                record["frontOnly"] = bool(record["frontOnly"] or name in front_only)
    return result


def routing_index(routing: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    groups = routing.get("priorityGroups", [])
    if not isinstance(groups, list):
        return result
    for group in groups:
        if not isinstance(group, dict):
            continue
        keys = group.get("keys", [])
        if not isinstance(keys, list):
            continue
        for key in keys:
            if not isinstance(key, dict) or not isinstance(key.get("name"), str):
                continue
            result[key["name"]] = {
                "groupId": group.get("id"),
                "rank": group.get("rank"),
                "objective": group.get("objective"),
                "observedDomains": copy.deepcopy(key.get("observedDomains", [])),
                "nativeType": key.get("nativeType"),
                "typeEvidence": key.get("typeEvidence"),
                "writePolicy": key.get("writePolicy"),
                "characteristicValue": copy.deepcopy(key.get("characteristicValue")),
                "observedValue": copy.deepcopy(key.get("observedValue")),
            }
    return result


def camera_ids(record: dict[str, Any]) -> list[str]:
    if record.get("rearOnly") and not record.get("frontOnly"):
        return ["0"]
    if record.get("frontOnly") and not record.get("rearOnly"):
        return ["1"]
    return ["0", "1"]


def advertised_values(name: str, advertised: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for camera_id, label in CAMERAS.items():
        camera_values = advertised.get(label, {})
        if isinstance(camera_values, dict) and name in camera_values:
            values[camera_id] = copy.deepcopy(camera_values[name])
    return values


def family_for(name: str) -> str:
    pieces = name.split(".")
    if pieces and pieces[0] == "com":
        pieces = pieces[1:]
    return ".".join(pieces[:-1]) if len(pieces) > 1 else name


def build_database(root: pathlib.Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_manifest(root)
    sources = manifest["sourceFiles"]
    inventory = load_json(root / sources["inventory"])
    advertised = load_json(root / sources["advertisedValues"])
    routing = load_yaml(root / sources["routingPriority"])
    records = inventory_index(inventory)
    route_records = routing_index(routing)
    hints = {
        item["key"]: item
        for item in manifest.get("typeHints", [])
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    }
    defaults = manifest["defaultRecordPolicy"]
    context = manifest["buildContext"]

    routing_only = sorted(set(route_records) - set(records))
    for name in routing_only:
        route = route_records[name]
        records[name] = {
            "name": name,
            "family": family_for(name),
            "directions": set(normalize_domains(route.get("observedDomains"))),
            "rearOnly": True,
            "frontOnly": False,
            "routingOnly": True,
        }

    materialized: list[dict[str, Any]] = []
    for name in sorted(records):
        source = records[name]
        route = route_records.get(name)
        hint = hints.get(name, {})
        record = {
            "name": name,
            "family": source["family"],
            "directions": sorted(source["directions"]),
            "cameraIds": camera_ids(source),
            "buildContext": copy.deepcopy(context),
            "advertisedValues": advertised_values(name, advertised),
            "javaType": hint.get("javaType", defaults.get("javaType")),
            "nativeType": hint.get("nativeType", defaults.get("nativeType")),
            "vendorId": hint.get("vendorId", defaults.get("vendorId")),
            "tagId": hint.get("tagId", defaults.get("tagId")),
            "typeStatus": hint.get("typeStatus", defaults["typeStatus"]),
            "byteLayoutStatus": hint.get("byteLayoutStatus", defaults["byteLayoutStatus"]),
            "byteLayoutDescription": hint.get("byteLayoutDescription", defaults["byteLayoutDescription"]),
            "callSiteStatus": defaults["callSiteStatus"],
            "stockCallSites": copy.deepcopy(defaults["stockCallSites"]),
            "externalSourceRefs": sorted(set(hint.get("externalSourceRefs", []))),
            "writePolicy": defaults["writePolicy"],
            "productionStatus": defaults["productionStatus"],
            "routingPriority": None,
            "sourceRefs": [sources["inventory"]],
            "sourceInventoryStatus": "ROUTING_TRACE_ONLY" if source.get("routingOnly") else "STATIC_CHARACTERISTICS_INVENTORY",
        }
        if record["advertisedValues"]:
            record["sourceRefs"].append(sources["advertisedValues"])
        if route:
            record["routingPriority"] = {
                "groupId": route.get("groupId"),
                "rank": route.get("rank"),
                "objective": route.get("objective"),
                "observedDomains": normalize_domains(route.get("observedDomains")),
                "characteristicValue": route.get("characteristicValue"),
                "observedValue": route.get("observedValue"),
            }
            record["sourceRefs"].append(sources["routingPriority"])
            record["writePolicy"] = route.get("writePolicy") or record["writePolicy"]
            route_type = route.get("nativeType")
            if record["nativeType"] is None and isinstance(route_type, str) and route_type != "pending-runtime-recovery":
                record["nativeType"] = route_type
                record["typeStatus"] = "PUBLIC_SOURCE_HINT_UNVERIFIED_ON_TARGET"
            if route.get("typeEvidence"):
                record["externalSourceRefs"] = sorted(
                    set(record["externalSourceRefs"] + [sources["publicCrossReference"], sources["externalSourceIndex"]])
                )
        record["sourceRefs"] = sorted(set(record["sourceRefs"]))
        materialized.append(record)

    direction_counts = {direction: 0 for direction in sorted(DIRECTIONS)}
    for record in materialized:
        for direction in record["directions"]:
            direction_counts[direction] += 1

    return {
        "schemaVersion": 1,
        "databaseVersion": manifest["databaseVersion"],
        "issue": manifest["issue"],
        "buildContext": copy.deepcopy(context),
        "summary": {
            "inventoryKeyCount": len(records) - len(routing_only),
            "routingOnlyKeyCount": len(routing_only),
            "totalRecordCount": len(materialized),
            "directionCounts": direction_counts,
        },
        "records": materialized,
        "interpretationRules": copy.deepcopy(manifest["interpretationRules"]),
        "sourceFiles": copy.deepcopy(sources),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    database = build_database(args.root)
    payload = json.dumps(database, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
