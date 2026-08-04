#!/usr/bin/env python3
"""Validate the bounded CMF Phone 2 Pro community camera evidence register."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any
from urllib.parse import urlparse

INDEX_PATH = pathlib.Path("research/community-camera-evidence.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/COMMUNITY_CAMERA_EVIDENCE.md")
VALID_GRADES = {
    "SECOND_HAND_LEAD",
    "SINGLE_REPORT",
    "MULTIPLE_INDEPENDENT_REPORTS",
    "OFFICIAL_CONTEXT_PLUS_REPORT",
}
VALID_CONTEXT_STATUS = {"EXACT", "PARTIAL", "UNKNOWN"}
VALID_DATE_PRECISION = {"DAY", "MONTH", "YEAR", "UNKNOWN"}
REQUIRED_TOPICS = {
    "GCAM_COMPATIBILITY",
    "PUBLIC_CAMERA_IDS",
    "STOCK_VIDEO_ROUTING",
    "FIRMWARE_REGRESSION",
    "LENS_HANDOVER",
    "AUTOFOCUS_REGRESSION",
    "POST_PROCESSING",
    "CAMERA_APP_STABILITY",
}
REQUIRED_TEST_IDS = {
    "test-public-camera-id-enumeration",
    "test-gcam-build-and-lens-matrix",
    "test-stock-video-route-matrix",
    "test-lens-handover-continuity",
    "test-build-controlled-image-regression",
    "test-preview-final-processing-delta",
    "test-cross-lens-autofocus",
    "test-stock-camera-soak",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _id_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
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

    device = index.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        for field in ("marketingName", "model", "codename", "observedBuildId", "observedFingerprintEvidence"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")
        if device.get("codename") != "Galaga":
            errors.append("device.codename must be Galaga")
        evidence = device.get("observedFingerprintEvidence")
        if _text(evidence) and not (root / str(evidence)).is_file():
            errors.append("device.observedFingerprintEvidence must reference an existing file")

    scope = index.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        if scope.get("issue") != 79:
            errors.append("scope.issue must be 79")
        for field in ("objective", "interpretationRule", "redistributionRule"):
            if not _text(scope.get(field)):
                errors.append(f"scope.{field} must be non-empty")
        interpretation = str(scope.get("interpretationRule", "")).lower()
        if "never implementation proof" not in interpretation:
            errors.append("scope.interpretationRule must reject implementation proof")
        redistribution = str(scope.get("redistributionRule", "")).lower()
        for required in ("do not redistribute", "apks", "private logs", "user photographs"):
            if required not in redistribution:
                errors.append(f"scope.redistributionRule must mention {required}")

    grades = index.get("evidenceGrades")
    if not isinstance(grades, dict) or set(grades) != VALID_GRADES:
        errors.append("evidenceGrades must define every supported grade exactly once")
    elif not all(_text(description) for description in grades.values()):
        errors.append("every evidence grade requires a description")

    sources = index.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or len(sources) < 6:
        errors.append("sources must contain at least six source contexts")
        sources = []
    for position, source in enumerate(sources):
        prefix = f"sources[{position}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("id")
        if not _text(source_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif source_id in source_ids:
            errors.append(f"duplicate source id {source_id}")
        else:
            source_ids.add(str(source_id))
            if f"`{source_id}`" not in document:
                errors.append(f"document is missing source id {source_id}")
        for field in ("publisher", "title", "deviceContext"):
            if not _text(source.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if not _https_url(source.get("url")):
            errors.append(f"{prefix}.url must be an https URL")
        if source.get("datePrecision") not in VALID_DATE_PRECISION:
            errors.append(f"{prefix}.datePrecision is invalid")
        if source.get("datePrecision") != "UNKNOWN" and not _text(source.get("firstReportedDate")):
            errors.append(f"{prefix}.firstReportedDate is required when date precision is known")
        build = source.get("buildContext")
        if not isinstance(build, dict) or build.get("status") not in VALID_CONTEXT_STATUS:
            errors.append(f"{prefix}.buildContext is invalid")
        elif build.get("status") == "EXACT" and not _text(build.get("value")):
            errors.append(f"{prefix}.buildContext exact value is required")
        app = source.get("appContext")
        if not isinstance(app, dict) or app.get("status") not in VALID_CONTEXT_STATUS:
            errors.append(f"{prefix}.appContext is invalid")
        else:
            if app.get("status") != "UNKNOWN" and not _text(app.get("name")):
                errors.append(f"{prefix}.appContext name is required")
            if "version" not in app:
                errors.append(f"{prefix}.appContext must record version or UNKNOWN")
        if not _text_list(source.get("limitations")):
            errors.append(f"{prefix}.limitations must be a non-empty text list")

    reports = index.get("reports")
    report_ids: set[str] = set()
    report_topics: set[str] = set()
    referenced_test_ids: set[str] = set()
    if not isinstance(reports, list) or len(reports) < 8:
        errors.append("reports must contain at least eight bounded reports")
        reports = []
    for position, report in enumerate(reports):
        prefix = f"reports[{position}]"
        if not isinstance(report, dict):
            errors.append(f"{prefix} must be an object")
            continue
        report_id = report.get("id")
        if not _text(report_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif report_id in report_ids:
            errors.append(f"duplicate report id {report_id}")
        else:
            report_ids.add(str(report_id))
            if f"`{report_id}`" not in document:
                errors.append(f"document is missing report id {report_id}")
        if report.get("sourceId") not in source_ids:
            errors.append(f"{prefix}.sourceId references unknown source")
        grade = report.get("grade")
        if grade not in VALID_GRADES:
            errors.append(f"{prefix}.grade is invalid")
        topic = report.get("topic")
        if not _text(topic):
            errors.append(f"{prefix}.topic must be non-empty")
        else:
            report_topics.add(str(topic))
        if not _text(report.get("reportedBehavior")):
            errors.append(f"{prefix}.reportedBehavior must be non-empty")
        for field in ("buildContextStatus", "appContextStatus"):
            if report.get(field) not in VALID_CONTEXT_STATUS:
                errors.append(f"{prefix}.{field} is invalid")
        corroborated = report.get("independentCorroboration")
        if not isinstance(corroborated, bool):
            errors.append(f"{prefix}.independentCorroboration must be boolean")
        if grade == "MULTIPLE_INDEPENDENT_REPORTS" and corroborated is not True:
            errors.append(f"{prefix} multiple-report grade requires independent corroboration")
        if grade in {"SECOND_HAND_LEAD", "SINGLE_REPORT"} and corroborated is not False:
            errors.append(f"{prefix} lead/single grade cannot claim independent corroboration")
        if report.get("implementationProof") is not False:
            errors.append(f"{prefix}.implementationProof must be false")
        test_ids = report.get("testIds")
        if not _id_list(test_ids):
            errors.append(f"{prefix}.testIds must be a unique non-empty id list")
        else:
            referenced_test_ids.update(test_ids)
        if not _text_list(report.get("limitations")):
            errors.append(f"{prefix}.limitations must be a non-empty text list")

    missing_topics = REQUIRED_TOPICS - report_topics
    if missing_topics:
        errors.append(f"missing required report topics: {sorted(missing_topics)}")

    tests = index.get("controlledTests")
    test_ids: set[str] = set()
    related_report_ids: set[str] = set()
    if not isinstance(tests, list) or len(tests) < 8:
        errors.append("controlledTests must contain at least eight tests")
        tests = []
    for position, test in enumerate(tests):
        prefix = f"controlledTests[{position}]"
        if not isinstance(test, dict):
            errors.append(f"{prefix} must be an object")
            continue
        test_id = test.get("id")
        if not _text(test_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif test_id in test_ids:
            errors.append(f"duplicate test id {test_id}")
        else:
            test_ids.add(str(test_id))
            if f"`{test_id}`" not in document:
                errors.append(f"document is missing test id {test_id}")
        if not _text(test.get("objective")) or not _text(test.get("decisionRule")):
            errors.append(f"{prefix}.objective and decisionRule must be non-empty")
        if not _text_list(test.get("protocol")) or len(test.get("protocol", [])) < 3:
            errors.append(f"{prefix}.protocol must contain at least three steps")
        if not _text_list(test.get("requiredArtifacts")):
            errors.append(f"{prefix}.requiredArtifacts must be a non-empty text list")
        report_links = test.get("relatedReportIds")
        if not _id_list(report_links):
            errors.append(f"{prefix}.relatedReportIds must be a unique non-empty id list")
        else:
            related_report_ids.update(report_links)

    missing_tests = REQUIRED_TEST_IDS - test_ids
    if missing_tests:
        errors.append(f"missing required controlled tests: {sorted(missing_tests)}")
    unknown_test_links = referenced_test_ids - test_ids
    if unknown_test_links:
        errors.append(f"reports reference unknown tests: {sorted(unknown_test_links)}")
    unknown_report_links = related_report_ids - report_ids
    if unknown_report_links:
        errors.append(f"tests reference unknown reports: {sorted(unknown_report_links)}")
    untested_reports = report_ids - related_report_ids
    if untested_reports:
        errors.append(f"reports without a reverse-linked controlled test: {sorted(untested_reports)}")

    non_claims = index.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 5 or not all(_text(item) for item in non_claims):
        errors.append("nonClaims must contain at least five explicit boundaries")
    else:
        for position, statement in enumerate(non_claims):
            lowered = statement.lower()
            if not any(term in lowered for term in ("does not", "do not", "not prove")):
                errors.append(f"nonClaims[{position}] must explicitly limit interpretation")

    maintenance = index.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if not _text_list(maintenance.get("updateTriggers")):
            errors.append("maintenance.updateTriggers must be a non-empty text list")
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")
        if maintenance.get("validationTool") != "tools/validate-community-camera-evidence.py":
            errors.append("maintenance.validationTool is incorrect")

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
    print("Community camera evidence register is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
