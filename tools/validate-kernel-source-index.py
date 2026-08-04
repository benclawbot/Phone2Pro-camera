#!/usr/bin/env python3
"""Validate the official Galaga kernel-source provenance and camera index."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

INDEX_PATH = pathlib.Path("research/galaga-kernel-source-index.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/GALAGA_KERNEL_SOURCE_REFERENCE.md")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
BUILD_ID = re.compile(r"^[0-9]{10}$")
VALID_REPOSITORIES = {
    "android_kernel_6.1_nothing_mt6878",
    "android_kernel_modules_nothing_mt6878",
    "android_kernel_device_modules_6.1_nothing_mt6878",
}
VALID_ROLES = {"BASE_KERNEL", "KERNEL_MODULES", "DEVICE_MODULES_AND_DEVICE_TREE"}
VALID_RELATIONS = {"EXACT_BUILD_MATCH", "OFFICIAL_BUT_NOT_EXACT_BUILD_MATCH"}
VALID_SOURCE_CONFIDENCE = {"VERIFIED_SOURCE"}
VALID_MISSING_STATUS = {
    "NOT_PRESENT_IN_OFFICIAL_KERNEL_SOURCE_SET",
    "NOT_AVAILABLE_IN_INDEXED_OFFICIAL_BRANCHES",
}


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

    device = index.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        for field in ("marketingName", "model", "codename", "soc"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")
        if device.get("codename") != "Galaga":
            errors.append("device.codename must be Galaga")
        if device.get("soc") != "MT6878":
            errors.append("device.soc must be MT6878")

    observed = index.get("observedFirmware")
    observed_build = None
    if not isinstance(observed, dict):
        errors.append("observedFirmware must be an object")
    else:
        observed_build = observed.get("buildId")
        if not isinstance(observed_build, str) or not BUILD_ID.match(observed_build):
            errors.append("observedFirmware.buildId must be a 10-digit build ID")
        if observed_build and observed_build not in str(observed.get("fingerprint", "")):
            errors.append("observed build ID must appear in fingerprint")
        evidence = observed.get("evidence")
        if not _text(evidence) or not (root / evidence).is_file():
            errors.append("observedFirmware.evidence must reference an existing repository file")

    release = index.get("officialSourceRelease")
    relation = None
    if not isinstance(release, dict):
        errors.append("officialSourceRelease must be an object")
    else:
        for field in ("label", "releaseDate", "explanation"):
            if not _text(release.get(field)):
                errors.append(f"officialSourceRelease.{field} must be non-empty")
        relation = release.get("relationToObservedFirmware")
        if relation not in VALID_RELATIONS:
            errors.append("officialSourceRelease.relationToObservedFirmware is invalid")
        release_label = str(release.get("label", ""))
        if relation == "EXACT_BUILD_MATCH" and observed_build and observed_build not in release_label:
            errors.append("exact build match requires observed build ID in release label")
        if observed_build == "2606151653" and "260415-1710" in release_label and relation != "OFFICIAL_BUT_NOT_EXACT_BUILD_MATCH":
            errors.append("known 260415 versus 260615 mismatch must remain explicit")

    repositories = index.get("repositories")
    repository_ids: set[str] = set()
    repository_names: set[str] = set()
    if not isinstance(repositories, list) or len(repositories) != 3:
        errors.append("repositories must contain the three official Galaga source repositories")
        repositories = []
    for position, repository in enumerate(repositories):
        prefix = f"repositories[{position}]"
        if not isinstance(repository, dict):
            errors.append(f"{prefix} must be an object")
            continue
        repository_id = repository.get("id")
        if not _text(repository_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif repository_id in repository_ids:
            errors.append(f"duplicate repository id {repository_id}")
        else:
            repository_ids.add(repository_id)
            if f"`{repository_id}`" not in document:
                errors.append(f"document is missing repository id {repository_id}")
        if repository.get("owner") != "NothingOSS":
            errors.append(f"{prefix}.owner must be NothingOSS")
        repository_name = repository.get("repository")
        if repository_name not in VALID_REPOSITORIES:
            errors.append(f"{prefix}.repository is not an indexed official repository")
        elif repository_name in repository_names:
            errors.append(f"duplicate repository name {repository_name}")
        else:
            repository_names.add(repository_name)
        if repository.get("branch") != "mt6878/Galaga/16b":
            errors.append(f"{prefix}.branch must be mt6878/Galaga/16b")
        commit = repository.get("commit")
        if not isinstance(commit, str) or not SHA40.match(commit):
            errors.append(f"{prefix}.commit must be a lowercase 40-character SHA")
        if repository.get("role") not in VALID_ROLES:
            errors.append(f"{prefix}.role is invalid")
        for field in ("commitMessage", "commitDate", "cameraScope"):
            if not _text(repository.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if release and _text(release.get("label")) and release.get("label") not in str(repository.get("commitMessage", "")):
            errors.append(f"{prefix}.commitMessage must identify the indexed release")

    sources = index.get("cameraSources")
    source_ids: set[str] = set()
    source_paths: set[tuple[str, str]] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("cameraSources must be a non-empty list")
        sources = []
    for position, source in enumerate(sources):
        prefix = f"cameraSources[{position}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("id")
        if not _text(source_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif source_id in source_ids:
            errors.append(f"duplicate camera source id {source_id}")
        else:
            source_ids.add(source_id)
            if f"`{source_id}`" not in document:
                errors.append(f"document is missing camera source id {source_id}")
        repository_id = source.get("repositoryId")
        if repository_id not in repository_ids:
            errors.append(f"{prefix}.repositoryId references unknown repository")
        path = source.get("path")
        if not _remote_path(path):
            errors.append(f"{prefix}.path must be a safe repository-relative path")
        elif (str(repository_id), path) in source_paths:
            errors.append(f"duplicate indexed source path {repository_id}:{path}")
        else:
            source_paths.add((str(repository_id), path))
        if not _text(source.get("category")) or not _text(source.get("significance")):
            errors.append(f"{prefix}.category and significance must be non-empty")
        if not isinstance(source.get("galagaSpecific"), bool):
            errors.append(f"{prefix}.galagaSpecific must be boolean")
        if source.get("confidence") not in VALID_SOURCE_CONFIDENCE:
            errors.append(f"{prefix}.confidence is invalid")
        observations = source.get("observations")
        if observations is not None and (
            not isinstance(observations, list) or not observations or not all(_text(value) for value in observations)
        ):
            errors.append(f"{prefix}.observations must be a non-empty text list when present")

    missing = index.get("missingUserspaceAndFirmware")
    missing_ids: set[str] = set()
    if not isinstance(missing, list) or not missing:
        errors.append("missingUserspaceAndFirmware must be a non-empty list")
        missing = []
    for position, item in enumerate(missing):
        prefix = f"missingUserspaceAndFirmware[{position}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        item_id = item.get("id")
        if not _text(item_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif item_id in missing_ids:
            errors.append(f"duplicate missing component id {item_id}")
        else:
            missing_ids.add(item_id)
            if f"`{item_id}`" not in document:
                errors.append(f"document is missing userspace/firmware gap id {item_id}")
        if item.get("status") not in VALID_MISSING_STATUS:
            errors.append(f"{prefix}.status is invalid")
        for field in ("component", "whyRequired"):
            if not _text(item.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if _validate_issue_list(item.get("unknownIssues"), prefix, errors) == 0:
            errors.append(f"{prefix} must link active unknown issues")

    non_claims = index.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 4 or not all(_text(value) for value in non_claims):
        errors.append("nonClaims must contain at least four explicit boundaries")
    else:
        required_phrases = ("does not prove", "does not", "not treated", "does not claim")
        if not all(any(phrase in value for phrase in required_phrases) for value in non_claims):
            errors.append("every nonClaim must explicitly limit interpretation")

    for heading in (
        "## Provenance and build relation",
        "## Galaga camera topology",
        "## Configuration and camera subsystems",
        "## Clock, calibration, PDA, and flash interfaces",
        "## Missing userspace and firmware boundary",
        "## Non-claims",
        "## Update procedure",
    ):
        if heading not in document:
            errors.append(f"document is missing required heading {heading}")

    if relation == "OFFICIAL_BUT_NOT_EXACT_BUILD_MATCH" and "official but not an exact build match" not in document:
        errors.append("document must state the official source/build mismatch")
    if "complete Android camera" not in document:
        errors.append("document must state that the source set is not a complete Android camera stack")

    return errors


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


def _remote_path(value: Any) -> bool:
    if not _text(value):
        return False
    path = pathlib.PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and not str(value).startswith("/")


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
    index = load_index(root)
    print(
        f"Validated {len(index['repositories'])} official repositories, "
        f"{len(index['cameraSources'])} camera source paths, and "
        f"{len(index['missingUserspaceAndFirmware'])} userspace/firmware gaps."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
