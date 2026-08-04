#!/usr/bin/env python3
"""Validate the versioned CMF Phone 2 Pro camera routing specification."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

SPEC_PATH = pathlib.Path("spec/camera-routing-spec.v1.json")
ISSUE_REFERENCE = re.compile(r"^issue:#([1-9][0-9]*)$")
VALID_STATUS = {"COMPLETE", "BOUNDED", "UNAVAILABLE"}
VALID_MECHANISM = {
    "STOCK_INTERNAL_ROUTE",
    "STOCK_CAMERA_HANDOFF",
    "PUBLIC_CAMERA2",
    "PUBLIC_ZOOM_OR_CROP",
    "UNAVAILABLE",
}
VALID_RENDERING = {"OPTICAL", "DIGITAL", "UNKNOWN"}
VALID_LAYERS = {
    "USER_INTENT",
    "APP",
    "STOCK_APP",
    "PUBLIC_API",
    "SESSION",
    "OPAQUE_BOUNDARY",
    "OUTPUT",
}
UNKNOWN_MARKERS = {"UNKNOWN", "UNRESOLVED", "UNKNOWN_SYSTEM_OR_VENDOR_ROUTE"}


def load_spec(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / SPEC_PATH).read_text(encoding="utf-8"))


def validate(root: pathlib.Path, spec: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if spec is None:
        try:
            spec = load_spec(root)
        except (OSError, json.JSONDecodeError) as error:
            return [f"cannot load {SPEC_PATH}: {error}"]

    if spec.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not _text(spec.get("routingVersion")):
        errors.append("routingVersion must be non-empty")
    device = spec.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        for field in ("marketingName", "codename", "buildScope"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")

    routes = spec.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append("routes must be a non-empty list")
        return errors

    route_ids: set[str] = set()
    for index, route in enumerate(routes):
        prefix = f"routes[{index}]"
        if not isinstance(route, dict):
            errors.append(f"{prefix} must be an object")
            continue
        route_id = route.get("id")
        if not _text(route_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif route_id in route_ids:
            errors.append(f"duplicate route id {route_id}")
        else:
            route_ids.add(route_id)

    for index, route in enumerate(routes):
        prefix = f"routes[{index}]"
        if not isinstance(route, dict):
            continue
        route_id = route.get("id")
        status = route.get("status")
        mechanism = route.get("mechanism")
        rendering = route.get("rendering")
        if status not in VALID_STATUS:
            errors.append(f"{prefix}.status is invalid")
        if mechanism not in VALID_MECHANISM:
            errors.append(f"{prefix}.mechanism is invalid")
        if rendering not in VALID_RENDERING:
            errors.append(f"{prefix}.rendering is invalid")

        trigger = route.get("trigger")
        if not isinstance(trigger, dict):
            errors.append(f"{prefix}.trigger must be an object")
        else:
            for field in ("surface", "action"):
                if not _text(trigger.get(field)):
                    errors.append(f"{prefix}.trigger.{field} must be non-empty")

        privilege = route.get("privilege")
        if not isinstance(privilege, dict):
            errors.append(f"{prefix}.privilege must be an object")
            privilege_required = None
        else:
            privilege_required = privilege.get("required")
            if not isinstance(privilege_required, bool):
                errors.append(f"{prefix}.privilege.required must be boolean")
            if not _text(privilege.get("identity")):
                errors.append(f"{prefix}.privilege.identity must be non-empty")

        target = route.get("target")
        if not isinstance(target, dict):
            errors.append(f"{prefix}.target must be an object")
            target = {}
        else:
            for field in ("opticalRoute", "cameraId", "activePhysicalSensor", "sensorScenario"):
                if not _text(target.get(field)):
                    errors.append(f"{prefix}.target.{field} must be non-empty")
        if status == "COMPLETE" and _contains_unknown(target):
            errors.append(f"{prefix} COMPLETE route cannot contain unknown target values")
        if target.get("cameraId") in {"2", "3", "4", "5"} and privilege_required is False:
            errors.append(f"{prefix} system camera ID cannot be ordinary-app accessible")

        steps = route.get("steps")
        step_count = 0
        if not isinstance(steps, list) or not steps:
            errors.append(f"{prefix}.steps must be a non-empty list")
        else:
            step_count = len(steps)
            for step_index, step in enumerate(steps, start=1):
                step_prefix = f"{prefix}.steps[{step_index - 1}]"
                if not isinstance(step, dict):
                    errors.append(f"{step_prefix} must be an object")
                    continue
                if step.get("order") != step_index:
                    errors.append(f"{step_prefix}.order must be {step_index}")
                if step.get("layer") not in VALID_LAYERS:
                    errors.append(f"{step_prefix}.layer is invalid")
                if not _text(step.get("action")):
                    errors.append(f"{step_prefix}.action must be non-empty")
                _validate_evidence(root, step.get("evidence"), step_prefix, errors)

        opaque = route.get("opaqueBoundary")
        if status == "BOUNDED":
            if not isinstance(opaque, dict):
                errors.append(f"{prefix} BOUNDED route requires opaqueBoundary")
            else:
                after_step = opaque.get("afterStep")
                before_step = opaque.get("beforeStep")
                if not isinstance(after_step, int) or not isinstance(before_step, int):
                    errors.append(f"{prefix}.opaqueBoundary steps must be integers")
                elif after_step < 1 or before_step > step_count or after_step >= before_step:
                    errors.append(f"{prefix}.opaqueBoundary step range is invalid")
                if not _text(opaque.get("description")):
                    errors.append(f"{prefix}.opaqueBoundary.description must be non-empty")
        elif opaque is not None:
            errors.append(f"{prefix} {status} route must not define opaqueBoundary")

        fallback = route.get("fallback")
        if status == "UNAVAILABLE" and not isinstance(fallback, dict):
            errors.append(f"{prefix} UNAVAILABLE route requires fallback")
        if isinstance(fallback, dict):
            fallback_id = fallback.get("routeId")
            if fallback_id not in route_ids:
                errors.append(f"{prefix}.fallback references unknown route {fallback_id!r}")
            if fallback_id == route_id:
                errors.append(f"{prefix}.fallback cannot reference itself")
            if not _text(fallback.get("condition")):
                errors.append(f"{prefix}.fallback.condition must be non-empty")
            if not _text(fallback.get("transparency")):
                errors.append(f"{prefix}.fallback.transparency must be non-empty")
        elif fallback is not None:
            errors.append(f"{prefix}.fallback must be an object or null")

        issue_count = _validate_issue_list(route.get("unknownIssues"), prefix, errors)
        if status in {"BOUNDED", "UNAVAILABLE"} and issue_count == 0:
            errors.append(f"{prefix} {status} route requires unknownIssues")
        if status == "UNAVAILABLE" and mechanism != "UNAVAILABLE":
            errors.append(f"{prefix} UNAVAILABLE route must use UNAVAILABLE mechanism")
        if rendering == "DIGITAL" and target.get("opticalRoute") not in {"main", "front"}:
            errors.append(f"{prefix} digital rendering cannot claim an auxiliary optical route")

    return errors


def _validate_evidence(
    root: pathlib.Path,
    evidence: Any,
    prefix: str,
    errors: list[str],
) -> None:
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{prefix}.evidence must be a non-empty list")
        return
    seen: set[str] = set()
    for index, reference in enumerate(evidence):
        evidence_prefix = f"{prefix}.evidence[{index}]"
        if not _text(reference):
            errors.append(f"{evidence_prefix} must be non-empty")
            continue
        if reference in seen:
            errors.append(f"{prefix}.evidence contains duplicate {reference}")
            continue
        seen.add(reference)
        if ISSUE_REFERENCE.match(reference) or reference.startswith("https://"):
            continue
        path = pathlib.PurePosixPath(reference)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{evidence_prefix} must be repository-relative")
        elif not (root / reference).is_file():
            errors.append(f"{evidence_prefix} path does not exist: {reference}")


def _validate_issue_list(value: Any, prefix: str, errors: list[str]) -> int:
    name = f"{prefix}.unknownIssues"
    if not isinstance(value, list):
        errors.append(f"{name} must be a list")
        return 0
    valid: set[int] = set()
    for entry in value:
        if not isinstance(entry, int) or isinstance(entry, bool) or entry <= 0:
            errors.append(f"{name} entries must be positive issue numbers")
        elif entry in valid:
            errors.append(f"{name} contains duplicate issue #{entry}")
        else:
            valid.add(entry)
    return len(valid)


def _contains_unknown(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_unknown(entry) for entry in value.values())
    if isinstance(value, list):
        return any(_contains_unknown(entry) for entry in value)
    if isinstance(value, str):
        upper = value.upper()
        return any(marker in upper for marker in UNKNOWN_MARKERS)
    return False


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    spec = load_spec(root)
    print(f"Validated {len(spec['routes'])} routes for {spec['routingVersion']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
