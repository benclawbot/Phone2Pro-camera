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
VALID_MODES = {"QUICK", "AUTO", "MAX_DETAIL"}
VALID_COMPUTE = {"LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH", "VARIABLE_HIGH"}
VALID_MEMORY = {"LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "VERY_HIGH", "VARIABLE_HIGH"}
VALID_IMPLEMENTATION_LICENSES = {"MIT", "Apache-2.0"}
REQUIRED_METHOD_IDS = {
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
REQUIRED_CATEGORIES = {
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
REQUIRED_BENCHMARK_IDS = {
    "benchmark-hdrplus-burst",
    "benchmark-burstsr",
    "benchmark-sidd",
    "benchmark-dnd",
    "benchmark-galaga-controlled",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_text(item) for item in value)
        and len(value) == len(set(value))
    )


def _https_url(value: Any) -> bool:
    if not _text(value):
        return False
    parsed = urlparse(str(value))
    return parsed.scheme == "https" and bool(parsed.netloc)


def load_index(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / INDEX_PATH).read_text(encoding="utf-8"))


def validate(
    root: pathlib.Path,
    index: dict[str, Any] | None = None,
    document: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if index is None:
        try:
            index = load_index(root)
        except (OSError, json.JSONDecodeError) as error:
            return [f"cannot load {INDEX_PATH}: {error}"]
    if document is None:
        try:
            document = (root / DOCUMENT_PATH).read_text(encoding="utf-8")
        except OSError as error:
            return [f"cannot load {DOCUMENT_PATH}: {error}"]

    if index.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    version = index.get("indexVersion")
    if not _text(version):
        errors.append("indexVersion must be non-empty")
    elif f"**Index version:** {version}" not in document:
        errors.append("document index version does not match")

    scope = index.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        if scope.get("issue") != 81:
            errors.append("scope.issue must be 81")
        for field in ("objective", "engineeringGuide", "alignmentContract", "resourceContract", "renderingContract", "interpretationRule"):
            if not _text(scope.get(field)):
                errors.append(f"scope.{field} must be non-empty")
        for field in ("engineeringGuide", "alignmentContract", "resourceContract", "renderingContract"):
            path = scope.get(field)
            if _text(path) and not (root / str(path)).is_file():
                errors.append(f"scope.{field} must reference an existing file")
        rule = str(scope.get("interpretationRule", "")).lower()
        for phrase in ("not code", "patent", "disabled"):
            if phrase not in rule:
                errors.append(f"scope.interpretationRule must mention {phrase}")

    papers = index.get("papers")
    paper_ids: set[str] = set()
    if not isinstance(papers, list) or len(papers) < 10:
        errors.append("papers must contain at least ten primary records")
        papers = []
    for position, paper in enumerate(papers):
        prefix = f"papers[{position}]"
        if not isinstance(paper, dict):
            errors.append(f"{prefix} must be an object")
            continue
        paper_id = paper.get("id")
        if not _text(paper_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif paper_id in paper_ids:
            errors.append(f"duplicate paper id {paper_id}")
        else:
            paper_ids.add(str(paper_id))
        for field in ("title", "authors", "venue", "primaryContribution"):
            if not _text(paper.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        year = paper.get("year")
        if not isinstance(year, int) or year < 1900 or year > 2100:
            errors.append(f"{prefix}.year is invalid")
        if not _https_url(paper.get("url")):
            errors.append(f"{prefix}.url must be an https URL")

    implementations = index.get("implementations")
    implementation_ids: set[str] = set()
    if not isinstance(implementations, list) or len(implementations) < 3:
        errors.append("implementations must contain at least three pinned references")
        implementations = []
    for position, implementation in enumerate(implementations):
        prefix = f"implementations[{position}]"
        if not isinstance(implementation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        implementation_id = implementation.get("id")
        if not _text(implementation_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif implementation_id in implementation_ids:
            errors.append(f"duplicate implementation id {implementation_id}")
        else:
            implementation_ids.add(str(implementation_id))
        for field in ("repository", "status", "notes"):
            if not _text(implementation.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        revision = implementation.get("revision")
        if not isinstance(revision, str) or not SHA40.fullmatch(revision):
            errors.append(f"{prefix}.revision must be a lowercase 40-character commit")
        if not _https_url(implementation.get("url")):
            errors.append(f"{prefix}.url must be an https URL")
        elif isinstance(revision, str) and revision not in implementation["url"]:
            errors.append(f"{prefix}.url must include its pinned commit")
        if implementation.get("license") not in VALID_IMPLEMENTATION_LICENSES:
            errors.append(f"{prefix}.license must be a reviewed permissive identifier")

    benchmarks = index.get("benchmarks")
    benchmark_ids: set[str] = set()
    if not isinstance(benchmarks, list) or len(benchmarks) != len(REQUIRED_BENCHMARK_IDS):
        errors.append("benchmarks must contain exactly the five required records")
        benchmarks = []
    for position, benchmark in enumerate(benchmarks):
        prefix = f"benchmarks[{position}]"
        if not isinstance(benchmark, dict):
            errors.append(f"{prefix} must be an object")
            continue
        benchmark_id = benchmark.get("id")
        if not _text(benchmark_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif benchmark_id in benchmark_ids:
            errors.append(f"duplicate benchmark id {benchmark_id}")
        else:
            benchmark_ids.add(str(benchmark_id))
            if f"`{benchmark_id}`" not in document:
                errors.append(f"document is missing benchmark id {benchmark_id}")
        paper_links = benchmark.get("paperIds")
        if not _text_list(paper_links, allow_empty=True):
            errors.append(f"{prefix}.paperIds must be a unique text list")
        else:
            unknown = set(paper_links) - paper_ids
            if unknown:
                errors.append(f"{prefix}.paperIds references unknown papers: {sorted(unknown)}")
        if not _text_list(benchmark.get("tasks")):
            errors.append(f"{prefix}.tasks must be a non-empty text list")
        license_status = benchmark.get("licenseStatus")
        if not _text(license_status) or "UNKNOWN" in str(license_status):
            errors.append(f"{prefix}.licenseStatus must be explicit")
        if not _text_list(benchmark.get("limitations")):
            errors.append(f"{prefix}.limitations must be a non-empty text list")

    missing_benchmarks = REQUIRED_BENCHMARK_IDS - benchmark_ids
    if missing_benchmarks:
        errors.append(f"missing required benchmark ids: {sorted(missing_benchmarks)}")

    methods = index.get("methods")
    method_ids: set[str] = set()
    categories: set[str] = set()
    modes_seen: set[str] = set()
    if not isinstance(methods, list) or len(methods) != len(REQUIRED_METHOD_IDS):
        errors.append("methods must contain exactly the ten required methods")
        methods = []
    for position, method in enumerate(methods):
        prefix = f"methods[{position}]"
        if not isinstance(method, dict):
            errors.append(f"{prefix} must be an object")
            continue
        method_id = method.get("id")
        if not _text(method_id):
            errors.append(f"{prefix}.id must be non-empty")
            continue
        method_id = str(method_id)
        if method_id in method_ids:
            errors.append(f"duplicate method id {method_id}")
        method_ids.add(method_id)
        if f"`{method_id}`" not in document:
            errors.append(f"document is missing method id {method_id}")
        category = method.get("category")
        if not _text(category):
            errors.append(f"{prefix}.category must be non-empty")
        else:
            categories.add(str(category))
        paper_links = method.get("paperIds")
        if not _text_list(paper_links):
            errors.append(f"{prefix}.paperIds must be a non-empty unique list")
        else:
            unknown = set(paper_links) - paper_ids
            if unknown:
                errors.append(f"{prefix}.paperIds references unknown papers: {sorted(unknown)}")
        implementation_links = method.get("implementationIds")
        if not _text_list(implementation_links, allow_empty=True):
            errors.append(f"{prefix}.implementationIds must be a unique text list")
        else:
            unknown = set(implementation_links) - implementation_ids
            if unknown:
                errors.append(f"{prefix}.implementationIds references unknown implementations: {sorted(unknown)}")
        for field in ("assumptions", "failureArtifacts", "mobileRisks", "benchmarkIds"):
            if not _text_list(method.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty unique text list")
        benchmark_links = method.get("benchmarkIds")
        if isinstance(benchmark_links, list):
            unknown = set(benchmark_links) - benchmark_ids
            if unknown:
                errors.append(f"{prefix}.benchmarkIds references unknown benchmarks: {sorted(unknown)}")
            if "benchmark-galaga-controlled" not in benchmark_links:
                errors.append(f"{prefix} must include benchmark-galaga-controlled")
        if method.get("computeClass") not in VALID_COMPUTE:
            errors.append(f"{prefix}.computeClass is invalid")
        if method.get("memoryClass") not in VALID_MEMORY:
            errors.append(f"{prefix}.memoryClass is invalid")
        for field in ("licensing", "decision"):
            if not _text(method.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        mode_assignments = method.get("modeAssignments")
        if not _text_list(mode_assignments) or not set(mode_assignments) <= VALID_MODES:
            errors.append(f"{prefix}.modeAssignments is invalid")
        else:
            modes_seen.update(mode_assignments)
        if method_id in {"method-kpn-burst-denoising", "method-handheld-raw-mfsr"} and "QUICK" in set(mode_assignments or []):
            errors.append(f"{prefix} high-cost learned/super-resolution method cannot be assigned to QUICK")

    missing_methods = REQUIRED_METHOD_IDS - method_ids
    if missing_methods:
        errors.append(f"missing required method ids: {sorted(missing_methods)}")
    missing_categories = REQUIRED_CATEGORIES - categories
    if missing_categories:
        errors.append(f"missing required categories: {sorted(missing_categories)}")
    if modes_seen != VALID_MODES:
        errors.append("method assignments must cover QUICK, AUTO and MAX_DETAIL")

    mode_requirements = index.get("modeRequirements")
    if not isinstance(mode_requirements, dict) or set(mode_requirements) != VALID_MODES:
        errors.append("modeRequirements must define QUICK, AUTO and MAX_DETAIL exactly once")
    elif any(not _text_list(requirements) or len(requirements) < 3 for requirements in mode_requirements.values()):
        errors.append("every mode must contain at least three requirements")

    if not _text_list(index.get("acceptanceMetrics")) or len(index.get("acceptanceMetrics", [])) < 6:
        errors.append("acceptanceMetrics must contain at least six measurements")

    non_claims = index.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 5 or not all(_text(item) for item in non_claims):
        errors.append("nonClaims must contain at least five explicit limitations")
    else:
        for position, statement in enumerate(non_claims):
            if not any(term in statement.lower() for term in ("does not", "not a")):
                errors.append(f"nonClaims[{position}] must explicitly limit interpretation")

    maintenance = index.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")
        if maintenance.get("validationTool") != "tools/validate-computational-photography-literature.py":
            errors.append("maintenance.validationTool is incorrect")
        if not _text_list(maintenance.get("updateTriggers")):
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
