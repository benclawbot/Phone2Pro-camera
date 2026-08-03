#!/usr/bin/env python3
"""Validate repeatable experiment protocols and executed result records."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]
NEGATIVE_LANGUAGE = re.compile(r"( failed under | was not observed under )", re.IGNORECASE)
PROHIBITED_NEGATIVE_LANGUAGE = (
    re.compile(r"\bis impossible\b", re.IGNORECASE),
    re.compile(r"\bdoes not exist\b", re.IGNORECASE),
    re.compile(r"\bcan never\b", re.IGNORECASE),
    re.compile(r"\bno .+ can work\b", re.IGNORECASE),
)


class ExperimentValidationError(ValueError):
    """Raised when registry input cannot be parsed."""


def parse_datetime(value: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ExperimentValidationError(f"{label}: invalid date-time {value!r}") from error


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExperimentValidationError(f"unable to read JSON {path}: {error}") from error


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ExperimentValidationError(f"unable to read YAML {path}: {error}") from error


def unique_index(items: Any, key: str, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{label} must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] must be an object")
            continue
        value = item.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{label}[{index}].{key} must be a non-empty string")
            continue
        if value in result:
            errors.append(f"{label}: duplicate {key} {value!r}")
        else:
            result[value] = item
    return result


def validate_sequences(items: Any, label: str, errors: list[str]) -> None:
    if not isinstance(items, list):
        return
    sequences = [item.get("sequence") for item in items if isinstance(item, dict)]
    if len(sequences) != len(set(sequences)):
        errors.append(f"{label}: duplicate sequence numbers")
    if sequences and sorted(sequences) != list(range(1, len(sequences) + 1)):
        errors.append(f"{label}: sequence numbers must be contiguous starting at 1")


def schema_errors(schema: dict[str, Any], item: dict[str, Any], label: str) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    errors: list[str] = []
    for error in sorted(validator.iter_errors(item), key=lambda entry: list(entry.path)):
        location = ".".join(str(part) for part in error.path)
        errors.append(f"{label}{'.' + location if location else ''}: {error.message}")
    return errors


def validate_records(
    protocol_registry: dict[str, Any],
    result_registry: dict[str, Any],
    protocol_schema: dict[str, Any],
    result_schema: dict[str, Any],
    matrix: dict[str, Any],
    artifact_manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if protocol_registry.get("schemaVersion") != 1:
        errors.append("protocol registry schemaVersion must be 1")
    if result_registry.get("schemaVersion") != 1:
        errors.append("result registry schemaVersion must be 1")

    protocols = unique_index(protocol_registry.get("protocols"), "id", "protocols", errors)
    results = unique_index(result_registry.get("results"), "id", "results", errors)
    builds = unique_index(matrix.get("builds"), "id", "version matrix builds", errors)
    manifest_artifacts = unique_index(
        artifact_manifest.get("artifacts"), "id", "diagnostic artifacts", errors
    )

    protocol_controls: dict[str, tuple[set[str], set[str]]] = {}
    for protocol_id, protocol in protocols.items():
        errors.extend(schema_errors(protocol_schema, protocol, f"protocol {protocol_id!r}"))
        validate_sequences(protocol.get("launchProcedure"), f"protocol {protocol_id!r} launchProcedure", errors)
        validate_sequences(protocol.get("captureOrder"), f"protocol {protocol_id!r} captureOrder", errors)
        controls = protocol.get("controls")
        if not isinstance(controls, dict):
            continue
        positive = unique_index(
            controls.get("positive"), "id", f"protocol {protocol_id!r} positive controls", errors
        )
        negative = unique_index(
            controls.get("negative"), "id", f"protocol {protocol_id!r} negative controls", errors
        )
        overlap = sorted(set(positive) & set(negative))
        if overlap:
            errors.append(f"protocol {protocol_id!r}: control IDs appear in both roles: {overlap}")
        protocol_controls[protocol_id] = (set(positive), set(negative))

    for result_id, result in results.items():
        errors.extend(schema_errors(result_schema, result, f"result {result_id!r}"))
        protocol_id = result.get("protocolId")
        protocol = protocols.get(protocol_id)
        if protocol is None:
            errors.append(f"result {result_id!r}: unknown protocolId {protocol_id!r}")
        elif result.get("protocolVersion") != protocol.get("version"):
            errors.append(
                f"result {result_id!r}: protocolVersion {result.get('protocolVersion')!r} "
                f"does not match {protocol.get('version')!r}"
            )

        build_id = result.get("buildMatrixEntryId")
        build = builds.get(build_id)
        if build is None:
            errors.append(f"result {result_id!r}: unknown buildMatrixEntryId {build_id!r}")

        timing = result.get("timing")
        result_start: datetime | None = None
        result_end: datetime | None = None
        if isinstance(timing, dict):
            try:
                result_start = parse_datetime(timing.get("startedAt", ""), f"result {result_id!r} startedAt")
                result_end = parse_datetime(timing.get("endedAt", ""), f"result {result_id!r} endedAt")
                if result_end < result_start:
                    errors.append(f"result {result_id!r}: endedAt precedes startedAt")
            except ExperimentValidationError as error:
                errors.append(str(error))

        execution_context = result.get("executionContext")
        if isinstance(execution_context, dict) and isinstance(build, dict):
            package = execution_context.get("package")
            camera_packages = build.get("cameraPackages")
            if isinstance(package, dict) and isinstance(camera_packages, list):
                matched = next(
                    (
                        candidate
                        for candidate in camera_packages
                        if isinstance(candidate, dict)
                        and candidate.get("packageName") == package.get("packageName")
                    ),
                    None,
                )
                if matched is None:
                    errors.append(
                        f"result {result_id!r}: package {package.get('packageName')!r} "
                        f"is absent from build {build_id!r}"
                    )
                elif matched.get("versionName") != package.get("versionName"):
                    errors.append(
                        f"result {result_id!r}: package version {package.get('versionName')!r} "
                        f"does not match matrix version {matched.get('versionName')!r}"
                    )

        result_artifacts = unique_index(
            result.get("artifacts"), "artifactId", f"result {result_id!r} artifacts", errors
        )
        for artifact_id, artifact in result_artifacts.items():
            manifest = manifest_artifacts.get(artifact_id)
            if manifest is None:
                errors.append(f"result {result_id!r}: unknown artifactId {artifact_id!r}")
                continue
            for field in ("name", "sizeBytes", "sha256"):
                if artifact.get(field) != manifest.get(field):
                    errors.append(
                        f"result {result_id!r} artifact {artifact_id!r}: {field} "
                        f"does not match diagnostic manifest"
                    )
            if manifest.get("buildMatrixEntryId") != build_id:
                errors.append(
                    f"result {result_id!r} artifact {artifact_id!r}: manifest build link "
                    f"{manifest.get('buildMatrixEntryId')!r} does not match {build_id!r}"
                )
            try:
                acquired = parse_datetime(
                    artifact.get("acquiredAt", ""),
                    f"result {result_id!r} artifact {artifact_id!r} acquiredAt",
                )
                if result_start and acquired < result_start:
                    errors.append(f"result {result_id!r} artifact {artifact_id!r}: acquired before result start")
                if result_end and acquired > result_end:
                    errors.append(f"result {result_id!r} artifact {artifact_id!r}: acquired after result end")
            except ExperimentValidationError as error:
                errors.append(str(error))

        controls = result.get("controls")
        if isinstance(controls, dict):
            result_positive = unique_index(
                controls.get("positive"),
                "controlId",
                f"result {result_id!r} positive controls",
                errors,
            )
            result_negative = unique_index(
                controls.get("negative"),
                "controlId",
                f"result {result_id!r} negative controls",
                errors,
            )
            expected = protocol_controls.get(protocol_id)
            if expected is not None:
                if set(result_positive) != expected[0]:
                    errors.append(
                        f"result {result_id!r}: positive control IDs {sorted(result_positive)} "
                        f"do not match protocol {sorted(expected[0])}"
                    )
                if set(result_negative) != expected[1]:
                    errors.append(
                        f"result {result_id!r}: negative control IDs {sorted(result_negative)} "
                        f"do not match protocol {sorted(expected[1])}"
                    )
            for control in [*result_positive.values(), *result_negative.values()]:
                for artifact_id in control.get("artifactIds", []):
                    if artifact_id not in result_artifacts:
                        errors.append(
                            f"result {result_id!r} control {control.get('controlId')!r}: "
                            f"artifact {artifact_id!r} is not declared"
                        )

        captures = result.get("captures")
        validate_sequences(captures, f"result {result_id!r} captures", errors)
        if isinstance(captures, list):
            for capture in captures:
                if not isinstance(capture, dict):
                    continue
                for artifact_id in capture.get("artifactIds", []):
                    if artifact_id not in result_artifacts:
                        errors.append(
                            f"result {result_id!r} capture {capture.get('sequence')!r}: "
                            f"artifact {artifact_id!r} is not declared"
                        )
                for field in ("startedAt", "endedAt"):
                    value = capture.get(field)
                    if value is not None:
                        try:
                            instant = parse_datetime(
                                value,
                                f"result {result_id!r} capture {capture.get('sequence')!r} {field}",
                            )
                            if result_start and instant < result_start:
                                errors.append(
                                    f"result {result_id!r} capture {capture.get('sequence')!r}: "
                                    f"{field} precedes result start"
                                )
                            if result_end and instant > result_end:
                                errors.append(
                                    f"result {result_id!r} capture {capture.get('sequence')!r}: "
                                    f"{field} exceeds result end"
                                )
                        except ExperimentValidationError as error:
                            errors.append(str(error))
                if capture.get("startedAt") and capture.get("endedAt"):
                    start = parse_datetime(capture["startedAt"], "capture startedAt")
                    end = parse_datetime(capture["endedAt"], "capture endedAt")
                    if end < start:
                        errors.append(
                            f"result {result_id!r} capture {capture.get('sequence')!r}: "
                            f"endedAt precedes startedAt"
                        )

        outcome = result.get("outcome")
        if isinstance(outcome, dict):
            statement = outcome.get("negativeResultStatement")
            if isinstance(statement, str):
                if not NEGATIVE_LANGUAGE.search(statement):
                    errors.append(
                        f"result {result_id!r}: negativeResultStatement must use "
                        f"'failed under' or 'was not observed under'"
                    )
                for prohibited in PROHIBITED_NEGATIVE_LANGUAGE:
                    if prohibited.search(statement):
                        errors.append(
                            f"result {result_id!r}: negativeResultStatement contains "
                            f"prohibited generalization {prohibited.pattern!r}"
                        )

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocols", default=str(ROOT / "data" / "experiments" / "protocols.json"))
    parser.add_argument("--results", default=str(ROOT / "data" / "experiments" / "results.json"))
    parser.add_argument("--matrix", default=str(ROOT / "data" / "builds" / "version-matrix.json"))
    parser.add_argument(
        "--artifacts",
        default=str(ROOT / "data" / "artifacts" / "diagnostic-manifest.yaml"),
    )
    parser.add_argument(
        "--protocol-schema",
        default=str(ROOT / "schemas" / "experiment-protocol.schema.json"),
    )
    parser.add_argument(
        "--result-schema",
        default=str(ROOT / "schemas" / "experiment-result.schema.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        protocol_registry = load_json(Path(args.protocols))
        result_registry = load_json(Path(args.results))
        protocol_schema = load_json(Path(args.protocol_schema))
        result_schema = load_json(Path(args.result_schema))
        matrix = load_json(Path(args.matrix))
        artifact_manifest = load_yaml(Path(args.artifacts))
    except ExperimentValidationError as error:
        print(f"Experiment validation failed: {error}", file=sys.stderr)
        return 2

    values = (
        protocol_registry,
        result_registry,
        protocol_schema,
        result_schema,
        matrix,
        artifact_manifest,
    )
    if not all(isinstance(value, dict) for value in values):
        print("Experiment validation failed: all registry inputs must be objects", file=sys.stderr)
        return 2

    errors = validate_records(
        protocol_registry,
        result_registry,
        protocol_schema,
        result_schema,
        matrix,
        artifact_manifest,
    )
    if errors:
        print("Experiment validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"Experiment validation passed: {len(protocol_registry['protocols'])} protocol(s), "
        f"{len(result_registry['results'])} result(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
