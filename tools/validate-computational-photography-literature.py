#!/usr/bin/env python3
"""Validate the computational-photography literature and method register."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any
from urllib.parse import urlparse

INDEX_PATH = pathlib.Path("research/computational-photography-literature.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/COMPUTATIONAL_PHOTOGRAPHY_LITERATURE_REVIEW.md")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
MODES = {"QUICK", "AUTO", "MAX_DETAIL"}
COMPUTE = {"LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH", "VARIABLE_HIGH"}
MEMORY = {"LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH", "VARIABLE_HIGH"}
LICENSES = {"MIT", "Apache-2.0"}
METHOD_IDS = {
    "method-hdrplus-constant-exposure-raw-burst",
    "method-motion-metered-low-light-burst",
    "method-fft-tile-alignment",
    "method-robust-wiener-burst-merge",
    "method-handheld-raw-mfsr",
    "method-kpn-burst-denoising",
    "method-gyro-aided-alignment-seed",
    "method-exposure-fusion",
    "method-reinhard-global-tone-map",
    "method-local-laplacian-detail-tone",
}
CATEGORIES = {
    "BURST_HDR",
    "CAPTURE_POLICY",
    "ALIGNMENT",
    "DENOISING_MERGE",
    "SUPER_RESOLUTION",
    "LEARNED_DENOISING",
    "MOTION_HANDLING",
    "HDR_TONE_FUSION",
    "TONE_MAPPING",
    "SHARPENING_TONE_MAPPING",
}
BENCHMARK_IDS = {
    "benchmark-hdrplus-burst",
    "benchmark-burstsr",
    "benchmark-sidd",
    "benchmark-dnd",
    "benchmark-galaga-controlled",
}


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def text_list(value: Any, *, empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (empty or bool(value))
        and all(text(item) for item in value)
        and len(value) == len(set(value))
    )


def https(value: Any) -> bool:
    if not text(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def load_index(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / INDEX_PATH).read_text(encoding="utf-8"))


def validate(root: pathlib.Path, index: dict[str, Any] | None = None, document: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        index = index if index is not None else load_index(root)
        document = document if document is not None else (root / DOCUMENT_PATH).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot load literature review: {error}"]

    if index.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    version = index.get("indexVersion")
    if not text(version):
        errors.append("indexVersion must be non-empty")
    elif f"**Index version:** {version}" not in document:
        errors.append("document index version does not match")

    scope = index.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        if scope.get("issue") != 81:
            errors.append("scope.issue must be 81")
        path_fields = ("engineeringGuide", "alignmentContract", "resourceContract", "renderingContract")
        for field in ("objective", *path_fields, "interpretationRule"):
            if not text(scope.get(field)):
                errors.append(f"scope.{field} must be non-empty")
        for field in path_fields:
            if text(scope.get(field)) and not (root / scope[field]).is_file():
                errors.append(f"scope.{field} must reference an existing file")
        rule = str(scope.get("interpretationRule", "")).lower()
        for phrase in ("not code", "patent", "disabled"):
            if phrase not in rule:
                errors.append(f"scope.interpretationRule must mention {phrase}")

    paper_ids: set[str] = set()
    papers = index.get("papers")
    if not isinstance(papers, list) or len(papers) < 10:
        errors.append("papers must contain at least ten primary records")
        papers = []
    for i, paper in enumerate(papers):
        prefix = f"papers[{i}]"
        if not isinstance(paper, dict):
            errors.append(f"{prefix} must be an object")
            continue
        pid = paper.get("id")
        if not text(pid):
            errors.append(f"{prefix}.id must be non-empty")
        elif pid in paper_ids:
            errors.append(f"duplicate paper id {pid}")
        else:
            paper_ids.add(pid)
        for field in ("title", "authors", "venue", "primaryContribution"):
            if not text(paper.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if not isinstance(paper.get("year"), int) or not 1900 <= paper["year"] <= 2100:
            errors.append(f"{prefix}.year is invalid")
        if not https(paper.get("url")):
            errors.append(f"{prefix}.url must be an https URL")

    implementation_ids: set[str] = set()
    implementations = index.get("implementations")
    if not isinstance(implementations, list) or len(implementations) < 3:
        errors.append("implementations must contain at least three pinned references")
        implementations = []
    for i, item in enumerate(implementations):
        prefix = f"implementations[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        iid = item.get("id")
        if not text(iid):
            errors.append(f"{prefix}.id must be non-empty")
        elif iid in implementation_ids:
            errors.append(f"duplicate implementation id {iid}")
        else:
            implementation_ids.add(iid)
        for field in ("repository", "status", "notes"):
            if not text(item.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        revision = item.get("revision")
        if not isinstance(revision, str) or not SHA40.fullmatch(revision):
            errors.append(f"{prefix}.revision must be a lowercase 40-character commit")
        if not https(item.get("url")):
            errors.append(f"{prefix}.url must be an https URL")
        elif isinstance(revision, str) and revision not in item["url"]:
            errors.append(f"{prefix}.url must include its pinned commit")
        if item.get("license") not in LICENSES:
            errors.append(f"{prefix}.license must be a reviewed permissive identifier")

    benchmark_ids: set[str] = set()
    benchmarks = index.get("benchmarks")
    if not isinstance(benchmarks, list) or len(benchmarks) != len(BENCHMARK_IDS):
        errors.append("benchmarks must contain exactly the five required records")
        benchmarks = []
    for i, item in enumerate(benchmarks):
        prefix = f"benchmarks[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        bid = item.get("id")
        if not text(bid):
            errors.append(f"{prefix}.id must be non-empty")
        elif bid in benchmark_ids:
            errors.append(f"duplicate benchmark id {bid}")
        else:
            benchmark_ids.add(bid)
            if f"`{bid}`" not in document:
                errors.append(f"document is missing benchmark id {bid}")
        links = item.get("paperIds")
        if not text_list(links, empty=True):
            errors.append(f"{prefix}.paperIds must be a unique text list")
        elif set(links) - paper_ids:
            errors.append(f"{prefix}.paperIds references unknown papers: {sorted(set(links) - paper_ids)}")
        if not text_list(item.get("tasks")):
            errors.append(f"{prefix}.tasks must be a non-empty text list")
        if not text(item.get("licenseStatus")) or "UNKNOWN" in item["licenseStatus"]:
            errors.append(f"{prefix}.licenseStatus must be explicit")
        if not text_list(item.get("limitations")):
            errors.append(f"{prefix}.limitations must be a non-empty text list")
    if BENCHMARK_IDS - benchmark_ids:
        errors.append(f"missing required benchmark ids: {sorted(BENCHMARK_IDS - benchmark_ids)}")

    method_ids: set[str] = set()
    categories: set[str] = set()
    modes_seen: set[str] = set()
    methods = index.get("methods")
    if not isinstance(methods, list) or len(methods) != len(METHOD_IDS):
        errors.append("methods must contain exactly the ten required methods")
        methods = []
    for i, method in enumerate(methods):
        prefix = f"methods[{i}]"
        if not isinstance(method, dict):
            errors.append(f"{prefix} must be an object")
            continue
        mid = method.get("id")
        if not text(mid):
            errors.append(f"{prefix}.id must be non-empty")
            continue
        if mid in method_ids:
            errors.append(f"duplicate method id {mid}")
        method_ids.add(mid)
        if f"`{mid}`" not in document:
            errors.append(f"document is missing method id {mid}")
        if text(method.get("category")):
            categories.add(method["category"])
        else:
            errors.append(f"{prefix}.category must be non-empty")
        paper_links = method.get("paperIds")
        if not text_list(paper_links):
            errors.append(f"{prefix}.paperIds must be a non-empty unique list")
        elif set(paper_links) - paper_ids:
            errors.append(f"{prefix}.paperIds references unknown papers: {sorted(set(paper_links) - paper_ids)}")
        impl_links = method.get("implementationIds")
        if not text_list(impl_links, empty=True):
            errors.append(f"{prefix}.implementationIds must be a unique text list")
        elif set(impl_links) - implementation_ids:
            errors.append(f"{prefix}.implementationIds references unknown implementations: {sorted(set(impl_links) - implementation_ids)}")
        for field in ("assumptions", "failureArtifacts", "mobileRisks", "benchmarkIds"):
            if not text_list(method.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty unique text list")
        benchmark_links = method.get("benchmarkIds", [])
        if set(benchmark_links) - benchmark_ids:
            errors.append(f"{prefix}.benchmarkIds references unknown benchmarks: {sorted(set(benchmark_links) - benchmark_ids)}")
        if "benchmark-galaga-controlled" not in benchmark_links:
            errors.append(f"{prefix} must include benchmark-galaga-controlled")
        if method.get("computeClass") not in COMPUTE:
            errors.append(f"{prefix}.computeClass is invalid")
        if method.get("memoryClass") not in MEMORY:
            errors.append(f"{prefix}.memoryClass is invalid")
        for field in ("licensing", "decision"):
            if not text(method.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        assignments = method.get("modeAssignments")
        if not text_list(assignments) or not set(assignments) <= MODES:
            errors.append(f"{prefix}.modeAssignments is invalid")
        else:
            modes_seen.update(assignments)
        if mid in {"method-kpn-burst-denoising", "method-handheld-raw-mfsr"} and "QUICK" in set(assignments or []):
            errors.append(f"{prefix} high-cost learned/super-resolution method cannot be assigned to QUICK")
    if METHOD_IDS - method_ids:
        errors.append(f"missing required method ids: {sorted(METHOD_IDS - method_ids)}")
    if CATEGORIES - categories:
        errors.append(f"missing required categories: {sorted(CATEGORIES - categories)}")
    if modes_seen != MODES:
        errors.append("method assignments must cover QUICK, AUTO and MAX_DETAIL")

    mode_requirements = index.get("modeRequirements")
    if not isinstance(mode_requirements, dict) or set(mode_requirements) != MODES:
        errors.append("modeRequirements must define QUICK, AUTO and MAX_DETAIL exactly once")
    elif any(not text_list(value) or len(value) < 3 for value in mode_requirements.values()):
        errors.append("every mode must contain at least three requirements")
    if not text_list(index.get("acceptanceMetrics")) or len(index.get("acceptanceMetrics", [])) < 6:
        errors.append("acceptanceMetrics must contain at least six measurements")

    non_claims = index.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 5 or not all(text(item) for item in non_claims):
        errors.append("nonClaims must contain at least five explicit limitations")
    else:
        for i, statement in enumerate(non_claims):
            if not any(term in statement.lower() for term in ("does not", "not a", "until")):
                errors.append(f"nonClaims[{i}] must explicitly limit interpretation")

    maintenance = index.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")
        if maintenance.get("validationTool") != "tools/validate-computational-photography-literature.py":
            errors.append("maintenance.validationTool is incorrect")
        if not text_list(maintenance.get("updateTriggers")):
            errors.append("maintenance.updateTriggers must be a non-empty text list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Computational-photography literature register is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
