#!/usr/bin/env python3
"""Analyze controlled Nothing Camera Expert routing trace bundles.

The analyzer consumes the timestamped bundles produced by
``tools/device/run-expert-route-trace.sh``. It validates optical-route
association, extracts Camera2 routing evidence, summarizes vendor-key type
coverage, checks package privilege hints, and emits a conservative architecture
classification.

It never opens image files and never infers a lens route from requested UI
state alone. A route is accepted only when the non-image association metadata
matches the expected optical signature.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

ROUTES = ("06x", "1x", "2x")
MODES = ("camera2", "key-types")

EXPECTED_OPTICS = {
    "06x": {
        "focalLengthMm": 1.64,
        "focalToleranceMm": 0.12,
        "equivalentMm": 15.0,
        "equivalentToleranceMm": 1.0,
        "dimensions": {(3264, 2448), (2448, 3264)},
    },
    "1x": {
        "focalLengthMm": 5.56,
        "focalToleranceMm": 0.15,
        "equivalentMm": 24.0,
        "equivalentToleranceMm": 1.0,
        "dimensions": {(4080, 3072), (3072, 4080)},
    },
    "2x": {
        "focalLengthMm": 7.10,
        "focalToleranceMm": 0.20,
        "equivalentMm": 50.0,
        "equivalentToleranceMm": 2.0,
        "dimensions": {(4096, 3072), (3072, 4096)},
    },
}

ROUTING_KEY_PATTERN = re.compile(
    r"zoom|crop|focal|physical|sensorScenario|forceSensorMode|seamless|"
    r"insensor|remosaic|multicam|cameraFlex|flexibleCapabilities|pipDevices|"
    r"proprietaryRequest|initrequest|tnrOffByPhysicalIds|nothing\.camera|sois|supereis",
    re.IGNORECASE,
)

OPEN_EVENT_KINDS = {"open-camera", "ndk-open-camera"}
PHYSICAL_EVENT_KINDS = {
    "set-output-physical-id",
    "builder-set-physical-key",
    "active-physical-id",
}
TYPE_EVENT_KINDS = {
    "key-definition",
    "builder-set",
    "session-parameter-key",
    "session-parameters",
}
NOISE_FIELDS = {"timestampMs", "pid", "tid", "stack", "schema", "source"}


@dataclasses.dataclass
class Bundle:
    path: Path
    route: str
    mode: str
    created_at: str | None
    metadata: dict[str, Any]
    association: dict[str, Any] | None
    events: list[dict[str, Any]]
    package_text: str
    appops_text: str
    status_text: str
    warnings: list[str]


def parse_json_object_from_line(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text:
        return None
    candidates = [text]
    first_brace = text.find("{")
    if first_brace > 0:
        candidates.append(text[first_brace:])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        if value.get("type") == "send" and isinstance(value.get("payload"), dict):
            return value["payload"]
        return value
    return None


def iter_events(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        event = parse_json_object_from_line(line)
        if event is not None:
            yield event


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def normalize_route(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("×", "x")
    aliases = {
        "0.6x": "06x",
        ".6x": "06x",
        "06x": "06x",
        "0.6": "06x",
        "1": "1x",
        "1x": "1x",
        "2": "2x",
        "2x": "2x",
    }
    return aliases.get(text)


def discover_bundles(root: Path) -> list[Bundle]:
    bundles: list[Bundle] = []
    if not root.exists():
        return bundles

    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        metadata = read_json(directory / "run-metadata.json")
        if metadata is None:
            continue
        route = normalize_route(metadata.get("route"))
        mode = str(metadata.get("traceMode", "")).strip()
        if route not in ROUTES or mode not in MODES:
            continue

        warnings: list[str] = []
        association = read_json(directory / "output-association-template.json")
        events = list(iter_events(directory / "frida.log"))
        if not events:
            warnings.append("frida.log contained no parseable JSON events")
        if association is None:
            warnings.append("output-association-template.json is missing or invalid")
        if not (directory / "SHA256SUMS").exists():
            warnings.append("SHA256SUMS is missing")

        package_text = (
            read_text(directory / "package-dumpsys-after.txt")
            or read_text(directory / "package-dumpsys-before.txt")
        )
        appops_text = (
            read_text(directory / "appops-after.txt")
            or read_text(directory / "appops-before.txt")
        )
        status_text = read_text(directory / "run-status.txt")

        bundles.append(
            Bundle(
                path=directory,
                route=route,
                mode=mode,
                created_at=metadata.get("createdAtUtc"),
                metadata=metadata,
                association=association,
                events=events,
                package_text=package_text,
                appops_text=appops_text,
                status_text=status_text,
                warnings=warnings,
            )
        )
    return bundles


def parse_time(value: str | None) -> tuple[int, str]:
    if not value:
        return (0, "")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (1, parsed.astimezone(dt.timezone.utc).isoformat())
    except ValueError:
        return (0, value)


def choose_latest_bundles(bundles: Iterable[Bundle]) -> dict[tuple[str, str], Bundle]:
    selected: dict[tuple[str, str], Bundle] = {}
    for bundle in bundles:
        key = (bundle.route, bundle.mode)
        current = selected.get(key)
        candidate_key = (parse_time(bundle.created_at), bundle.path.name)
        current_key = (
            (parse_time(current.created_at), current.path.name)
            if current is not None
            else None
        )
        if current is None or candidate_key > current_key:
            selected[key] = bundle
    return selected


def to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def to_int(value: Any) -> int | None:
    number = to_float(value)
    if number is None or not math.isfinite(number):
        return None
    return int(round(number))


def validate_association(route: str, association: dict[str, Any] | None) -> dict[str, Any]:
    expected = EXPECTED_OPTICS[route]
    result: dict[str, Any] = {
        "status": "missing",
        "matches": False,
        "checks": {},
        "capture": None,
    }
    if association is None:
        return result

    capture = association.get("capture")
    if not isinstance(capture, dict):
        result["status"] = "invalid"
        return result

    result["capture"] = capture
    focal = to_float(capture.get("focalLengthMm"))
    equivalent = to_float(capture.get("focalLength35mmEquivalent"))
    width = to_int(capture.get("width"))
    height = to_int(capture.get("height"))

    focal_ok = (
        focal is not None
        and abs(focal - expected["focalLengthMm"]) <= expected["focalToleranceMm"]
    )
    equivalent_ok = (
        equivalent is not None
        and abs(equivalent - expected["equivalentMm"])
        <= expected["equivalentToleranceMm"]
    )
    dimensions_ok = (
        width is not None
        and height is not None
        and (width, height) in expected["dimensions"]
    )

    validation = association.get("validation")
    explicit = None
    if isinstance(validation, dict):
        explicit = validation.get("matchesAssignedOpticalRoute")

    result["checks"] = {
        "focalLength": focal_ok,
        "equivalentFocalLength": equivalent_ok,
        "dimensions": dimensions_ok,
        "explicitMatch": explicit,
    }

    supplied_count = sum(value is not None for value in (focal, equivalent, width, height))
    if explicit is False:
        result["status"] = "mismatch"
        return result
    if supplied_count < 4:
        result["status"] = "incomplete"
        return result
    if focal_ok and equivalent_ok and dimensions_ok:
        result["status"] = "verified"
        result["matches"] = True
        return result

    result["status"] = "mismatch"
    return result


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize_value(item)
            for key, item in sorted(value.items())
            if key not in NOISE_FIELDS
        }
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


def event_key_names(event: dict[str, Any]) -> list[str]:
    names: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value not in names:
            names.append(value)

    for field in ("key", "keyName", "name"):
        value = event.get(field)
        if isinstance(value, dict):
            add(value.get("name"))
        else:
            add(value)

    for field in ("request", "parameters", "sessionParameters", "values"):
        value = event.get(field)
        if isinstance(value, dict):
            for key in value:
                add(key)
    return names


def extract_open_ids(events: Iterable[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for event in events:
        if event.get("kind") not in OPEN_EVENT_KINDS:
            continue
        for field in ("cameraId", "id", "camera_id"):
            value = event.get(field)
            if value is not None:
                text = str(value)
                if text not in values:
                    values.append(text)
                break
    return values


def extract_physical_ids(events: Iterable[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for event in events:
        if event.get("kind") not in PHYSICAL_EVENT_KINDS:
            continue
        for field in ("physicalCameraId", "physicalId", "cameraId", "id", "value"):
            value = event.get(field)
            if isinstance(value, dict):
                value = value.get("value")
            if value is not None:
                text = str(value)
                if text not in values:
                    values.append(text)
                break
    return values


def routing_event_fingerprints(events: Iterable[dict[str, Any]]) -> list[str]:
    fingerprints: list[str] = []
    for event in events:
        names = event_key_names(event)
        relevant = (
            event.get("kind") in OPEN_EVENT_KINDS
            or event.get("kind") in PHYSICAL_EVENT_KINDS
            or any(ROUTING_KEY_PATTERN.search(name) for name in names)
        )
        if not relevant:
            continue
        normalized = normalize_value(event)
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        if encoded not in fingerprints:
            fingerprints.append(encoded)
    return fingerprints


def routing_key_values(events: Iterable[dict[str, Any]]) -> dict[str, list[Any]]:
    values: dict[str, list[Any]] = {}
    for event in events:
        names = event_key_names(event)
        for name in names:
            if not ROUTING_KEY_PATTERN.search(name):
                continue
            candidate: Any = None
            if isinstance(event.get("key"), dict):
                candidate = event.get("value")
            elif event.get("key") == name or event.get("keyName") == name:
                candidate = event.get("value")
            for field in ("request", "parameters", "sessionParameters", "values"):
                mapping = event.get(field)
                if isinstance(mapping, dict) and name in mapping:
                    candidate = mapping[name]
                    break
            normalized = normalize_value(candidate)
            bucket = values.setdefault(name, [])
            if normalized not in bucket:
                bucket.append(normalized)
    return values


def type_coverage(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    definitions: dict[str, dict[str, Any]] = {}
    stock_values: dict[str, list[Any]] = {}
    for event in events:
        if event.get("kind") not in TYPE_EVENT_KINDS:
            continue
        names = event_key_names(event)
        for name in names:
            if not ROUTING_KEY_PATTERN.search(name):
                continue
            key_value = event.get("key")
            if isinstance(key_value, dict):
                definitions[name] = {
                    field: key_value.get(field)
                    for field in (
                        "javaType",
                        "nativeType",
                        "vendorId",
                        "tag",
                        "keyJavaClass",
                        "nativeKeyJavaClass",
                    )
                    if key_value.get(field) is not None
                }
            candidate = event.get("value")
            if candidate is not None:
                bucket = stock_values.setdefault(name, [])
                normalized = normalize_value(candidate)
                if normalized not in bucket:
                    bucket.append(normalized)

    with_java_type = sum(bool(item.get("javaType")) for item in definitions.values())
    with_native_type = sum(bool(item.get("nativeType")) for item in definitions.values())
    return {
        "routingKeyDefinitions": definitions,
        "routingStockValues": stock_values,
        "definitionCount": len(definitions),
        "withJavaType": with_java_type,
        "withNativeType": with_native_type,
    }


def privilege_summary(package_text: str, appops_text: str) -> dict[str, Any]:
    lower = package_text.lower()
    system_camera_granted = bool(
        re.search(
            r"android\.permission\.system_camera\s*:\s*granted\s*=\s*true",
            package_text,
            re.IGNORECASE,
        )
    )
    system_camera_requested = "android.permission.system_camera" in lower
    privileged_flag = bool(
        re.search(r"\bprivileged\b", package_text, re.IGNORECASE)
        or re.search(r"pkgflags=\[[^\]]*\bsystem\b", package_text, re.IGNORECASE)
    )
    system_path = bool(
        re.search(
            r"(?:codepath|path|resourcepath)=/(?:system|system_ext|product|vendor)/",
            package_text,
            re.IGNORECASE,
        )
    )
    shared_uid = None
    match = re.search(
        r"(?:shareduid|shareduserid|userid)\s*=\s*([^\s,}]+)",
        package_text,
        re.IGNORECASE,
    )
    if match:
        shared_uid = match.group(1)

    appops_camera_allowed = bool(
        re.search(r"\bCAMERA\b[^\n]*(?:allow|foreground)", appops_text, re.IGNORECASE)
    )

    return {
        "systemCameraRequested": system_camera_requested,
        "systemCameraGranted": system_camera_granted,
        "privilegedOrSystemFlag": privileged_flag,
        "installedOnSystemPartition": system_path,
        "sharedOrUserId": shared_uid,
        "cameraAppOpAllowed": appops_camera_allowed,
    }


def route_specific_keys(
    per_route: dict[str, dict[str, list[Any]]]
) -> dict[str, dict[str, list[Any]]]:
    all_names = sorted({name for mapping in per_route.values() for name in mapping})
    result: dict[str, dict[str, list[Any]]] = {}
    for name in all_names:
        route_values = {route: per_route.get(route, {}).get(name, []) for route in ROUTES}
        encoded = {
            json.dumps(value, sort_keys=True, separators=(",", ":"))
            for value in route_values.values()
        }
        if len(encoded) > 1:
            result[name] = route_values
    return result


def classify_architecture(
    route_data: dict[str, dict[str, Any]],
    differing_keys: dict[str, dict[str, list[Any]]],
) -> dict[str, Any]:
    missing = [
        route
        for route in ROUTES
        if route not in route_data
        or route_data[route]["association"]["status"] != "verified"
        or not route_data[route]["openCameraIds"]
    ]
    if missing:
        return {
            "classification": "incomplete",
            "confidence": 0,
            "reason": "Missing verified optical association or Camera2 open evidence.",
            "missingRoutes": missing,
            "nextAction": "Collect or repair the missing controlled route bundles.",
        }

    open_ids = {route: route_data[route]["openCameraIds"] for route in ROUTES}
    primary = {route: ids[0] if len(ids) == 1 else tuple(ids) for route, ids in open_ids.items()}
    unique = {json.dumps(value, sort_keys=True) for value in primary.values()}
    physical_ids = {route: route_data[route]["physicalCameraIds"] for route in ROUTES}

    if len(unique) > 1:
        exact = [primary[route] for route in ROUTES] == ["2", "0", "3"]
        return {
            "classification": "direct-system-camera-route",
            "confidence": 4 if exact else 3,
            "reason": (
                "Each verified optical route opened a different Camera2 endpoint."
                if exact
                else "Verified optical routes opened route-dependent Camera2 endpoints."
            ),
            "openCameraIds": open_ids,
            "physicalCameraIds": physical_ids,
            "nextAction": (
                "Recover package authorization and characteristics for the non-public IDs, "
                "then build a minimal authorized direct-open reproducer."
            ),
        }

    common = next(iter(primary.values()))
    if common == "4":
        return {
            "classification": "system-logical-sat-route",
            "confidence": 3,
            "reason": "All verified routes opened system-only logical candidate ID 4.",
            "openCameraIds": open_ids,
            "physicalCameraIds": physical_ids,
            "differingRoutingKeys": sorted(differing_keys),
            "nextAction": (
                "Recover ID 4 logical/hidden-physical metadata and isolate the session or "
                "request state selecting each optical sensor."
            ),
        }

    if common == "0":
        if differing_keys or len({tuple(v) for v in physical_ids.values()}) > 1:
            return {
                "classification": "public-id-vendor-sat-route",
                "confidence": 3,
                "reason": (
                    "All verified routes opened public ID 0 while physical or routing metadata differed."
                ),
                "openCameraIds": open_ids,
                "physicalCameraIds": physical_ids,
                "differingRoutingKeys": sorted(differing_keys),
                "nextAction": (
                    "Reproduce the earliest route-specific session configuration using exact "
                    "target types and working stock values."
                ),
            }
        return {
            "classification": "lower-layer-route-unresolved",
            "confidence": 2,
            "reason": (
                "All verified routes opened public ID 0 with no observed Java Camera2 routing difference."
            ),
            "openCameraIds": open_ids,
            "physicalCameraIds": physical_ids,
            "nextAction": (
                "Trace JNI, Binder, CameraService/provider and HAL metadata around configureStreams "
                "and request submission."
            ),
        }

    return {
        "classification": "single-nonpublic-camera-route",
        "confidence": 2,
        "reason": f"All verified routes opened the same non-public endpoint {common!r}.",
        "openCameraIds": open_ids,
        "physicalCameraIds": physical_ids,
        "differingRoutingKeys": sorted(differing_keys),
        "nextAction": (
            "Determine whether the endpoint is a logical/SAT device and isolate its per-route state."
        ),
    }


def build_report(root: Path) -> dict[str, Any]:
    all_bundles = discover_bundles(root)
    selected = choose_latest_bundles(all_bundles)
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "root": str(root),
        "discoveredBundleCount": len(all_bundles),
        "selectedBundles": {},
        "routes": {},
        "vendorTypeCoverage": {},
        "privilege": {},
    }

    route_key_values: dict[str, dict[str, list[Any]]] = {}
    privilege_sources: list[dict[str, Any]] = []

    for route in ROUTES:
        camera_bundle = selected.get((route, "camera2"))
        key_bundle = selected.get((route, "key-types"))

        if camera_bundle is not None:
            association = validate_association(route, camera_bundle.association)
            route_values = routing_key_values(camera_bundle.events)
            route_key_values[route] = route_values
            route_record = {
                "camera2Bundle": str(camera_bundle.path),
                "createdAt": camera_bundle.created_at,
                "association": association,
                "openCameraIds": extract_open_ids(camera_bundle.events),
                "physicalCameraIds": extract_physical_ids(camera_bundle.events),
                "routingKeys": route_values,
                "routingEventCount": len(routing_event_fingerprints(camera_bundle.events)),
                "warnings": list(camera_bundle.warnings),
            }
            report["routes"][route] = route_record
            report["selectedBundles"][f"{route}:camera2"] = str(camera_bundle.path)
            privilege_sources.append(
                privilege_summary(camera_bundle.package_text, camera_bundle.appops_text)
            )

        if key_bundle is not None:
            report["selectedBundles"][f"{route}:key-types"] = str(key_bundle.path)
            report["vendorTypeCoverage"][route] = type_coverage(key_bundle.events)
            privilege_sources.append(
                privilege_summary(key_bundle.package_text, key_bundle.appops_text)
            )

    differing = route_specific_keys(route_key_values)
    report["routeSpecificRoutingKeys"] = differing
    report["architecture"] = classify_architecture(report["routes"], differing)

    if privilege_sources:
        report["privilege"] = {
            key: any(bool(item.get(key)) for item in privilege_sources)
            if key != "sharedOrUserId"
            else next((item.get(key) for item in privilege_sources if item.get(key)), None)
            for key in (
                "systemCameraRequested",
                "systemCameraGranted",
                "privilegedOrSystemFlag",
                "installedOnSystemPartition",
                "sharedOrUserId",
                "cameraAppOpAllowed",
            )
        }

    missing_modes = [
        f"{route}:{mode}"
        for route in ROUTES
        for mode in MODES
        if (route, mode) not in selected
    ]
    report["missingSelectedBundles"] = missing_modes
    report["completeSixRunMatrix"] = not missing_modes
    return report


def render_markdown(report: dict[str, Any]) -> str:
    architecture = report["architecture"]
    lines = [
        "# Expert Routing Bundle Analysis",
        "",
        f"- Classification: **{architecture['classification']}**",
        f"- Confidence: **{architecture['confidence']}/4**",
        f"- Reason: {architecture['reason']}",
        f"- Six-run matrix complete: **{str(report['completeSixRunMatrix']).lower()}**",
        "",
        "## Route evidence",
        "",
        "| Route | Association | Open IDs | Physical IDs | Routing keys |",
        "|---|---|---|---|---:|",
    ]

    for route in ROUTES:
        data = report["routes"].get(route)
        if data is None:
            lines.append(f"| {route} | missing | — | — | 0 |")
            continue
        lines.append(
            "| {route} | {association} | {open_ids} | {physical_ids} | {count} |".format(
                route=route,
                association=data["association"]["status"],
                open_ids=", ".join(data["openCameraIds"]) or "—",
                physical_ids=", ".join(data["physicalCameraIds"]) or "—",
                count=len(data["routingKeys"]),
            )
        )

    lines.extend(["", "## Route-specific routing metadata", ""])
    differing = report.get("routeSpecificRoutingKeys", {})
    if not differing:
        lines.append("No route-specific routing-key value was found in the selected Camera2 traces.")
    else:
        for name, values in differing.items():
            lines.append(f"### `{name}`")
            lines.append("")
            for route in ROUTES:
                rendered = json.dumps(values.get(route, []), sort_keys=True)
                lines.append(f"- `{route}`: `{rendered}`")
            lines.append("")

    lines.extend(["## Package privilege indicators", ""])
    privilege = report.get("privilege", {})
    if privilege:
        for key, value in privilege.items():
            lines.append(f"- `{key}`: `{json.dumps(value)}`")
    else:
        lines.append("No package dump or app-op evidence was available.")

    lines.extend(["", "## Vendor-key type recovery", ""])
    coverage = report.get("vendorTypeCoverage", {})
    if coverage:
        lines.append("| Route | Definitions | Java type recovered | Native type recovered |")
        lines.append("|---|---:|---:|---:|")
        for route in ROUTES:
            item = coverage.get(route, {})
            lines.append(
                f"| {route} | {item.get('definitionCount', 0)} | "
                f"{item.get('withJavaType', 0)} | {item.get('withNativeType', 0)} |"
            )
    else:
        lines.append("No key-type trace was selected.")

    lines.extend(
        [
            "",
            "## Next action",
            "",
            architecture["nextAction"],
            "",
            "## Evidence caveats",
            "",
            "- The classifier requires verified non-image optical metadata for each route.",
            "- A route-specific value is a discriminator candidate, not causal proof.",
            "- Exact vendor-key types and working stock values are required before any write test.",
            "- The report does not inspect or copy photographs.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("traces/expert-routing"),
        help="Directory containing timestamped trace bundles.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write the full machine-readable report.",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=None,
        help="Write a human-readable report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless the six-run matrix is complete and architecture is resolved.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(args.root)
    markdown = render_markdown(report)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown, encoding="utf-8")

    if not args.json and not args.markdown:
        print(markdown)

    if args.strict:
        unresolved = report["architecture"]["classification"] in {
            "incomplete",
            "lower-layer-route-unresolved",
        }
        if not report["completeSixRunMatrix"] or unresolved:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
