#!/usr/bin/env python3
"""Validate and render the Galaga camera privilege-boundary model."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import sys
from typing import Any

ACCESS_CLASSES = {"PUBLIC", "HIDDEN_CALLABLE", "PRIVILEGED", "ROOT_ONLY", "FIRMWARE_INTERNAL"}
BOUNDARY_STATES = {"NO_REJECTION_OBSERVED", "FILTERED", "REJECTED", "UNRESOLVED", "REQUIRES_POLICY_CHANGE"}
CLASSIFICATIONS = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}


class BoundaryModelError(ValueError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_model_path() -> Path:
    return repository_root() / "research/boundaries/galaga-camera-privilege-boundaries.json"


def load_model(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BoundaryModelError(f"cannot load boundary model: {error}") from error
    if not isinstance(value, dict):
        raise BoundaryModelError("model root must be an object")
    return value


def text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BoundaryModelError(f"{name} must be non-empty text")
    return value.strip()


def index(items: Any, name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        raise BoundaryModelError(f"{name} must be a non-empty list")
    output: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            raise BoundaryModelError(f"{name}[{position}] must be an object")
        item_id = text(item.get("id"), f"{name}[{position}].id")
        if item_id in output:
            raise BoundaryModelError(f"duplicate {name} id: {item_id}")
        output[item_id] = item
    return output


def validate_boundary(value: Any, name: str, layers: set[str], required: bool) -> dict[str, Any] | None:
    if value is None and not required:
        return None
    if not isinstance(value, dict):
        raise BoundaryModelError(f"{name} must be an object")
    layer = value.get("layer")
    if layer is not None and layer not in layers:
        raise BoundaryModelError(f"{name} references unknown layer {layer}")
    state = text(value.get("state"), f"{name}.state")
    classification = text(value.get("classification"), f"{name}.classification")
    if state not in BOUNDARY_STATES:
        raise BoundaryModelError(f"{name} has invalid state {state}")
    if classification not in CLASSIFICATIONS:
        raise BoundaryModelError(f"{name} has invalid classification {classification}")
    text(value.get("reason"), f"{name}.reason")
    return value


def validate_model(model: dict[str, Any]) -> dict[str, Any]:
    if model.get("schemaVersion") != 1:
        raise BoundaryModelError("schemaVersion must be 1")
    device = model.get("device")
    if not isinstance(device, dict):
        raise BoundaryModelError("device must be an object")
    for field in ("model", "codename", "androidVersion", "soc"):
        text(device.get(field), f"device.{field}")

    access = index(model.get("accessClasses"), "accessClasses")
    if set(access) != ACCESS_CLASSES:
        raise BoundaryModelError(f"access classes must be exactly {sorted(ACCESS_CLASSES)}")
    for item_id, item in access.items():
        text(item.get("label"), f"accessClasses.{item_id}.label")
        text(item.get("definition"), f"accessClasses.{item_id}.definition")

    layers = index(model.get("layers"), "layers")
    for item_id, item in layers.items():
        text(item.get("label"), f"layers.{item_id}.label")

    evidence = model.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        raise BoundaryModelError("evidence must be a non-empty object")
    for item_id, item in evidence.items():
        if not isinstance(item, dict):
            raise BoundaryModelError(f"evidence.{item_id} must be an object")
        if text(item.get("classification"), f"evidence.{item_id}.classification") not in CLASSIFICATIONS:
            raise BoundaryModelError(f"evidence.{item_id} has invalid classification")
        text(item.get("path"), f"evidence.{item_id}.path")
        text(item.get("supports"), f"evidence.{item_id}.supports")

    deployments = index(model.get("deploymentClasses"), "deploymentClasses")
    for item_id, item in deployments.items():
        text(item.get("label"), f"deploymentClasses.{item_id}.label")
        text(item.get("consequence"), f"deploymentClasses.{item_id}.consequence")
        for field in ("allowedAccessClasses", "conditionalAccessClasses", "prohibitedClaims"):
            values = item.get(field)
            if not isinstance(values, list) or set(values) - ACCESS_CLASSES:
                raise BoundaryModelError(f"deploymentClasses.{item_id}.{field} is invalid")

    features = index(model.get("features"), "features")
    for item_id, item in features.items():
        for field in ("label", "route", "status", "replacementConsequence"):
            text(item.get(field), f"features.{item_id}.{field}")
        if item.get("accessClass") not in ACCESS_CLASSES:
            raise BoundaryModelError(f"features.{item_id}.accessClass is invalid")
        validate_boundary(item.get("firstBoundary"), f"features.{item_id}.firstBoundary", set(layers), True)
        validate_boundary(item.get("hardRejection"), f"features.{item_id}.hardRejection", set(layers), False)
        refs = item.get("evidence")
        if not isinstance(refs, list) or not refs or set(refs) - set(evidence):
            raise BoundaryModelError(f"features.{item_id}.evidence is invalid")
        supported = item.get("supportedDeployments")
        if not isinstance(supported, list) or not supported or set(supported) - set(deployments):
            raise BoundaryModelError(f"features.{item_id}.supportedDeployments is invalid")

    for item_id in ("direct-ultrawide", "direct-telephoto"):
        item = features.get(item_id)
        if not item or item.get("accessClass") != "PRIVILEGED":
            raise BoundaryModelError(f"{item_id} must remain PRIVILEGED")
        first = item["firstBoundary"]
        hard = item.get("hardRejection")
        if first.get("layer") != "CAMERA_SERVICE_ENUMERATION" or first.get("state") != "FILTERED":
            raise BoundaryModelError(f"{item_id} must preserve enumeration filtering")
        if not hard or hard.get("layer") != "CAMERA_SERVICE_CHARACTERISTICS" or hard.get("state") != "REJECTED":
            raise BoundaryModelError(f"{item_id} must preserve characteristics rejection")

    return {"access": access, "layers": layers, "evidence": evidence, "deployments": deployments, "features": features}


def build_report(model: dict[str, Any]) -> dict[str, Any]:
    validated = validate_model(model)
    features = list(validated["features"].values())
    unresolved = [item["id"] for item in features if item["firstBoundary"]["classification"] in {"UNKNOWN", "HYPOTHESIS"} or item["firstBoundary"]["state"] == "UNRESOLVED"]
    rejected = [item["id"] for item in features if item["firstBoundary"]["state"] == "REJECTED" or item.get("hardRejection", {}).get("state") == "REJECTED"]
    return {
        "schemaVersion": 1,
        "device": model["device"],
        "accessClasses": model["accessClasses"],
        "layers": model["layers"],
        "deploymentClasses": model["deploymentClasses"],
        "features": features,
        "evidence": model["evidence"],
        "summary": {
            "featureCount": len(features),
            "byAccessClass": dict(sorted(collections.Counter(item["accessClass"] for item in features).items())),
            "byFirstBoundary": dict(sorted(collections.Counter(item["firstBoundary"]["layer"] or "NONE" for item in features).items())),
            "byHardRejection": dict(sorted(collections.Counter(item.get("hardRejection", {}).get("layer", "NONE") for item in features).items())),
            "rejectedFeatureIds": rejected,
            "unresolvedFeatureIds": unresolved,
        },
        "evidenceBoundary": {
            "verified": "Observed route tables, public visibility, system-only characteristics rejections, and recorded API error namespaces are preserved as verified evidence.",
            "partiallyVerified": "AOSP method anchors and deployment consequences identify the expected boundary without proving the target implementation is byte-identical or sufficient for access.",
            "unknown": "Connect-stage privilege parity, route-specific vendor session state, provider/HAL selection, SELinux grants, and ISP tuning contracts remain unknown until measured.",
        },
    }


def escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def node_id(value: str) -> str:
    return "n_" + "".join(character if character.isalnum() else "_" for character in value)


def render_markdown(report: dict[str, Any]) -> str:
    device = report["device"]
    lines = [
        "# Galaga camera privilege-boundary diagram", "",
        "Status: executable per-feature enforcement map for CAM-086.", "",
        f"Target: **{device['model']}** (`{device['codename']}`), Android {device['androidVersion']}, {device['soc']}.", "",
        "## Evidence classification", "",
        f"- **VERIFIED:** {report['evidenceBoundary']['verified']}",
        f"- **PARTIALLY VERIFIED:** {report['evidenceBoundary']['partiallyVerified']}",
        f"- **UNKNOWN:** {report['evidenceBoundary']['unknown']}", "",
        "## Enforcement stack", "", "```mermaid", "flowchart LR",
        "  APP[Application route selection] --> FRAMEWORK[Camera2 framework]",
        "  PACKAGE[Package identity / grants / allowlists] -. policy .-> ENUM[CameraService enumeration]",
        "  FRAMEWORK --> ENUM", "  ENUM --> CHARACTERISTICS[CameraService characteristics]",
        "  CHARACTERISTICS --> CONNECT[CameraService connect]", "  CONNECT --> SESSION[Session and request configuration]",
        "  SESSION --> HAL[Provider / HAL]", "  HAL --> ISP[ISP / tuning firmware]",
        "  PACKAGE -. policy .-> CHARACTERISTICS", "  PACKAGE -. policy .-> CONNECT",
        "  SELINUX[SELinux / caller domain] -. policy .-> CHARACTERISTICS", "  SELINUX -. policy .-> CONNECT",
        "```", "", "## Feature-to-boundary diagram", "", "```mermaid", "flowchart LR",
    ]
    labels = {item["id"]: item["label"] for item in report["layers"]}
    nodes: set[str] = set()
    hard_edges: set[tuple[str, str]] = set()
    for feature in report["features"]:
        layer = feature["firstBoundary"]["layer"]
        key, label = ("NONE", "No rejection observed") if layer is None else (layer, labels[layer])
        boundary_node = node_id("boundary_" + key)
        if boundary_node not in nodes:
            lines.append(f'  {boundary_node}["{label}"]')
            nodes.add(boundary_node)
        lines.append(f'  {node_id(feature["id"])}["{feature["label"]}<br/>{feature["accessClass"]}"] --> {boundary_node}')
        hard = feature.get("hardRejection")
        if hard:
            hard_node = node_id("boundary_" + hard["layer"])
            if hard_node not in nodes:
                lines.append(f'  {hard_node}["{labels[hard["layer"]]}"]')
                nodes.add(hard_node)
            edge = (boundary_node, hard_node)
            if edge not in hard_edges:
                lines.append(f"  {boundary_node} -->|hard rejection| {hard_node}")
                hard_edges.add(edge)
    lines.extend(["```", "", "## Access classes", "", "| Class | Definition |", "|---|---|"])
    for item in report["accessClasses"]:
        lines.append(f"| `{item['id']}` | {escape(item['definition'])} |")

    lines.extend(["", "## Per-feature enforcement map", "", "| Feature | Route | Access class | First observed difference | First hard rejection | Confidence | Replacement consequence | Evidence |", "|---|---|---|---|---|---|---|---|"])
    for feature in report["features"]:
        first = feature["firstBoundary"]
        hard = feature.get("hardRejection")
        hard_text = "—" if not hard else f"`{hard['layer']}` / `{hard['state']}`"
        confidence = first["classification"] if not hard or hard["classification"] == first["classification"] else f"{first['classification']}; hard rejection {hard['classification']}"
        links = ", ".join(f"[`{evidence_id}`](./{Path(report['evidence'][evidence_id]['path']).name})" for evidence_id in feature["evidence"])
        lines.append(f"| {escape(feature['label'])} | {escape(feature['route'])} | `{feature['accessClass']}` | `{first['layer'] or 'None observed'}` / `{first['state']}` | {hard_text} | `{confidence}` | {escape(feature['replacementConsequence'])} | {links} |")

    lines.extend(["", "## Deployment separation", "", "| Deployment | Allowed | Conditional | Must not be claimed | Consequence |", "|---|---|---|---|---|"])
    for item in report["deploymentClasses"]:
        fmt = lambda values: ", ".join(f"`{value}`" for value in values) or "—"
        lines.append(f"| {escape(item['label'])} | {fmt(item['allowedAccessClasses'])} | {fmt(item['conditionalAccessClasses'])} | {fmt(item['prohibitedClaims'])} | {escape(item['consequence'])} |")

    lines.extend(["", "## Current decisive boundaries", "",
        "- IDs `2`, `3`, `4`, and `5` first differ at ordinary CameraService enumeration and are then hard-rejected at characteristics as system-only devices.",
        "- The existing ordinary hidden-ID probe does not independently reach CameraService connect; it stops during characteristics preflight.",
        "- The stock Galaga manual table directly selects IDs `2`, `0`, and `3`, but the stock package authorization mechanism remains unresolved.",
        "- Package identity, grants, roles, and allowlists are distinct from SELinux; no target SELinux denial has yet been established as the first rejection.",
        "- No ordinary-callable vendor/session route, provider/HAL sensor-selection contract, or ISP tuning contract has been causally reproduced.",
        "", "## Unresolved work", ""])
    by_id = {item["id"]: item for item in report["features"]}
    for feature_id in report["summary"]["unresolvedFeatureIds"]:
        lines.append(f"- `{feature_id}`: {by_id[feature_id]['firstBoundary']['reason']}")
    lines.extend(["", "## Generation", "", "This document is generated from `research/boundaries/galaga-camera-privilege-boundaries.json`:", "", "```bash", "python3 tools/research/build-camera-privilege-boundary.py \\", "  --markdown docs/research/CAMERA_PRIVILEGE_BOUNDARY.md \\", "  --json /private/galaga-camera-privilege-boundary.json", "```", ""])
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Build the Galaga camera privilege-boundary report")
    value.add_argument("model", nargs="?", default=str(default_model_path()))
    value.add_argument("--json", dest="json_path")
    value.add_argument("--markdown", dest="markdown_path")
    value.add_argument("--check-markdown", dest="check_markdown")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = build_report(load_model(args.model))
    except BoundaryModelError as error:
        print(f"boundary model error: {error}", file=sys.stderr)
        return 2
    rendered_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    rendered_markdown = render_markdown(report)
    if args.check_markdown:
        try:
            existing = Path(args.check_markdown).read_text(encoding="utf-8")
        except OSError as error:
            print(f"cannot read Markdown check file: {error}", file=sys.stderr)
            return 2
        if existing != rendered_markdown:
            print(f"generated Markdown differs from {args.check_markdown}", file=sys.stderr)
            return 1
    for path, content in ((args.json_path, rendered_json), (args.markdown_path, rendered_markdown)):
        if path:
            output = Path(path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
    if not args.json_path and not args.markdown_path and not args.check_markdown:
        sys.stdout.write(rendered_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
