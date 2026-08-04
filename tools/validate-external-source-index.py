#!/usr/bin/env python3
"""Validate the federated, revision-pinned external-source catalogue."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any
from urllib.parse import urlparse

INDEX_PATH = pathlib.Path("research/external-source-index.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/EXTERNAL_SOURCE_INDEX.md")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
YEAR = re.compile(r"^(19|20)\d{2}$")
REQUIRED_CLASSIFICATIONS = {
    "OFFICIAL_VENDOR",
    "OFFICIAL_SOURCE_CODE",
    "PLATFORM_SOURCE_CODE",
    "REFERENCE_IMPLEMENTATION",
    "ACADEMIC_PRIMARY",
    "COMMUNITY_REPORT",
    "COMMUNITY_ARCHIVE",
    "DATASET_REFERENCE",
}
COMMUNITY_CONFIDENCE = {
    "OBSERVATIONAL_CORROBORATED",
    "OBSERVATIONAL_SINGLE",
    "SECOND_HAND_LEAD",
    "METADATA_VERIFIED",
}
NOTE_REQUIRED_FRESHNESS = {
    "EXACT_BUILD_UNVERIFIED_ARTIFACT",
    "BUILD_MISMATCH",
    "PLATFORM_MISMATCH",
    "HISTORICAL_METHOD",
    "DATE_SCOPED_OBSERVATION",
    "DATASET_TERMS_PENDING",
}
REQUIRED_FACETS = {
    "classification",
    "publisher",
    "license",
    "targetRelevance",
    "confidence",
    "freshness",
    "buildScope",
    "sourceRegistry",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_text_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(_text(item) for item in value)
        and len(value) == len(set(value))
    )


def _https(value: Any) -> bool:
    if not _text(value):
        return False
    parsed = urlparse(str(value))
    return parsed.scheme == "https" and bool(parsed.netloc)


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_index(root: pathlib.Path) -> dict[str, Any]:
    return _load_json(root / INDEX_PATH)


def _registry_ids(registry: dict[str, Any], selector: str) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    records = registry.get(selector)
    if not isinstance(records, list):
        return set(), [f"selector {selector} must resolve to a list"]
    ids: set[str] = set()
    for position, record in enumerate(records):
        if not isinstance(record, dict) or not _text(record.get("id")):
            errors.append(f"selector {selector}[{position}] must contain a non-empty id")
            continue
        record_id = str(record["id"])
        if record_id in ids:
            errors.append(f"selector {selector} contains duplicate id {record_id}")
        ids.add(record_id)
    return ids, errors


def _validate_locator_against_registry(
    source: dict[str, Any], registry: dict[str, Any], selector: str
) -> list[str]:
    errors: list[str] = []
    records = registry.get(selector, [])
    record = next(
        (
            item
            for item in records
            if isinstance(item, dict) and item.get("id") == source.get("sourceRecordId")
        ),
        None,
    )
    if record is None:
        return ["sourceRecordId is not present in its registry selector"]

    locator = str(source.get("locatorValue", ""))
    registry_path = source.get("sourceRegistry")

    if registry_path == "research/galaga-kernel-source-index.v1.json":
        if record.get("commit") != locator:
            errors.append("kernel repository locator must equal the registered commit")
    elif registry_path == "research/mediatek-public-camera-cross-reference.v1.json":
        revision = record.get("revision")
        if _text(revision) and revision != locator:
            errors.append("public-source locator must equal the registered revision")
    elif registry_path == "research/open-source-camera-architecture-review.v1.json":
        revision = record.get("revision")
        if _text(revision) and revision != locator:
            errors.append("architecture-source locator must equal the registered revision")
    elif registry_path == "research/computational-photography-literature.v1.json":
        if selector == "papers" and str(record.get("year")) != locator:
            errors.append("paper locator must equal the registered publication year")
        elif selector == "implementations" and record.get("revision") != locator:
            errors.append("implementation locator must equal the registered revision")
        elif selector == "benchmarks" and record.get("id") != locator:
            errors.append("benchmark locator must equal the registered benchmark id")
    elif registry_path == "research/community-camera-evidence.v1.json":
        report_date = record.get("firstReportedDate")
        if _text(report_date) and str(report_date) not in locator:
            errors.append("community locator must include the registered report date")
        build = record.get("buildContext")
        if isinstance(build, dict) and build.get("status") == "EXACT":
            exact_build = build.get("value")
            if _text(exact_build) and str(exact_build) not in locator:
                errors.append("community locator must include the registered exact build")
    elif registry_path == "research/galaga-firmware-acquisition.v1.json":
        record_id = record.get("id")
        if record_id == "nothing-support-release-note":
            expected = registry.get("device", {}).get("release")
            if expected != locator:
                errors.append("release-note locator must equal the target release")
        elif record_id == "oem-incremental-ota":
            for field in ("fromBuild", "toBuild"):
                value = record.get(field)
                if _text(value) and str(value) not in locator:
                    errors.append(f"OTA locator must include {field}")
        elif record_id == "nothing-archive-index" and record.get("releaseTag") != locator:
            errors.append("archive locator must equal the registered release tag")
    return errors


def validate(
    root: pathlib.Path,
    index: dict[str, Any] | None = None,
    document: str | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        index = index if index is not None else load_index(root)
        document = (
            document
            if document is not None
            else (root / DOCUMENT_PATH).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot load external source index: {error}"]

    if index.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    version = index.get("indexVersion")
    if not _text(version):
        errors.append("indexVersion must be non-empty")
    elif f"**Index version:** {version}" not in document:
        errors.append("document index version does not match")
    if index.get("issue") != 74:
        errors.append("issue must be 74")

    target = index.get("target")
    if not isinstance(target, dict):
        errors.append("target must be an object")
    else:
        if target.get("device") != "Galaga" or target.get("model") != "A001":
            errors.append("target must identify Galaga A001")
        if target.get("observedBuild") != "2606151653":
            errors.append("target.observedBuild must be 2606151653")
        evidence = target.get("fingerprintEvidence")
        if not _text(evidence) or not (root / str(evidence)).is_file():
            errors.append("target.fingerprintEvidence must reference an existing file")

    classifications = index.get("classificationVocabulary")
    confidences = index.get("confidenceVocabulary")
    freshness_values = index.get("freshnessVocabulary")
    if not _unique_text_list(classifications) or set(classifications) != REQUIRED_CLASSIFICATIONS:
        errors.append("classificationVocabulary must define every required class exactly once")
        classifications = []
    if not _unique_text_list(confidences):
        errors.append("confidenceVocabulary must be a unique non-empty list")
        confidences = []
    if not _unique_text_list(freshness_values):
        errors.append("freshnessVocabulary must be a unique non-empty list")
        freshness_values = []
    facets = index.get("searchFacets")
    if not _unique_text_list(facets) or set(facets) != REQUIRED_FACETS:
        errors.append("searchFacets must define every required facet exactly once")

    policy = index.get("claimReferencePolicy")
    if not isinstance(policy, dict):
        errors.append("claimReferencePolicy must be an object")
    else:
        if policy.get("requiredFields") != ["sourceId", "citationKey"]:
            errors.append("claimReferencePolicy.requiredFields is incorrect")
        if not _text(policy.get("rule")):
            errors.append("claimReferencePolicy.rule must be non-empty")
        if not _unique_text_list(policy.get("prohibited")) or len(policy.get("prohibited", [])) < 5:
            errors.append("claimReferencePolicy.prohibited must contain at least five unique rules")

    coverage = index.get("registryCoverage")
    coverage_keys: set[tuple[str, str]] = set()
    loaded_registries: dict[str, dict[str, Any]] = {}
    expected_by_coverage: dict[tuple[str, str], set[str]] = {}
    if not isinstance(coverage, list) or len(coverage) < 8:
        errors.append("registryCoverage must contain at least eight selectors")
        coverage = []
    for position, item in enumerate(coverage):
        prefix = f"registryCoverage[{position}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        path = item.get("path")
        selector = item.get("selector")
        excluded = item.get("excludedIds")
        if not _text(path) or not _text(selector):
            errors.append(f"{prefix}.path and selector must be non-empty")
            continue
        key = (str(path), str(selector))
        if key in coverage_keys:
            errors.append(f"duplicate registry coverage selector {key}")
        coverage_keys.add(key)
        if not isinstance(excluded, list) or not all(_text(value) for value in excluded):
            errors.append(f"{prefix}.excludedIds must be a text list")
            excluded = []
        registry_path = root / str(path)
        if not registry_path.is_file():
            errors.append(f"{prefix}.path does not exist")
            continue
        try:
            registry = loaded_registries.setdefault(str(path), _load_json(registry_path))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{prefix} cannot load registry: {error}")
            continue
        registry_ids, selector_errors = _registry_ids(registry, str(selector))
        errors.extend(f"{prefix}: {message}" for message in selector_errors)
        unknown_exclusions = set(excluded) - registry_ids
        if unknown_exclusions:
            errors.append(f"{prefix}.excludedIds references unknown ids: {sorted(unknown_exclusions)}")
        expected_by_coverage[key] = registry_ids - set(excluded)

    sources = index.get("sources")
    source_ids: set[str] = set()
    citation_keys: set[str] = set()
    actual_by_coverage: dict[tuple[str, str], set[str]] = {}
    classifications_seen: set[str] = set()
    if not isinstance(sources, list) or len(sources) < 40:
        errors.append("sources must contain at least forty normalized records")
        sources = []
    for position, source in enumerate(sources):
        prefix = f"sources[{position}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("sourceId")
        if not _text(source_id):
            errors.append(f"{prefix}.sourceId must be non-empty")
            continue
        source_id = str(source_id)
        if source_id in source_ids:
            errors.append(f"duplicate sourceId {source_id}")
        source_ids.add(source_id)
        if f"`{source_id}`" not in document:
            errors.append(f"document is missing sourceId {source_id}")

        classification = source.get("classification")
        if classification not in classifications:
            errors.append(f"{prefix}.classification is invalid")
        else:
            classifications_seen.add(str(classification))
        if source.get("confidence") not in confidences:
            errors.append(f"{prefix}.confidence is invalid")
        if source.get("freshness") not in freshness_values:
            errors.append(f"{prefix}.freshness is invalid")
        for field in (
            "title",
            "publisher",
            "locatorType",
            "locatorValue",
            "citationKey",
            "license",
            "scope",
            "targetRelevance",
            "buildScope",
            "sourceRegistry",
            "sourceSelector",
            "sourceRecordId",
        ):
            if not _text(source.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if not _https(source.get("url")):
            errors.append(f"{prefix}.url must be an https URL")

        citation_key = source.get("citationKey")
        if _text(citation_key):
            if not str(citation_key).startswith(f"{source_id}@"):
                errors.append(f"{prefix}.citationKey must start with sourceId@")
            if citation_key in citation_keys:
                errors.append(f"duplicate citationKey {citation_key}")
            citation_keys.add(str(citation_key))

        if not isinstance(source.get("implementationProof"), bool):
            errors.append(f"{prefix}.implementationProof must be boolean")
        if not isinstance(source.get("artifactVerified"), bool):
            errors.append(f"{prefix}.artifactVerified must be boolean")

        freshness = source.get("freshness")
        if freshness in NOTE_REQUIRED_FRESHNESS and not _text(source.get("mismatchNotes")):
            errors.append(f"{prefix}.mismatchNotes is required for {freshness}")
        if freshness in {"EXACT_BUILD_METADATA", "PLATFORM_BASELINE"} and source.get("mismatchNotes") is not None and not _text(source.get("mismatchNotes")):
            errors.append(f"{prefix}.mismatchNotes must be null or non-empty")

        locator_type = source.get("locatorType")
        locator_value = source.get("locatorValue")
        if locator_type == "GIT_COMMIT":
            if not isinstance(locator_value, str) or not SHA40.fullmatch(locator_value):
                errors.append(f"{prefix}.locatorValue must be a lowercase 40-character commit")
            elif locator_value not in str(source.get("url", "")):
                errors.append(f"{prefix}.url must contain the exact commit")
        if locator_type == "SOURCEFORGE_REVISION" and str(locator_value) not in str(source.get("url", "")):
            errors.append(f"{prefix}.url must contain the exact SourceForge revision")
        if locator_type == "PUBLICATION_YEAR" and not YEAR.fullmatch(str(locator_value)):
            errors.append(f"{prefix}.locatorValue must be a publication year")

        if classification == "ACADEMIC_PRIMARY":
            if source.get("implementationProof") is not False:
                errors.append(f"{prefix} academic source cannot be implementation proof")
            if locator_type != "PUBLICATION_YEAR":
                errors.append(f"{prefix} academic source must use PUBLICATION_YEAR")
        if classification in {"COMMUNITY_REPORT", "COMMUNITY_ARCHIVE"}:
            if source.get("implementationProof") is not False:
                errors.append(f"{prefix} community source cannot be implementation proof")
            if source.get("confidence") not in COMMUNITY_CONFIDENCE:
                errors.append(f"{prefix} community confidence is too strong")
        if classification == "DATASET_REFERENCE":
            if source.get("freshness") != "DATASET_TERMS_PENDING":
                errors.append(f"{prefix} dataset source must remain DATASET_TERMS_PENDING")
            if source.get("artifactVerified") is not False:
                errors.append(f"{prefix} dataset bytes cannot be marked verified")
        if freshness == "EXACT_BUILD_UNVERIFIED_ARTIFACT" and source.get("artifactVerified") is not False:
            errors.append(f"{prefix} exact-build unverified artifact cannot be marked verified")

        registry_path = str(source.get("sourceRegistry", ""))
        selector = str(source.get("sourceSelector", ""))
        coverage_key = (registry_path, selector)
        if coverage_key not in coverage_keys:
            errors.append(f"{prefix} references an undeclared registry selector")
        actual_by_coverage.setdefault(coverage_key, set()).add(str(source.get("sourceRecordId", "")))
        registry = loaded_registries.get(registry_path)
        if registry is not None:
            locator_errors = _validate_locator_against_registry(source, registry, selector)
            errors.extend(f"{prefix}: {message}" for message in locator_errors)

    if classifications_seen != REQUIRED_CLASSIFICATIONS:
        errors.append(f"source classifications are incomplete: {sorted(REQUIRED_CLASSIFICATIONS - classifications_seen)}")

    for key, expected_ids in expected_by_coverage.items():
        actual_ids = actual_by_coverage.get(key, set())
        missing = expected_ids - actual_ids
        extra = actual_ids - expected_ids
        if missing:
            errors.append(f"registry selector {key} is missing indexed ids: {sorted(missing)}")
        if extra:
            errors.append(f"registry selector {key} contains unexpected indexed ids: {sorted(extra)}")

    maintenance = index.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")
        if maintenance.get("validationTool") != "tools/validate-external-source-index.py":
            errors.append("maintenance.validationTool is incorrect")
        if not _unique_text_list(maintenance.get("updateTriggers")):
            errors.append("maintenance.updateTriggers must be a unique non-empty list")

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
    print("External source index is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
