#!/usr/bin/env python3
"""Validate the versioned CMF Phone 2 Pro camera platform specification."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

MANIFEST_PATH = pathlib.Path("spec/platform-spec-manifest.v0.1.json")
DOCUMENT_PATH = pathlib.Path("docs/CMF_PHONE_2_PRO_CAMERA_PLATFORM_SPEC.md")
ISSUE_REFERENCE = re.compile(r"^issue:#([1-9][0-9]*)$")
VALID_BUILD_STATUS = {"OBSERVED", "UNTESTED"}
VALID_CONFIDENCE = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}
VALID_IMPLEMENTATION_USE = {
    "ENABLED",
    "ENABLED_WITH_FALLBACK",
    "DISABLED",
    "DIAGNOSTIC_ONLY",
    "DOCUMENTATION_ONLY",
}
VALID_DECISION_STATUS = {"ADOPTED", "SUPERSEDED"}
REQUIRED_SECTION_HEADINGS = {
    "hardware": "## Hardware",
    "public-api": "## Public API",
    "stock-apk": "## Stock APK",
    "firmware": "## Firmware",
    "vendor-api": "## Vendor API",
    "routing": "## Routing",
    "security": "## Security",
    "processing": "## Processing",
    "replacement-app": "## Replacement app",
}


def load_manifest(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))


def validate(
    root: pathlib.Path,
    manifest: dict[str, Any] | None = None,
    document: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if manifest is None:
        try:
            manifest = load_manifest(root)
        except (OSError, json.JSONDecodeError) as error:
            return [f"cannot load {MANIFEST_PATH}: {error}"]
    if document is None:
        try:
            document = (root / DOCUMENT_PATH).read_text(encoding="utf-8")
        except OSError as error:
            return [f"cannot load {DOCUMENT_PATH}: {error}"]

    if manifest.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    spec_version = manifest.get("specVersion")
    if not _text(spec_version):
        errors.append("specVersion must be non-empty")
    elif f"**Specification version:** {spec_version}" not in document:
        errors.append("document specification version does not match manifest")
    if not _text(manifest.get("publishedAt")):
        errors.append("publishedAt must be non-empty")
    if manifest.get("status") != "LIVING_SPECIFICATION":
        errors.append("status must be LIVING_SPECIFICATION")

    device = manifest.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        for field in ("marketingName", "model", "codename", "soc"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")

    build_scopes = manifest.get("buildScopes")
    build_ids: set[str] = set()
    if not isinstance(build_scopes, list) or not build_scopes:
        errors.append("buildScopes must be a non-empty list")
    else:
        for index, build in enumerate(build_scopes):
            prefix = f"buildScopes[{index}]"
            if not isinstance(build, dict):
                errors.append(f"{prefix} must be an object")
                continue
            build_id = build.get("id")
            if not _text(build_id):
                errors.append(f"{prefix}.id must be non-empty")
            elif build_id in build_ids:
                errors.append(f"duplicate build scope id {build_id}")
            else:
                build_ids.add(build_id)
            if not _text(build.get("fingerprint")):
                errors.append(f"{prefix}.fingerprint must be non-empty")
            if build.get("status") not in VALID_BUILD_STATUS:
                errors.append(f"{prefix}.status is invalid")
            _validate_evidence(root, build.get("evidence"), f"{prefix}.evidence", errors)

    required_sections = manifest.get("requiredSections")
    if not isinstance(required_sections, list):
        errors.append("requiredSections must be a list")
        required_sections = []
    elif set(required_sections) != set(REQUIRED_SECTION_HEADINGS):
        errors.append("requiredSections must contain every canonical section exactly once")
    elif len(required_sections) != len(set(required_sections)):
        errors.append("requiredSections contains duplicates")
    for section, heading in REQUIRED_SECTION_HEADINGS.items():
        if heading not in document:
            errors.append(f"document is missing section {section}")

    claims = manifest.get("claims")
    claim_ids: set[str] = set()
    claim_sections: set[str] = set()
    if not isinstance(claims, list) or not claims:
        errors.append("claims must be a non-empty list")
        claims = []
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be an object")
            continue
        claim_id = claim.get("id")
        if not _text(claim_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif claim_id in claim_ids:
            errors.append(f"duplicate claim id {claim_id}")
        else:
            claim_ids.add(claim_id)
            if claim_id not in document:
                errors.append(f"document is missing claim id {claim_id}")
        section = claim.get("section")
        if section not in REQUIRED_SECTION_HEADINGS:
            errors.append(f"{prefix}.section is invalid")
        else:
            claim_sections.add(section)
        if not _text(claim.get("statement")):
            errors.append(f"{prefix}.statement must be non-empty")
        confidence = claim.get("confidence")
        implementation_use = claim.get("implementationUse")
        if confidence not in VALID_CONFIDENCE:
            errors.append(f"{prefix}.confidence is invalid")
        if implementation_use not in VALID_IMPLEMENTATION_USE:
            errors.append(f"{prefix}.implementationUse is invalid")
        if confidence in {"HYPOTHESIS", "UNKNOWN"} and implementation_use in {
            "ENABLED",
            "ENABLED_WITH_FALLBACK",
        }:
            errors.append(f"{prefix} unresolved claim cannot be enabled")
        if claim.get("buildScope") not in build_ids:
            errors.append(f"{prefix}.buildScope references an unknown scope")
        _validate_evidence(root, claim.get("evidence"), f"{prefix}.evidence", errors)
        issue_count = _validate_issue_list(claim.get("unknownIssues"), prefix, errors)
        if confidence in {"PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"} and issue_count == 0:
            errors.append(f"{prefix} unresolved confidence requires unknownIssues")
    missing_claim_sections = set(REQUIRED_SECTION_HEADINGS) - claim_sections
    if missing_claim_sections:
        errors.append(
            "claims do not cover required sections: "
            + ", ".join(sorted(missing_claim_sections))
        )

    decisions = manifest.get("decisions")
    decision_ids: set[str] = set()
    if not isinstance(decisions, list) or not decisions:
        errors.append("decisions must be a non-empty list")
        decisions = []
    for index, decision in enumerate(decisions):
        prefix = f"decisions[{index}]"
        if not isinstance(decision, dict):
            errors.append(f"{prefix} must be an object")
            continue
        decision_id = decision.get("id")
        if not _text(decision_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif decision_id in decision_ids:
            errors.append(f"duplicate decision id {decision_id}")
        else:
            decision_ids.add(decision_id)
            if decision_id not in document:
                errors.append(f"document is missing decision id {decision_id}")
        if not _text(decision.get("decision")):
            errors.append(f"{prefix}.decision must be non-empty")
        if decision.get("status") not in VALID_DECISION_STATUS:
            errors.append(f"{prefix}.status is invalid")
        rationale = decision.get("rationaleClaims")
        if not isinstance(rationale, list) or not rationale:
            errors.append(f"{prefix}.rationaleClaims must be a non-empty list")
        else:
            for claim_id in rationale:
                if claim_id not in claim_ids:
                    errors.append(f"{prefix} references unknown claim {claim_id!r}")
        _validate_issue_list(decision.get("revisitIssues"), prefix + ".revisit", errors)

    triggers = manifest.get("updateTriggers")
    if not isinstance(triggers, list) or len(triggers) < 4:
        errors.append("updateTriggers must contain at least four entries")
    else:
        for index, trigger in enumerate(triggers):
            if not _text(trigger):
                errors.append(f"updateTriggers[{index}] must be non-empty")
    for heading in ("## Decision register", "## Known unknowns", "## Versioning and update policy"):
        if heading not in document:
            errors.append(f"document is missing required heading {heading}")

    return errors


def _validate_evidence(
    root: pathlib.Path,
    values: Any,
    name: str,
    errors: list[str],
) -> None:
    if not isinstance(values, list) or not values:
        errors.append(f"{name} must be a non-empty list")
        return
    seen: set[str] = set()
    for value in values:
        if not _text(value):
            errors.append(f"{name} entries must be non-empty")
            continue
        if value in seen:
            errors.append(f"{name} contains duplicate evidence {value}")
            continue
        seen.add(value)
        if ISSUE_REFERENCE.match(value) or value.startswith("https://"):
            continue
        path = pathlib.PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{name} contains non-relative path {value}")
        elif not (root / value).is_file():
            errors.append(f"{name} path does not exist: {value}")


def _validate_issue_list(value: Any, prefix: str, errors: list[str]) -> int:
    name = f"{prefix}.unknownIssues" if not prefix.endswith(".revisit") else f"{prefix}Issues"
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
    manifest = load_manifest(root)
    print(
        f"Validated platform specification {manifest['specVersion']} with "
        f"{len(manifest['claims'])} claims and {len(manifest['decisions'])} decisions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
