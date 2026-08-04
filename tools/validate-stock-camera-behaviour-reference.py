#!/usr/bin/env python3
"""Validate the versioned stock-camera behaviour reference."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

REFERENCE = pathlib.Path("data/stock-camera/behaviour-reference.v1.json")
MODES = {"expert", "photo", "portrait", "night", "video"}
CLASSES = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def load_reference(root: pathlib.Path) -> dict[str, Any]:
    value = json.loads((root / REFERENCE).read_text(encoding="utf-8"))
    require(isinstance(value, dict), "reference must be an object")
    return value


def validate_reference(ref: dict[str, Any], root: pathlib.Path) -> None:
    require(ref.get("schemaVersion") == 1, "schemaVersion must be 1")
    require(ref.get("issue") == 99, "reference must bind issue 99")
    target = ref.get("targetBuild")
    require(isinstance(target, dict), "targetBuild is required")
    build = target.get("matrixEntryId")
    require(isinstance(build, str) and build, "matrixEntryId is required")

    registry = ref.get("evidenceRegistry")
    require(isinstance(registry, dict) and registry, "evidenceRegistry is required")
    for key, item in registry.items():
        require(isinstance(item, dict), f"{key}: evidence must be an object")
        require(item.get("classification") in CLASSES, f"{key}: invalid evidence class")
        path = item.get("path")
        require(isinstance(path, str) and (root / path).exists(), f"{key}: missing evidence path")

    modes = ref.get("modes")
    require(isinstance(modes, list), "modes must be an array")
    require({m.get("id") for m in modes if isinstance(m, dict)} == MODES, "exactly five required modes must exist")
    require(len(modes) == 5, "mode IDs must be unique")

    for mode in modes:
        require(isinstance(mode, dict), "mode must be an object")
        mode_id = mode.get("id")
        require(mode.get("status") in CLASSES, f"{mode_id}: invalid status")
        require(mode.get("buildScope") == build, f"{mode_id}: build scope drift")
        require(mode.get("decision") in {"REFERENCE_ONLY_PRIVILEGED_ROUTE", "GAP_REQUIRES_STOCK_TRACE"}, f"{mode_id}: invalid decision")
        require(isinstance(mode.get("unknowns"), list) and mode["unknowns"], f"{mode_id}: unknowns must remain explicit")
        require(isinstance(mode.get("routes"), list), f"{mode_id}: routes must be an array")

        for section in ("captureSequence", "metadata", "processing", "latency", "fallbacks"):
            item = mode.get(section)
            require(isinstance(item, dict), f"{mode_id}: {section} must be an object")
            require(item.get("status") in CLASSES, f"{mode_id}: invalid {section} status")
        latency = mode["latency"]
        require(isinstance(latency.get("metrics"), dict), f"{mode_id}: latency metrics must be an object")
        if latency["status"] == "UNKNOWN":
            require(not latency["metrics"], f"{mode_id}: unknown latency cannot contain metrics")

        for field in ("observedClaims", "inferredClaims"):
            claims = mode.get(field)
            require(isinstance(claims, list), f"{mode_id}: {field} must be an array")
            for claim in claims:
                require(isinstance(claim, dict), f"{mode_id}: claim must be an object")
                require(claim.get("class") in CLASSES, f"{mode_id}: invalid claim class")
                refs = claim.get("evidence")
                require(isinstance(refs, list) and refs, f"{mode_id}: claim needs evidence")
                require(all(r in registry for r in refs), f"{mode_id}: claim uses unknown evidence")
                if field == "inferredClaims":
                    require(claim.get("class") != "VERIFIED", f"{mode_id}: inference cannot be VERIFIED")

        protocol = mode.get("protocol")
        require(isinstance(protocol, dict), f"{mode_id}: protocol is required")
        require(isinstance(protocol.get("artifacts"), list) and protocol["artifacts"], f"{mode_id}: protocol artifacts required")
        require(isinstance(protocol.get("steps"), list) and protocol["steps"], f"{mode_id}: protocol steps required")

    expert = next(m for m in modes if m["id"] == "expert")
    routes = {(r.get("control"), r.get("endpoint"), r.get("physicalMm")) for r in expert["routes"]}
    require(routes == {("0.6x", 2, 1.64), ("1x", 0, 5.56), ("2x", 3, 7.1)}, "Expert route table drift")
    require(expert["decision"] == "REFERENCE_ONLY_PRIVILEGED_ROUTE", "Expert must remain privileged-reference-only")

    for mode in modes:
        if mode["id"] != "expert":
            require(mode["decision"] == "GAP_REQUIRES_STOCK_TRACE", f"{mode['id']}: unsupported mode marked ready")

    night = next(m for m in modes if m["id"] == "night")
    diagnostic = [c for c in night["observedClaims"] if "diagnostic" in c.get("text", "").lower()]
    require(diagnostic and all(c.get("nonStock") is True for c in diagnostic), "Night diagnostic evidence must remain non-stock")

    video = next(m for m in modes if m["id"] == "video")
    public = [c for c in video["observedClaims"] if "public rear" in c.get("text", "").lower()]
    require(public and all(c.get("nonStock") is True for c in public), "Video public capability must remain non-stock")

    summary = ref.get("summary")
    require(isinstance(summary, dict), "summary is required")
    require(summary.get("modeCount") == 5, "summary mode count drift")
    require(summary.get("expertRouteCount") == 3, "summary Expert route count drift")
    require(summary.get("gapModeCount") == 4, "summary gap count drift")
    require(summary.get("measuredLatencyMetricCount") == 0, "unmeasured latency must remain zero")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    validate_reference(load_reference(root), root)
    print("stock-camera behaviour reference: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
