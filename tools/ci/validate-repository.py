#!/usr/bin/env python3
"""Validate structured evidence and repository safety invariants.

This validator intentionally performs no network access. It checks syntax, schema
conformance, unique identifiers, cross-record build links and accidental
raw-artifact commits.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
ERRORS: list[str] = []

RAW_ARTIFACT_SUFFIXES = {
    ".apk",
    ".apks",
    ".aab",
    ".img",
    ".bin",
    ".elf",
    ".so",
    ".dex",
    ".vdex",
    ".odex",
    ".zip",
    ".7z",
    ".tar",
    ".tgz",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> None:
    ERRORS.append(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - aggregate all validation errors
        fail(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f"{path.relative_to(ROOT)}: invalid YAML: {exc}")
        return None


def check_unique(items: list[dict[str, Any]], key: str, label: str) -> None:
    seen: dict[Any, int] = {}
    for index, item in enumerate(items):
        value = item.get(key)
        if value is None:
            fail(f"{label}[{index}] is missing {key!r}")
            continue
        if value in seen:
            fail(f"{label}: duplicate {key} {value!r} at indexes {seen[value]} and {index}")
        else:
            seen[value] = index


def build_identity_sha256(build: dict[str, Any]) -> str:
    platform = build.get("platform")
    packages = build.get("cameraPackages")
    if not isinstance(platform, dict) or not isinstance(packages, list):
        raise ValueError("platform and cameraPackages are required")
    fingerprint = platform.get("buildFingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ValueError("platform.buildFingerprint is required")
    normalized_packages: list[dict[str, str]] = []
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            raise ValueError(f"cameraPackages[{index}] must be an object")
        normalized: dict[str, str] = {}
        for field in ("packageName", "versionName", "sha256"):
            value = package.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"cameraPackages[{index}].{field} is required")
            normalized[field] = value
        normalized_packages.append(normalized)
    normalized_packages.sort(
        key=lambda item: (item["packageName"], item["versionName"], item["sha256"])
    )
    payload = {
        "buildFingerprint": fingerprint,
        "cameraPackages": normalized_packages,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_syntax() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        if ".git" not in path.parts:
            load_json(path)
    for pattern in ("*.yaml", "*.yml"):
        for path in sorted(ROOT.rglob(pattern)):
            if ".git" not in path.parts:
                load_yaml(path)


def validate_capabilities() -> None:
    schema_path = ROOT / "schemas" / "capability-entry.schema.json"
    baseline_path = ROOT / "data" / "capabilities" / "baseline.json"
    schema = load_json(schema_path)
    baseline = load_json(baseline_path)
    if not isinstance(schema, dict) or not isinstance(baseline, dict):
        return

    validator = jsonschema.Draft202012Validator(schema)
    capabilities = baseline.get("capabilities")
    if not isinstance(capabilities, list):
        fail("data/capabilities/baseline.json: capabilities must be an array")
        return

    check_unique(capabilities, "id", "baseline capabilities")
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            fail(f"baseline capabilities[{index}] must be an object")
            continue
        for error in sorted(validator.iter_errors(capability), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in error.path)
            fail(
                f"data/capabilities/baseline.json capabilities[{index}]"
                f"{'.' + location if location else ''}: {error.message}"
            )


def validate_version_matrix() -> None:
    schema_path = ROOT / "schemas" / "version-matrix.schema.json"
    matrix_path = ROOT / "data" / "builds" / "version-matrix.json"
    artifact_path = ROOT / "data" / "artifacts" / "diagnostic-manifest.yaml"
    schema = load_json(schema_path)
    matrix = load_json(matrix_path)
    artifact_manifest = load_yaml(artifact_path)
    if not isinstance(schema, dict) or not isinstance(matrix, dict):
        return

    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    for error in sorted(validator.iter_errors(matrix), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path)
        fail(
            f"{matrix_path.relative_to(ROOT)}"
            f"{'.' + location if location else ''}: {error.message}"
        )

    builds = matrix.get("builds")
    if not isinstance(builds, list):
        return
    object_builds = [item for item in builds if isinstance(item, dict)]
    check_unique(object_builds, "id", "version matrix builds")
    build_by_id = {
        build.get("id"): build
        for build in object_builds
        if isinstance(build.get("id"), str)
    }

    fingerprints: dict[str, str] = {}
    identities: dict[str, str] = {}
    diagnostic_ids: dict[str, str] = {}
    for index, build in enumerate(object_builds):
        build_id = build.get("id")
        expected_identity = build.get("identitySha256")
        try:
            actual_identity = build_identity_sha256(build)
        except ValueError as error:
            fail(f"version matrix builds[{index}]: invalid identity inputs: {error}")
        else:
            if actual_identity != expected_identity:
                fail(
                    f"version matrix builds[{index}]: identitySha256 mismatch; "
                    f"expected {actual_identity}, found {expected_identity!r}"
                )
            if isinstance(build_id, str) and not build_id.endswith(f"-{actual_identity[:8]}"):
                fail(
                    f"version matrix builds[{index}]: id must end with the identity "
                    f"prefix {actual_identity[:8]!r}"
                )
            previous_identity = identities.get(actual_identity)
            if previous_identity is not None:
                fail(
                    f"version matrix builds[{index}]: identity duplicates entry "
                    f"{previous_identity!r}"
                )
            elif isinstance(build_id, str):
                identities[actual_identity] = build_id

        platform = build.get("platform")
        if isinstance(platform, dict):
            fingerprint = platform.get("buildFingerprint")
            if isinstance(fingerprint, str):
                previous = fingerprints.get(fingerprint)
                if previous is not None:
                    fail(
                        f"version matrix builds[{index}]: buildFingerprint duplicates "
                        f"entry {previous!r}"
                    )
                elif isinstance(build_id, str):
                    fingerprints[fingerprint] = build_id

        camera_packages = build.get("cameraPackages")
        if isinstance(camera_packages, list):
            packages = [item for item in camera_packages if isinstance(item, dict)]
            check_unique(packages, "packageName", f"version matrix build {build_id!r} cameraPackages")

        diagnostic_builds = build.get("diagnosticBuilds")
        if isinstance(diagnostic_builds, list):
            diagnostics = [item for item in diagnostic_builds if isinstance(item, dict)]
            check_unique(diagnostics, "id", f"version matrix build {build_id!r} diagnosticBuilds")
            for diagnostic in diagnostics:
                diagnostic_id = diagnostic.get("id")
                if isinstance(diagnostic_id, str):
                    previous = diagnostic_ids.get(diagnostic_id)
                    if previous is not None:
                        fail(
                            f"diagnostic build id {diagnostic_id!r} appears in both "
                            f"{previous!r} and {build_id!r}"
                        )
                    elif isinstance(build_id, str):
                        diagnostic_ids[diagnostic_id] = build_id

    if not isinstance(artifact_manifest, dict):
        return
    artifacts = artifact_manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return
    artifact_by_id = {
        artifact.get("id"): artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("id"), str)
    }

    device_build = artifact_manifest.get("deviceBuild")
    if isinstance(device_build, dict):
        linked_id = device_build.get("matrixEntryId")
        if linked_id not in build_by_id:
            fail(
                f"{artifact_path.relative_to(ROOT)}: deviceBuild.matrixEntryId "
                f"{linked_id!r} is missing from the version matrix"
            )

    for artifact_id, artifact in artifact_by_id.items():
        linked_id = artifact.get("buildMatrixEntryId")
        if linked_id not in build_by_id:
            fail(
                f"diagnostic artifact {artifact_id!r}: buildMatrixEntryId "
                f"{linked_id!r} is missing from the version matrix"
            )

    for build_id, build in build_by_id.items():
        diagnostics = build.get("diagnosticBuilds")
        if not isinstance(diagnostics, list):
            continue
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, dict):
                continue
            source_artifacts = diagnostic.get("sourceArtifacts")
            if not isinstance(source_artifacts, list):
                continue
            for artifact_id in source_artifacts:
                artifact = artifact_by_id.get(artifact_id)
                if artifact is None:
                    fail(
                        f"version matrix build {build_id!r}: diagnostic source artifact "
                        f"{artifact_id!r} is missing"
                    )
                elif artifact.get("buildMatrixEntryId") != build_id:
                    fail(
                        f"version matrix build {build_id!r}: diagnostic source artifact "
                        f"{artifact_id!r} links to {artifact.get('buildMatrixEntryId')!r}"
                    )


def validate_artifact_manifest() -> None:
    path = ROOT / "data" / "artifacts" / "diagnostic-manifest.yaml"
    data = load_yaml(path)
    if not isinstance(data, dict):
        return
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        fail(f"{path.relative_to(ROOT)}: artifacts must be an array")
        return
    check_unique(artifacts, "id", "diagnostic artifacts")

    by_id = {item.get("id"): item for item in artifacts if isinstance(item, dict)}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            fail(f"diagnostic artifacts[{index}] must be an object")
            continue
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            fail(f"diagnostic artifacts[{index}]: invalid sha256 {digest!r}")
        size = artifact.get("sizeBytes")
        if not isinstance(size, int) or size < 0:
            fail(f"diagnostic artifacts[{index}]: invalid sizeBytes {size!r}")
        duplicate_of = artifact.get("duplicateOf")
        if duplicate_of is not None:
            target = by_id.get(duplicate_of)
            if target is None:
                fail(f"diagnostic artifacts[{index}]: duplicateOf target {duplicate_of!r} missing")
            elif target.get("sha256") != digest:
                fail(f"diagnostic artifacts[{index}]: duplicate hash differs from {duplicate_of!r}")


def validate_source_index() -> None:
    path = ROOT / "data" / "sources" / "source-index.yaml"
    data = load_yaml(path)
    if not isinstance(data, dict):
        return
    sources = data.get("sources")
    if not isinstance(sources, list):
        fail(f"{path.relative_to(ROOT)}: sources must be an array")
        return
    check_unique(sources, "id", "source index")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            fail(f"source index[{index}] must be an object")
            continue
        confidence = source.get("confidence")
        if not isinstance(confidence, int) or not 0 <= confidence <= 4:
            fail(f"source index[{index}]: confidence must be 0..4")
        url = source.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            fail(f"source index[{index}]: invalid URL {url!r}")


def validate_sensor_map() -> None:
    path = ROOT / "data" / "hardware" / "sensor-map.yaml"
    data = load_yaml(path)
    if not isinstance(data, dict):
        return
    routes = data.get("routes")
    if not isinstance(routes, dict):
        fail(f"{path.relative_to(ROOT)}: routes must be an object")
        return
    for route_name, route in routes.items():
        if not isinstance(route, dict):
            fail(f"sensor route {route_name!r} must be an object")
            continue
        confidence = route.get("confidence")
        if not isinstance(confidence, dict):
            fail(f"sensor route {route_name!r}: confidence must be an object")
            continue
        for field, value in confidence.items():
            if not isinstance(value, int) or not 0 <= value <= 4:
                fail(f"sensor route {route_name!r}: confidence.{field} must be 0..4")


def validate_keywords() -> None:
    path = ROOT / "tools" / "apk" / "routing-keywords.txt"
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    keywords = [line for line in lines if line and not line.startswith("#")]
    duplicates = sorted(keyword for keyword, count in Counter(keywords).items() if count > 1)
    if duplicates:
        fail(f"{path.relative_to(ROOT)}: duplicate keywords: {duplicates}")


def validate_no_raw_artifacts() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in RAW_ARTIFACT_SUFFIXES:
            fail(f"raw/proprietary artifact must not be committed: {path.relative_to(ROOT)}")


def validate_documented_hashes() -> None:
    """Flag malformed literal SHA-256 values in structured files.

    External artifacts are intentionally absent, so this validates syntax only rather
    than attempting to recalculate their digests.
    """

    for path in (ROOT / "data").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "sha256" not in line.lower() or ":" not in line:
                continue
            candidate = line.split(":", 1)[-1].strip().strip("\"' ,}")
            if candidate and candidate not in {"unknown", "null"} and not SHA256_PATTERN.fullmatch(candidate):
                fail(f"{path.relative_to(ROOT)}:{line_number}: malformed SHA-256 value {candidate!r}")


def main() -> int:
    validate_syntax()
    validate_capabilities()
    validate_version_matrix()
    validate_artifact_manifest()
    validate_source_index()
    validate_sensor_map()
    validate_keywords()
    validate_no_raw_artifacts()
    validate_documented_hashes()

    if ERRORS:
        print("Repository validation failed:", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1

    digest = hashlib.sha256()
    for path in sorted((ROOT / "data").rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    print(f"Repository validation passed. Structured-data digest: {digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
