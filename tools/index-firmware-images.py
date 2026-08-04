#!/usr/bin/env python3
"""Create a local SHA-256 inventory for Galaga firmware and partition artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Iterable

SOURCE_INDEX = pathlib.Path("research/galaga-firmware-acquisition.v1.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_SUFFIXES = {
    ".img",
    ".bin",
    ".mbn",
    ".elf",
    ".fw",
    ".zip",
    ".sha256",
}


def load_source_index(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / SOURCE_INDEX).read_text(encoding="utf-8"))


def required_partitions(source_index: dict[str, Any]) -> set[str]:
    coverage = source_index.get("requiredPartitionCoverage")
    if not isinstance(coverage, list):
        raise ValueError("requiredPartitionCoverage must be a list")
    partitions: set[str] = set()
    for record in coverage:
        if not isinstance(record, dict) or not _text(record.get("partition")):
            raise ValueError("partition coverage records require partition names")
        partition = record["partition"]
        if partition in partitions:
            raise ValueError(f"duplicate required partition {partition}")
        partitions.add(partition)
    return partitions


def validate_source_index(source_index: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if source_index.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if source_index.get("status") != "BLOCKED_PENDING_LOCAL_ARTIFACTS":
        errors.append("source index must remain blocked until local artifacts are verified")
    device = source_index.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        fingerprint = device.get("fingerprint")
        build_id = device.get("buildId")
        if not _text(fingerprint) or not _text(build_id) or build_id not in fingerprint:
            errors.append("device fingerprint must contain the build ID")
    source_ids: set[str] = set()
    sources = source_index.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty list")
    else:
        for index, source in enumerate(sources):
            prefix = f"sources[{index}]"
            if not isinstance(source, dict):
                errors.append(f"{prefix} must be an object")
                continue
            source_id = source.get("id")
            if not _text(source_id):
                errors.append(f"{prefix}.id must be non-empty")
            elif source_id in source_ids:
                errors.append(f"duplicate source id {source_id}")
            else:
                source_ids.add(source_id)
            if not _text(source.get("url")) or not str(source.get("url")).startswith("https://"):
                errors.append(f"{prefix}.url must be HTTPS")
            if source.get("status") == "LOCATED_NOT_HASHED":
                if source.get("sha256") is not None or source.get("sizeBytes") is not None:
                    errors.append(f"{prefix} located-not-hashed source cannot contain digest metadata")
    coverage = source_index.get("requiredPartitionCoverage")
    if not isinstance(coverage, list) or not coverage:
        errors.append("requiredPartitionCoverage must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, record in enumerate(coverage):
            prefix = f"requiredPartitionCoverage[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{prefix} must be an object")
                continue
            partition = record.get("partition")
            if not _text(partition):
                errors.append(f"{prefix}.partition must be non-empty")
            elif partition in seen:
                errors.append(f"duplicate partition coverage {partition}")
            else:
                seen.add(partition)
            if record.get("status") != "NOT_VERIFIED":
                errors.append(f"{prefix} cannot be verified in the source-only index")
            if not _text(record.get("group")) or not _text(record.get("cameraRelevance")):
                errors.append(f"{prefix} group and cameraRelevance must be non-empty")
    requirements = source_index.get("verificationRequirements")
    if not isinstance(requirements, dict):
        errors.append("verificationRequirements must be an object")
    elif requirements.get("hashAlgorithm") != "SHA-256":
        errors.append("verification hash algorithm must be SHA-256")
    blockers = source_index.get("completionBlockers")
    if not isinstance(blockers, list) or len(blockers) < 4 or not all(_text(value) for value in blockers):
        errors.append("completionBlockers must contain at least four entries")
    return errors


def index_directory(
    input_dir: pathlib.Path,
    source_index: dict[str, Any],
    source_id: str,
    collector: str,
    collected_at: str,
) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        raise ValueError("input directory does not exist")
    if not _text(source_id) or source_id not in {
        source.get("id")
        for source in source_index.get("sources", [])
        if isinstance(source, dict)
    }:
        raise ValueError("source ID is not declared in the acquisition index")
    if not _text(collector):
        raise ValueError("collector must be non-empty")
    _parse_timestamp(collected_at)
    required = required_partitions(source_index)
    artifacts: list[dict[str, Any]] = []
    for path in _regular_files(input_dir):
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        partition = infer_partition(path.name, required)
        if partition is None:
            continue
        size = path.stat().st_size
        if size <= 0:
            raise ValueError(f"artifact is empty: {path.relative_to(input_dir)}")
        artifacts.append(
            {
                "sourceId": source_id,
                "relativePath": path.relative_to(input_dir).as_posix(),
                "partition": partition,
                "sizeBytes": size,
                "sha256": hash_file(path),
                "collectedAt": collected_at,
                "collector": collector,
                "status": "VERIFIED_LOCAL_SHA256",
            }
        )
    artifacts.sort(key=lambda item: (item["partition"], item["relativePath"]))
    device = source_index["device"]
    return {
        "schemaVersion": 1,
        "generatedFrom": SOURCE_INDEX.as_posix(),
        "indexVersion": source_index["indexVersion"],
        "deviceFingerprint": device["fingerprint"],
        "buildId": device["buildId"],
        "sourceId": source_id,
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
        "missingRequiredPartitions": sorted(required - {item["partition"] for item in artifacts}),
    }


def validate_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if inventory.get("schemaVersion") != 1:
        errors.append("inventory schemaVersion must be 1")
    artifacts = inventory.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("inventory artifacts must be a list")
        return errors
    if inventory.get("artifactCount") != len(artifacts):
        errors.append("artifactCount does not match artifacts length")
    paths: set[str] = set()
    for index, artifact in enumerate(artifacts):
        prefix = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("sourceId", "relativePath", "partition", "collectedAt", "collector"):
            if not _text(artifact.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        relative = artifact.get("relativePath")
        if _text(relative):
            path = pathlib.PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"{prefix}.relativePath must be safe and relative")
            elif relative in paths:
                errors.append(f"duplicate artifact path {relative}")
            else:
                paths.add(relative)
        if not isinstance(artifact.get("sizeBytes"), int) or isinstance(artifact.get("sizeBytes"), bool) or artifact.get("sizeBytes", 0) <= 0:
            errors.append(f"{prefix}.sizeBytes must be positive")
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or not SHA256.match(digest):
            errors.append(f"{prefix}.sha256 must be a lowercase SHA-256 digest")
        if artifact.get("status") != "VERIFIED_LOCAL_SHA256":
            errors.append(f"{prefix}.status must be VERIFIED_LOCAL_SHA256")
        try:
            _parse_timestamp(str(artifact.get("collectedAt", "")))
        except ValueError:
            errors.append(f"{prefix}.collectedAt must be an ISO-8601 timestamp")
    missing = inventory.get("missingRequiredPartitions")
    if not isinstance(missing, list) or not all(_text(value) for value in missing):
        errors.append("missingRequiredPartitions must be a text list")
    return errors


def infer_partition(filename: str, required: set[str]) -> str | None:
    stem = filename.lower()
    for suffix in sorted(ALLOWED_SUFFIXES, key=len, reverse=True):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    stem = re.sub(r"(?:[-_.](?:a|b|slot-a|slot-b))$", "", stem)
    stem = re.sub(r"(?:[-_.](?:image|partition|raw))$", "", stem)
    matches = [partition for partition in required if stem == partition or stem.startswith(partition + ".")]
    if not matches:
        return None
    return max(matches, key=len)


def hash_file(path: pathlib.Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed: {path.relative_to(root)}")
        if path.is_file():
            yield path


def _parse_timestamp(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    timestamp = dt.datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return timestamp


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=pathlib.Path)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--collector", required=True)
    parser.add_argument("--collected-at", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    source_index = load_source_index(root)
    source_errors = validate_source_index(source_index)
    if source_errors:
        for error in source_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    try:
        inventory = index_directory(
            args.input_dir,
            source_index,
            args.source_id,
            args.collector,
            args.collected_at,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    inventory_errors = validate_inventory(inventory)
    if inventory_errors:
        for error in inventory_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(
        f"Indexed {inventory['artifactCount']} artifacts; "
        f"{len(inventory['missingRequiredPartitions'])} required partitions remain missing."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
