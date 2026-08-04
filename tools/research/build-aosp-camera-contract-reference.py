#!/usr/bin/env python3
"""Validate and render the Android 16 camera-contract comparison catalog."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import sys
from typing import Any

COMPARISON_STATES = {"CONFORMING", "NOT_ADVERTISED", "OEM_EXTENSION", "DEVIATION", "UNKNOWN"}
CLASSIFICATIONS = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}


class ContractCatalogError(ValueError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_catalog_path() -> Path:
    return repository_root() / "research" / "contracts" / "android16-camera-contracts.json"


def load_catalog(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractCatalogError(f"cannot load camera contract catalog: {error}") from error
    if not isinstance(value, dict):
        raise ContractCatalogError("catalog root must be an object")
    return value


def require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractCatalogError(f"{name} must be non-empty text")
    return value.strip()


def require_unique(items: Any, name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        raise ContractCatalogError(f"{name} must be a non-empty list")
    output: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ContractCatalogError(f"{name}[{index}] must be an object")
        item_id = require_text(item.get("id"), f"{name}[{index}].id")
        if item_id in output:
            raise ContractCatalogError(f"duplicate {name} id: {item_id}")
        output[item_id] = item
    return output


def validate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    if catalog.get("schemaVersion") != 1:
        raise ContractCatalogError("schemaVersion must be 1")
    platform = catalog.get("referencePlatform")
    target = catalog.get("target")
    if not isinstance(platform, dict) or not isinstance(target, dict):
        raise ContractCatalogError("referencePlatform and target must be objects")
    for field in ("androidRelease", "branch", "retrievedAt"):
        require_text(platform.get(field), f"referencePlatform.{field}")
    if platform.get("apiLevel") != 36:
        raise ContractCatalogError("Android 16 reference apiLevel must be 36")
    for field in ("model", "codename", "androidVersion", "soc"):
        require_text(target.get(field), f"target.{field}")

    states = catalog.get("comparisonStates")
    if not isinstance(states, dict) or set(states) != COMPARISON_STATES:
        raise ContractCatalogError(f"comparisonStates must be exactly {sorted(COMPARISON_STATES)}")
    for state, definition in states.items():
        require_text(definition, f"comparisonStates.{state}")

    sources = catalog.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ContractCatalogError("sources must be a non-empty object")
    pinned_source_ids = {
        "frameworks-base-android16",
        "frameworks-av-android16",
        "system-media-android16",
        "hardware-interfaces-android16",
    }
    for source_id, source in sources.items():
        if not isinstance(source, dict):
            raise ContractCatalogError(f"sources.{source_id} must be an object")
        for field in ("title", "publisher", "revision", "sourceType", "authority"):
            require_text(source.get(field), f"sources.{source_id}.{field}")
        if not source.get("url") and not source.get("path"):
            raise ContractCatalogError(f"sources.{source_id} must contain url or path")
        if source_id in pinned_source_ids:
            revision = require_text(source.get("revision"), f"sources.{source_id}.revision")
            if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
                raise ContractCatalogError(f"sources.{source_id} must use a 40-character commit hash")

    contracts = require_unique(catalog.get("contracts"), "contracts")
    for contract_id, contract in contracts.items():
        for field in ("title", "contract"):
            require_text(contract.get(field), f"contracts.{contract_id}.{field}")
        introduced = contract.get("introduced")
        if not isinstance(introduced, dict) or not introduced:
            raise ContractCatalogError(f"contracts.{contract_id}.introduced must be an object")
        require_text(introduced.get("android"), f"contracts.{contract_id}.introduced.android")
        anchors = contract.get("android16Anchors")
        if not isinstance(anchors, list) or not anchors:
            raise ContractCatalogError(f"contracts.{contract_id}.android16Anchors must be non-empty")
        for anchor_index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict):
                raise ContractCatalogError(f"contracts.{contract_id}.android16Anchors[{anchor_index}] must be an object")
            source_id = require_text(anchor.get("source"), f"contracts.{contract_id}.android16Anchors[{anchor_index}].source")
            if source_id not in sources:
                raise ContractCatalogError(f"contracts.{contract_id} references unknown source {source_id}")
            if not any(isinstance(anchor.get(field), list) and anchor.get(field) for field in ("symbols", "metadata")):
                raise ContractCatalogError(f"contracts.{contract_id} anchor {anchor_index} needs symbols or metadata")
        differences = contract.get("versionDifferences")
        if not isinstance(differences, list) or not differences:
            raise ContractCatalogError(f"contracts.{contract_id}.versionDifferences must be non-empty")
        for difference_index, difference in enumerate(differences):
            require_text(difference, f"contracts.{contract_id}.versionDifferences[{difference_index}]")
        comparison = contract.get("targetComparison")
        if not isinstance(comparison, dict):
            raise ContractCatalogError(f"contracts.{contract_id}.targetComparison must be an object")
        state = require_text(comparison.get("state"), f"contracts.{contract_id}.targetComparison.state")
        classification = require_text(comparison.get("classification"), f"contracts.{contract_id}.targetComparison.classification")
        if state not in COMPARISON_STATES:
            raise ContractCatalogError(f"contracts.{contract_id} has invalid comparison state {state}")
        if classification not in CLASSIFICATIONS:
            raise ContractCatalogError(f"contracts.{contract_id} has invalid classification {classification}")
        require_text(comparison.get("observation"), f"contracts.{contract_id}.targetComparison.observation")
        evidence = comparison.get("evidence")
        if not isinstance(evidence, list) or not evidence or set(evidence) - set(sources):
            raise ContractCatalogError(f"contracts.{contract_id}.targetComparison.evidence is invalid")

    required_contracts = {
        "camera2-baseline",
        "logical-multi-camera",
        "hidden-physical-id-query",
        "physical-stream-controls",
        "active-physical-id",
        "system-cameras",
        "zoom-ratio",
        "session-parameters",
        "vendor-tags",
        "camera-extensions",
        "camera-service-stage-separation",
        "camera-hal-interface-generation",
    }
    if set(contracts) != required_contracts:
        raise ContractCatalogError(f"contracts must be exactly {sorted(required_contracts)}")
    return {"sources": sources, "contracts": contracts}


def build_report(catalog: dict[str, Any]) -> dict[str, Any]:
    validated = validate_catalog(catalog)
    contracts = list(validated["contracts"].values())
    by_state = collections.Counter(item["targetComparison"]["state"] for item in contracts)
    by_classification = collections.Counter(item["targetComparison"]["classification"] for item in contracts)
    deviations = [item["id"] for item in contracts if item["targetComparison"]["state"] == "DEVIATION"]
    unresolved = [item["id"] for item in contracts if item["targetComparison"]["state"] == "UNKNOWN"]
    return {
        "schemaVersion": 1,
        "referencePlatform": catalog["referencePlatform"],
        "target": catalog["target"],
        "comparisonStates": catalog["comparisonStates"],
        "sources": catalog["sources"],
        "contracts": contracts,
        "summary": {
            "contractCount": len(contracts),
            "byComparisonState": dict(sorted(by_state.items())),
            "byClassification": dict(sorted(by_classification.items())),
            "confirmedDeviationIds": deviations,
            "unresolvedContractIds": unresolved,
        },
        "evidenceBoundary": {
            "verified": "Pinned Android 16 source symbols, official release history, and target observations are indexed without treating optional capability absence as a deviation.",
            "partiallyVerified": "A standards match identifies expected behavior but does not prove the OEM binaries are byte-identical to AOSP.",
            "unknown": "Unobserved target interfaces, route-specific vendor values, and lower-layer behavior remain unknown until measured on matching firmware."
        }
    }


def escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def source_link(source_id: str, source: dict[str, Any]) -> str:
    target = source.get("url")
    if not target:
        path = Path(source["path"])
        if path.parts[:2] == ("docs", "research"):
            target = "./" + path.name
        else:
            target = "../../" + path.as_posix()
    return f"[`{source_id}`]({target})"


def anchor_text(anchor: dict[str, Any], sources: dict[str, Any]) -> str:
    names = list(anchor.get("symbols", [])) + list(anchor.get("metadata", []))
    location = anchor.get("path")
    label = ", ".join(f"`{name}`" for name in names)
    if location:
        label = f"`{location}`: {label}"
    return f"{source_link(anchor['source'], sources[anchor['source']])} — {label}"


def render_markdown(report: dict[str, Any]) -> str:
    platform = report["referencePlatform"]
    target = report["target"]
    sources = report["sources"]
    lines = [
        "# Android 16 camera contract reference", "",
        "Status: pinned AOSP/official Android cross-reference for CAM-091.", "",
        f"Reference: **{platform['androidRelease']} / API {platform['apiLevel']}**, branch `{platform['branch']}`.",
        f"Target: **{target['model']}** (`{target['codename']}`), Android {target['androidVersion']}, {target['soc']}.", "",
        "## Evidence classification", "",
        f"- **VERIFIED:** {report['evidenceBoundary']['verified']}",
        f"- **PARTIALLY VERIFIED:** {report['evidenceBoundary']['partiallyVerified']}",
        f"- **UNKNOWN:** {report['evidenceBoundary']['unknown']}", "",
        "## Target comparison summary", "",
        "| State | Count | Meaning |", "|---|---:|---|"
    ]
    for state in ("CONFORMING", "NOT_ADVERTISED", "OEM_EXTENSION", "DEVIATION", "UNKNOWN"):
        lines.append(f"| `{state}` | {report['summary']['byComparisonState'].get(state, 0)} | {escape(report['comparisonStates'][state])} |")
    if report["summary"]["confirmedDeviationIds"]:
        lines.extend(["", "Confirmed target deviations: " + ", ".join(f"`{item}`" for item in report["summary"]["confirmedDeviationIds"]) + "."])
    else:
        lines.extend(["", "**No target deviation is currently confirmed.** Optional capability absence and OEM vendor tags are classified separately."])

    lines.extend(["", "## Contract index", "", "| Contract | Introduced | Android 16 anchors | Target state | Confidence | Target observation |", "|---|---|---|---|---|---|"])
    for contract in report["contracts"]:
        introduced = contract["introduced"]
        introduced_text = f"Android {introduced['android']}"
        if introduced.get("apiLevel") is not None:
            introduced_text += f" / API {introduced['apiLevel']}"
        if introduced.get("halDeviceVersion"):
            introduced_text += f" / HAL {introduced['halDeviceVersion']}"
        if introduced.get("interface"):
            introduced_text += f" / {introduced['interface']}"
        anchors = "<br>".join(anchor_text(anchor, sources) for anchor in contract["android16Anchors"])
        comparison = contract["targetComparison"]
        lines.append(f"| {escape(contract['title'])} | {escape(introduced_text)} | {anchors} | `{comparison['state']}` | `{comparison['classification']}` | {escape(comparison['observation'])} |")

    lines.extend(["", "## Version differences and target consequences", ""])
    for contract in report["contracts"]:
        comparison = contract["targetComparison"]
        lines.extend([f"### {contract['title']}", "", f"**Standard contract:** {contract['contract']}", "", "Version history:"])
        lines.extend(f"- {item}" for item in contract["versionDifferences"])
        lines.extend(["", f"**Galaga comparison — `{comparison['state']}` / `{comparison['classification']}`:** {comparison['observation']}", "", "Target evidence:"])
        for evidence_id in comparison["evidence"]:
            lines.append(f"- {source_link(evidence_id, sources[evidence_id])}")
        lines.append("")

    lines.extend(["## Pinned Android 16 source revisions", "", "| Source | Revision | Scope |", "|---|---|---|"])
    for source_id in ("frameworks-base-android16", "frameworks-av-android16", "system-media-android16", "hardware-interfaces-android16"):
        source = sources[source_id]
        lines.append(f"| {source_link(source_id, source)} | `{source['revision']}` | {escape(source['title'])} |")

    lines.extend(["", "## Unresolved target checks", ""])
    by_id = {item["id"]: item for item in report["contracts"]}
    for contract_id in report["summary"]["unresolvedContractIds"]:
        comparison = by_id[contract_id]["targetComparison"]
        lines.append(f"- `{contract_id}`: {comparison['observation']}")
    lines.extend(["", "## Generation", "", "This document is generated from `research/contracts/android16-camera-contracts.json`:", "", "```bash", "python3 tools/research/build-aosp-camera-contract-reference.py \\", "  --markdown docs/research/AOSP_CAMERA_CONTRACT_REFERENCE.md \\", "  --json /private/android16-camera-contract-reference.json", "```", ""])
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Build the Android 16 camera contract reference")
    value.add_argument("catalog", nargs="?", default=str(default_catalog_path()))
    value.add_argument("--json", dest="json_path")
    value.add_argument("--markdown", dest="markdown_path")
    value.add_argument("--check-markdown", dest="check_markdown")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = build_report(load_catalog(args.catalog))
    except ContractCatalogError as error:
        print(f"camera contract catalog error: {error}", file=sys.stderr)
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
