#!/usr/bin/env python3
"""Validate the open-source camera architecture and licence decision register."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any
from urllib.parse import urlparse

INDEX_PATH = pathlib.Path("research/open-source-camera-architecture-review.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/OPEN_SOURCE_CAMERA_ARCHITECTURE_REVIEW.md")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHORT_REV = re.compile(r"^[0-9a-f]{6,12}$")
VALID_COVERAGE = {"FULL", "PARTIAL", "NONE", "NOT_OBSERVED"}
REQUIRED_DOMAINS = {
    "CAPTURE_SESSION",
    "RAW_YUV",
    "BURST",
    "GYRO",
    "STORAGE",
    "ERROR_HANDLING",
    "PRIVACY_INTENTS",
    "TESTING",
}
REQUIRED_PROJECT_IDS = {
    "androidx-camera-pipe",
    "grapheneos-camera",
    "open-camera",
    "motioncam",
    "photoncamera",
    "libre-camera",
}
REQUIRED_RECOMMENDATION_IDS = {
    "rec-camera-pipe-graph-contract",
    "rec-camera-pipe-simulation",
    "rec-graphene-storage-pipeline",
    "rec-clean-room-raw-buffer-pool",
    "rec-clean-room-gyro-frame-association",
    "rec-open-camera-test-inventory",
    "rec-libre-camera-ui-boundary",
    "rec-no-gpl-code-import",
}
VALID_LICENSES = {"Apache-2.0", "MIT", "GPL-3.0-only", "GPL-3.0-or-later"}
VALID_REUSE_DECISIONS = {
    "DIRECT_REUSE_APPROVED",
    "DIRECT_REUSE_WITH_ATTRIBUTION_REVIEW",
    "CLEAN_ROOM_PATTERN_ONLY",
}
VALID_IMPLEMENTATION_MODES = {
    "DIRECT_REUSE_OR_ADAPTATION",
    "DIRECT_REUSE_WITH_ATTRIBUTION_REVIEW",
    "CLEAN_ROOM_REIMPLEMENTATION",
    "POLICY_ONLY",
}
GPL_LICENSES = {"GPL-3.0-only", "GPL-3.0-or-later"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _unique_text_list(value: Any) -> bool:
    return _text_list(value) and len(value) == len(set(value))


def _https_url(value: Any) -> bool:
    if not _text(value):
        return False
    parsed = urlparse(str(value))
    return parsed.scheme == "https" and bool(parsed.netloc)


def _safe_external_path(value: Any) -> bool:
    if not _text(value) or str(value).startswith("/"):
        return False
    parts = pathlib.PurePosixPath(str(value)).parts
    return ".." not in parts


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

    context = index.get("projectContext")
    if not isinstance(context, dict):
        errors.append("projectContext must be an object")
    else:
        if context.get("projectLicense") != "MIT":
            errors.append("projectContext.projectLicense must be MIT")
        if context.get("issue") != 80:
            errors.append("projectContext.issue must be 80")
        for field in (
            "repository",
            "captureContract",
            "engineeringGuide",
            "complianceRegister",
            "complianceGuide",
            "legalCaveat",
        ):
            if not _text(context.get(field)):
                errors.append(f"projectContext.{field} must be non-empty")
        for field in ("captureContract", "engineeringGuide", "complianceRegister", "complianceGuide"):
            path = context.get(field)
            if _text(path) and not (root / str(path)).is_file():
                errors.append(f"projectContext.{field} must reference an existing file")
        if "not legal advice" not in str(context.get("legalCaveat", "")).lower():
            errors.append("projectContext.legalCaveat must state that the review is not legal advice")

    domains = index.get("coverageDomains")
    if not _unique_text_list(domains) or set(domains) != REQUIRED_DOMAINS:
        errors.append("coverageDomains must contain every required domain exactly once")

    projects = index.get("projects")
    project_ids: set[str] = set()
    project_licenses: dict[str, str] = {}
    if not isinstance(projects, list) or len(projects) != len(REQUIRED_PROJECT_IDS):
        errors.append("projects must contain exactly the six required projects")
        projects = []
    for position, project in enumerate(projects):
        prefix = f"projects[{position}]"
        if not isinstance(project, dict):
            errors.append(f"{prefix} must be an object")
            continue
        project_id = project.get("id")
        if not _text(project_id):
            errors.append(f"{prefix}.id must be non-empty")
            continue
        project_id = str(project_id)
        if project_id in project_ids:
            errors.append(f"duplicate project id {project_id}")
        project_ids.add(project_id)
        if f"`{project_id}`" not in document:
            errors.append(f"document is missing project id {project_id}")
        for field in (
            "name",
            "repository",
            "host",
            "branch",
            "revisionType",
            "licenseEvidence",
            "requiredReview",
        ):
            if not _text(project.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if not _https_url(project.get("sourceUrl")):
            errors.append(f"{prefix}.sourceUrl must be an https URL")
        revision = project.get("revision")
        revision_type = project.get("revisionType")
        if revision_type == "GIT_COMMIT":
            if not isinstance(revision, str) or not SHA40.fullmatch(revision):
                errors.append(f"{prefix}.revision must be a lowercase 40-character commit")
            elif revision not in str(project.get("sourceUrl", "")):
                errors.append(f"{prefix}.sourceUrl must include its pinned commit")
        elif revision_type == "SOURCEFORGE_SHORT_REVISION":
            if not isinstance(revision, str) or not SHORT_REV.fullmatch(revision):
                errors.append(f"{prefix}.revision must be a short hexadecimal SourceForge revision")
            if not _text(project.get("applicationRevision")):
                errors.append(f"{prefix}.applicationRevision must be recorded")
        else:
            errors.append(f"{prefix}.revisionType is invalid")

        license_id = project.get("license")
        if license_id not in VALID_LICENSES:
            errors.append(f"{prefix}.license is invalid")
        else:
            project_licenses[project_id] = str(license_id)
        decision = project.get("reuseDecision")
        if decision not in VALID_REUSE_DECISIONS:
            errors.append(f"{prefix}.reuseDecision is invalid")
        copied = project.get("copiedCodeAllowed")
        dependency = project.get("dependencyAllowed")
        if not isinstance(copied, bool) or not isinstance(dependency, bool):
            errors.append(f"{prefix}.copiedCodeAllowed and dependencyAllowed must be boolean")
        if license_id == "Apache-2.0":
            if decision != "DIRECT_REUSE_APPROVED" or copied is not True or dependency is not True:
                errors.append(f"{prefix} Apache-2.0 decision must allow reviewed direct reuse")
        elif license_id == "MIT":
            if decision != "DIRECT_REUSE_WITH_ATTRIBUTION_REVIEW" or copied is not True:
                errors.append(f"{prefix} MIT decision must require attribution review")
        elif license_id in GPL_LICENSES:
            if decision != "CLEAN_ROOM_PATTERN_ONLY" or copied is not False or dependency is not False:
                errors.append(f"{prefix} GPL project must be clean-room-only with copying/dependency disabled")

        paths = project.get("evidencePaths")
        if not isinstance(paths, list) or not paths or not all(_safe_external_path(path) for path in paths):
            errors.append(f"{prefix}.evidencePaths must contain safe source-relative paths")
        coverage = project.get("coverage")
        if not isinstance(coverage, dict) or set(coverage) != REQUIRED_DOMAINS:
            errors.append(f"{prefix}.coverage must define every domain exactly once")
        elif any(value not in VALID_COVERAGE for value in coverage.values()):
            errors.append(f"{prefix}.coverage contains an invalid value")
        if not _text_list(project.get("patterns")):
            errors.append(f"{prefix}.patterns must be a non-empty text list")
        if not _text_list(project.get("limitations")):
            errors.append(f"{prefix}.limitations must be a non-empty text list")

    missing_projects = REQUIRED_PROJECT_IDS - project_ids
    if missing_projects:
        errors.append(f"missing required project ids: {sorted(missing_projects)}")

    recommendations = index.get("recommendations")
    recommendation_ids: set[str] = set()
    if not isinstance(recommendations, list) or len(recommendations) != len(REQUIRED_RECOMMENDATION_IDS):
        errors.append("recommendations must contain exactly the eight required decisions")
        recommendations = []
    for position, recommendation in enumerate(recommendations):
        prefix = f"recommendations[{position}]"
        if not isinstance(recommendation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        recommendation_id = recommendation.get("id")
        if not _text(recommendation_id):
            errors.append(f"{prefix}.id must be non-empty")
            continue
        recommendation_id = str(recommendation_id)
        if recommendation_id in recommendation_ids:
            errors.append(f"duplicate recommendation id {recommendation_id}")
        recommendation_ids.add(recommendation_id)
        if f"`{recommendation_id}`" not in document:
            errors.append(f"document is missing recommendation id {recommendation_id}")
        for field in ("title", "decision", "rationale"):
            if not _text(recommendation.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        source_ids = recommendation.get("sourceProjectIds")
        if not _unique_text_list(source_ids):
            errors.append(f"{prefix}.sourceProjectIds must be a unique non-empty list")
            source_ids = []
        unknown_sources = set(source_ids) - project_ids
        if unknown_sources:
            errors.append(f"{prefix}.sourceProjectIds references unknown projects: {sorted(unknown_sources)}")
        mode = recommendation.get("implementationMode")
        if mode not in VALID_IMPLEMENTATION_MODES:
            errors.append(f"{prefix}.implementationMode is invalid")
        source_licenses = {project_licenses.get(source_id) for source_id in source_ids}
        has_gpl = bool(source_licenses & GPL_LICENSES)
        if has_gpl and mode not in {"CLEAN_ROOM_REIMPLEMENTATION", "POLICY_ONLY"}:
            errors.append(f"{prefix} GPL-derived recommendation must use clean-room or policy-only mode")
        if mode == "DIRECT_REUSE_OR_ADAPTATION" and any(
            license_id not in {"Apache-2.0", "MIT"} for license_id in source_licenses
        ):
            errors.append(f"{prefix} direct reuse can reference only permissive projects")
        if mode == "DIRECT_REUSE_WITH_ATTRIBUTION_REVIEW" and source_licenses != {"MIT"}:
            errors.append(f"{prefix} attribution-review reuse must reference MIT projects only")
        target_paths = recommendation.get("targetPaths")
        if not _unique_text_list(target_paths):
            errors.append(f"{prefix}.targetPaths must be a unique non-empty list")
        else:
            for target_path in target_paths:
                if not (root / target_path).is_file():
                    errors.append(f"{prefix}.targetPaths references missing file {target_path}")
        if not _text_list(recommendation.get("requirements")) or len(recommendation.get("requirements", [])) < 3:
            errors.append(f"{prefix}.requirements must contain at least three items")

    missing_recommendations = REQUIRED_RECOMMENDATION_IDS - recommendation_ids
    if missing_recommendations:
        errors.append(f"missing required recommendation ids: {sorted(missing_recommendations)}")

    non_claims = index.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 5 or not all(_text(item) for item in non_claims):
        errors.append("nonClaims must contain at least five explicit limitations")
    else:
        for position, statement in enumerate(non_claims):
            if not any(term in statement.lower() for term in ("does not", "not approve", "not certify")):
                errors.append(f"nonClaims[{position}] must explicitly limit interpretation")

    maintenance = index.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")
        if maintenance.get("validationTool") != "tools/validate-open-source-camera-architecture-review.py":
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
    print("Open-source camera architecture review is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
