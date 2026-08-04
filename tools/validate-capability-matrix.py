#!/usr/bin/env python3
"""Validate the versioned CMF Phone 2 Pro camera capability matrix."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

MATRIX_PATH = pathlib.Path("spec/camera-capability-matrix.v1.json")
ISSUE_REFERENCE = re.compile(r"^issue:#([1-9][0-9]*)$")

VALID_LAYERS = {
    "HARDWARE",
    "PUBLIC_API",
    "STOCK_APP",
    "VENDOR_API",
    "FIRMWARE",
    "SECURITY",
    "REPLACEMENT_APP",
}
VALID_REACHABILITY = {
    "PUBLIC",
    "STOCK_ONLY",
    "PRIVILEGED_OR_SYSTEM",
    "ADAPTER_GATED",
    "LOCAL_ONLY",
    "UNAVAILABLE",
    "UNKNOWN",
}
VALID_CONFIDENCE = {
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "HYPOTHESIS",
    "UNKNOWN",
}
VALID_REPLACEMENT_USE = {
    "ENABLED",
    "ENABLED_WITH_FALLBACK",
    "DIAGNOSTIC_ONLY",
    "DISABLED",
    "BLOCKED",
}
UNRESOLVED_CONFIDENCE = {"PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}
LIMITED_REACHABILITY = {
    "STOCK_ONLY",
    "PRIVILEGED_OR_SYSTEM",
    "ADAPTER_GATED",
    "UNAVAILABLE",
    "UNKNOWN",
}


def load_matrix(root: pathlib.Path) -> dict[str, Any]:
    path = root / MATRIX_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: pathlib.Path, matrix: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if matrix is None:
        try:
            matrix = load_matrix(root)
        except (OSError, json.JSONDecodeError) as error:
            return [f"cannot load {MATRIX_PATH}: {error}"]

    if matrix.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not _text(matrix.get("matrixVersion")):
        errors.append("matrixVersion must be non-empty")

    device = matrix.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        for field in ("marketingName", "codename", "soc"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")

    build_scopes = matrix.get("buildScopes")
    scope_ids: set[str] = set()
    if not isinstance(build_scopes, list) or not build_scopes:
        errors.append("buildScopes must be a non-empty list")
    else:
        for index, scope in enumerate(build_scopes):
            prefix = f"buildScopes[{index}]"
            if not isinstance(scope, dict):
                errors.append(f"{prefix} must be an object")
                continue
            scope_id = scope.get("id")
            if not _text(scope_id):
                errors.append(f"{prefix}.id must be non-empty")
            elif scope_id in scope_ids:
                errors.append(f"duplicate build scope id {scope_id}")
            else:
                scope_ids.add(scope_id)
            if scope.get("confidence") not in VALID_CONFIDENCE:
                errors.append(f"{prefix}.confidence is invalid")
            _validate_issue_list(scope.get("unknownIssues"), f"{prefix}.unknownIssues", errors)

    rows = matrix.get("rows")
    row_ids: set[str] = set()
    if not isinstance(rows, list) or not rows:
        errors.append("rows must be a non-empty list")
        return errors

    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        row_id = row.get("id")
        if not _text(row_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif row_id in row_ids:
            errors.append(f"duplicate row id {row_id}")
        else:
            row_ids.add(row_id)
        if not _text(row.get("feature")):
            errors.append(f"{prefix}.feature must be non-empty")

        layer = row.get("layer")
        reachability = row.get("reachability")
        confidence = row.get("confidence")
        replacement_use = row.get("replacementUse")
        if layer not in VALID_LAYERS:
            errors.append(f"{prefix}.layer is invalid")
        if reachability not in VALID_REACHABILITY:
            errors.append(f"{prefix}.reachability is invalid")
        if confidence not in VALID_CONFIDENCE:
            errors.append(f"{prefix}.confidence is invalid")
        if replacement_use not in VALID_REPLACEMENT_USE:
            errors.append(f"{prefix}.replacementUse is invalid")

        configuration = row.get("configuration")
        if not isinstance(configuration, dict) or not configuration:
            errors.append(f"{prefix}.configuration must be a non-empty object")

        build_scope = row.get("buildScope")
        if build_scope not in scope_ids:
            errors.append(f"{prefix}.buildScope references unknown scope {build_scope!r}")

        unknown_issues = row.get("unknownIssues")
        issue_count = _validate_issue_list(
            unknown_issues,
            f"{prefix}.unknownIssues",
            errors,
        )
        if confidence in UNRESOLVED_CONFIDENCE and issue_count == 0:
            errors.append(f"{prefix} unresolved confidence requires unknownIssues")
        if reachability in LIMITED_REACHABILITY and issue_count == 0:
            errors.append(f"{prefix} limited reachability requires unknownIssues")
        if replacement_use == "ENABLED" and reachability in LIMITED_REACHABILITY:
            errors.append(f"{prefix} cannot be ENABLED with {reachability} reachability")

        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must be a non-empty list")
        else:
            seen_evidence: set[str] = set()
            for evidence_index, reference in enumerate(evidence):
                evidence_prefix = f"{prefix}.evidence[{evidence_index}]"
                if not _text(reference):
                    errors.append(f"{evidence_prefix} must be non-empty")
                    continue
                if reference in seen_evidence:
                    errors.append(f"{prefix}.evidence contains duplicate {reference}")
                    continue
                seen_evidence.add(reference)
                if ISSUE_REFERENCE.match(reference):
                    continue
                if reference.startswith("https://"):
                    continue
                if pathlib.PurePosixPath(reference).is_absolute() or ".." in pathlib.PurePosixPath(reference).parts:
                    errors.append(f"{evidence_prefix} must be a repository-relative path")
                    continue
                if not (root / reference).is_file():
                    errors.append(f"{evidence_prefix} path does not exist: {reference}")

    return errors


def _validate_issue_list(value: Any, name: str, errors: list[str]) -> int:
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
    matrix = load_matrix(root)
    print(
        f"Validated {len(matrix['rows'])} capability rows "
        f"for matrix {matrix['matrixVersion']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
