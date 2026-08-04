#!/usr/bin/env python3
"""Validate source, licence, artifact-handling and clean-room records."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

REGISTER_PATH = pathlib.Path("compliance/source-license-register.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/SOURCE_LICENCE_COMPLIANCE.md")
VALID_DECISIONS = {
    "APPROVED",
    "APPROVED_RUNTIME",
    "APPROVED_TEST_ONLY",
    "APPROVED_BUILD_ONLY",
    "APPROVED_CI_ONLY",
    "APPROVED_CI_ONLY_WITH_PINNING_GATE",
}
VALID_REVIEW_STATUS = {"RECORDED", "RELEASE_REVIEW_REQUIRED"}
VALID_PATENT_STATUS = {"NOT_CLEARED", "CLEARED_WITH_REVIEW_REFERENCE"}
DEPENDENCY_LINE = re.compile(r"^(implementation|testImplementation)\(")


def load_register(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / REGISTER_PATH).read_text(encoding="utf-8"))


def validate(
    root: pathlib.Path,
    register: dict[str, Any] | None = None,
    document: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if register is None:
        try:
            register = load_register(root)
        except (OSError, json.JSONDecodeError) as error:
            return [f"cannot load {REGISTER_PATH}: {error}"]
    if document is None:
        try:
            document = (root / DOCUMENT_PATH).read_text(encoding="utf-8")
        except OSError as error:
            return [f"cannot load {DOCUMENT_PATH}: {error}"]

    if register.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    version = register.get("registerVersion")
    if not _text(version):
        errors.append("registerVersion must be non-empty")
    elif f"**Register version:** {version}" not in document:
        errors.append("document register version does not match")
    if not _text(register.get("scope")):
        errors.append("scope must be non-empty")
    if not _text(register.get("legalNotice")):
        errors.append("legalNotice must be non-empty")

    dependencies = register.get("dependencies")
    dependency_ids: set[str] = set()
    fragments_by_file: dict[str, set[str]] = {}
    if not isinstance(dependencies, list) or not dependencies:
        errors.append("dependencies must be a non-empty list")
        dependencies = []
    for index, dependency in enumerate(dependencies):
        prefix = f"dependencies[{index}]"
        if not isinstance(dependency, dict):
            errors.append(f"{prefix} must be an object")
            continue
        dependency_id = dependency.get("id")
        if not _text(dependency_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif dependency_id in dependency_ids:
            errors.append(f"duplicate dependency id {dependency_id}")
        else:
            dependency_ids.add(dependency_id)
            if f"`{dependency_id}`" not in document:
                errors.append(f"document is missing dependency id {dependency_id}")
        for field in (
            "kind",
            "component",
            "version",
            "licence",
            "licenceEvidence",
            "upstream",
            "declaredIn",
            "use",
            "decision",
            "redistribution",
            "attribution",
            "reviewStatus",
        ):
            if not _text(dependency.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if dependency.get("decision") not in VALID_DECISIONS:
            errors.append(f"{prefix}.decision is invalid")
        if dependency.get("reviewStatus") not in VALID_REVIEW_STATUS:
            errors.append(f"{prefix}.reviewStatus is invalid")
        if dependency.get("version") == "UNPINNED" and dependency.get("reviewStatus") != "RELEASE_REVIEW_REQUIRED":
            errors.append(f"{prefix} unpinned dependency requires release review")
        declared_in = dependency.get("declaredIn")
        fragments = dependency.get("declarationFragments")
        if not isinstance(fragments, list) or not fragments:
            errors.append(f"{prefix}.declarationFragments must be a non-empty list")
        elif _text(declared_in):
            declared_path = root / declared_in
            if not declared_path.is_file():
                errors.append(f"{prefix}.declaredIn path does not exist: {declared_in}")
            else:
                source = declared_path.read_text(encoding="utf-8")
                for fragment in fragments:
                    if not _text(fragment):
                        errors.append(f"{prefix}.declarationFragments entries must be non-empty")
                    elif fragment not in source:
                        errors.append(f"{prefix} declaration fragment not found: {fragment}")
                    else:
                        fragments_by_file.setdefault(declared_in, set()).add(fragment.strip())
        parent = dependency.get("parentDependency")
        if parent is not None and parent not in dependency_ids and not any(
            item.get("id") == parent for item in dependencies if isinstance(item, dict)
        ):
            errors.append(f"{prefix}.parentDependency references unknown id {parent!r}")

    _validate_direct_declarations(root, fragments_by_file, errors)

    artifacts = register.get("controlledArtifacts")
    artifact_ids: set[str] = set()
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("controlledArtifacts must be a non-empty list")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        prefix = f"controlledArtifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        artifact_id = artifact.get("id")
        if not _text(artifact_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif artifact_id in artifact_ids:
            errors.append(f"duplicate controlled artifact id {artifact_id}")
        else:
            artifact_ids.add(artifact_id)
            if f"`{artifact_id}`" not in document:
                errors.append(f"document is missing artifact id {artifact_id}")
        for field in ("kind", "licenceOrRights", "decision", "redistribution"):
            if not _text(artifact.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        redistribution = str(artifact.get("redistribution", ""))
        if artifact.get("licenceOrRights") in {
            "PROPRIETARY_OR_UNKNOWN",
            "USER_CONTROLLED_PRIVATE_DATA",
            "USER_COPYRIGHT_OR_OTHER_USER_CONTROLLED_RIGHTS",
            "MIXED_OPEN_SOURCE_PROPRIETARY_AND_UNKNOWN",
        } and "ALLOWED" in redistribution:
            errors.append(f"{prefix} restricted artifact cannot be marked ALLOWED")
        _validate_evidence_paths(root, artifact.get("evidence"), f"{prefix}.evidence", errors)

    clean_room = register.get("cleanRoomBoundary")
    if not isinstance(clean_room, dict):
        errors.append("cleanRoomBoundary must be an object")
    else:
        for field in ("learnedBehaviourAllowed", "copyingProhibited", "requiredSeparation"):
            values = clean_room.get(field)
            if not isinstance(values, list) or len(values) < 3 or not all(_text(value) for value in values):
                errors.append(f"cleanRoomBoundary.{field} must contain at least three entries")

    patent_areas = register.get("patentSensitiveAreas")
    if not isinstance(patent_areas, list) or not patent_areas:
        errors.append("patentSensitiveAreas must be a non-empty list")
    else:
        for index, area in enumerate(patent_areas):
            prefix = f"patentSensitiveAreas[{index}]"
            if not isinstance(area, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if not _text(area.get("area")) or not _text(area.get("decision")):
                errors.append(f"{prefix} area and decision must be non-empty")
            if area.get("status") not in VALID_PATENT_STATUS:
                errors.append(f"{prefix}.status is invalid")

    release_gates = register.get("releaseGates")
    if not isinstance(release_gates, list) or len(release_gates) < 5:
        errors.append("releaseGates must contain at least five entries")
    elif not all(_text(gate) for gate in release_gates):
        errors.append("releaseGates entries must be non-empty")

    for heading in (
        "## Dependency decisions",
        "## Proprietary and private artifact handling",
        "## Clean-room boundary",
        "## Patent-sensitive areas",
        "## Release gates",
        "## Contributor checklist",
    ):
        if heading not in document:
            errors.append(f"document is missing required heading {heading}")

    return errors


def _validate_direct_declarations(
    root: pathlib.Path,
    fragments_by_file: dict[str, set[str]],
    errors: list[str],
) -> None:
    build_path = "camera-app/app/build.gradle.kts"
    build = (root / build_path).read_text(encoding="utf-8")
    registered = fragments_by_file.get(build_path, set())
    for raw_line in build.splitlines():
        line = raw_line.strip()
        if DEPENDENCY_LINE.match(line) and line not in registered:
            errors.append(f"unregistered Gradle dependency declaration: {line}")
    for required in ("compileSdk = 36", "targetSdk = 36"):
        if required not in registered:
            errors.append(f"unregistered Android SDK declaration: {required}")

    root_build_path = "camera-app/build.gradle.kts"
    root_build = (root / root_build_path).read_text(encoding="utf-8")
    root_registered = fragments_by_file.get(root_build_path, set())
    for raw_line in root_build.splitlines():
        line = raw_line.strip()
        if "id(\"com.android.application\") version" in line and line not in root_registered:
            errors.append(f"unregistered Android Gradle plugin declaration: {line}")

    workflow_path = ".github/workflows/validate.yml"
    workflow = (root / workflow_path).read_text(encoding="utf-8")
    workflow_registered = fragments_by_file.get(workflow_path, set())
    for raw_line in workflow.splitlines():
        line = raw_line.strip()
        if line.startswith("uses: ") and line not in workflow_registered:
            errors.append(f"unregistered validation workflow action: {line}")
    install_line = "python -m pip install --disable-pip-version-check jsonschema PyYAML"
    if install_line in workflow and install_line not in workflow_registered:
        errors.append("unregistered validation workflow Python dependencies")


def _validate_evidence_paths(
    root: pathlib.Path,
    values: Any,
    name: str,
    errors: list[str],
) -> None:
    if not isinstance(values, list) or not values:
        errors.append(f"{name} must be a non-empty list")
        return
    for value in values:
        if not _text(value):
            errors.append(f"{name} entries must be non-empty paths")
        elif not (root / value).is_file():
            errors.append(f"{name} path does not exist: {value}")


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
    register = load_register(root)
    print(
        f"Validated {len(register['dependencies'])} dependencies, "
        f"{len(register['controlledArtifacts'])} controlled artifact classes, "
        f"and {len(register['patentSensitiveAreas'])} patent-sensitive areas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
