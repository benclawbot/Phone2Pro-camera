#!/usr/bin/env python3
"""Validate the revision-pinned public MediaTek camera cross-reference."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

INDEX_PATH = pathlib.Path("research/mediatek-public-camera-cross-reference.v1.json")
DOCUMENT_PATH = pathlib.Path("docs/MEDIATEK_PUBLIC_CAMERA_CROSS_REFERENCE.md")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._+/@-]+$")
VALID_RELATIONS = {
    "NAME_MATCH",
    "TYPE_OR_ENUM_ANALOGUE",
    "FLOW_ANALOGUE",
    "STRUCTURAL_ANALOGUE",
}
REQUIRED_SOURCE_IDS = {
    "chromeos-platform-camera-head-2026-01",
    "chromeos-mtkcam-content-2021",
    "chromeos-mtkcam-request-2023",
    "chromeos-mtkcam-pipeline-2023",
    "aosp-system-media-android16",
    "nothing-galaga-kernel-2026-04",
}
REQUIRED_FAMILY_GROUPS = (
    {"mediatek.mfnrfeature", "MFNR/AIS"},
    {"mediatek.hdrfeature", "HDR"},
    {"ZSL/postview/prerelease"},
    {"ISP tuning/reprocess"},
    {"mediatek.insensorzoomfeature", "in-sensor zoom"},
    {"mediatek.seamlessfeature", "seamless"},
    {"mediatek.cameraflex", "CameraFlex/multicam"},
    {"mediatek.multicamfeature", "logical-camera"},
    {"mediatek.eisfeature", "EIS"},
    {"mediatek.3afeature", "3A IPC"},
    {"nothing.camera.eis", "nothing.camera.soisParams"},
)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _safe_path(value: Any) -> bool:
    return (
        _text(value)
        and not str(value).startswith("/")
        and ".." not in pathlib.PurePosixPath(str(value)).parts
        and bool(SAFE_PATH.fullmatch(str(value)))
    )


def _issue_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, int) and item > 0 for item in value)
        and len(set(value)) == len(value)
    )


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
        for field in ("marketingName", "model", "codename", "soc", "observedBuildId", "observedFingerprintEvidence"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")
        if device.get("codename") != "Galaga" or device.get("soc") != "MT6878":
            errors.append("device must identify Galaga MT6878")
        evidence = device.get("observedFingerprintEvidence")
        if _text(evidence) and not (root / str(evidence)).is_file():
            errors.append("device.observedFingerprintEvidence must reference an existing file")

    scope = index.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        for field in ("objective", "interpretationRule", "targetInventory", "targetPriorityMap"):
            if not _text(scope.get(field)):
                errors.append(f"scope.{field} must be non-empty")
        if scope.get("relatedIssue") != 78:
            errors.append("scope.relatedIssue must be 78")
        for field in ("targetInventory", "targetPriorityMap"):
            path = scope.get(field)
            if _text(path) and not (root / str(path)).is_file():
                errors.append(f"scope.{field} must reference an existing file")
        rule = str(scope.get("interpretationRule", "")).lower()
        if "no public source" not in rule or "exact" not in rule:
            errors.append("scope.interpretationRule must explicitly reject exact equivalence")

    sources = index.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty list")
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
        for field in ("kind", "repository", "revisionType", "url", "platform", "scope", "targetRelation"):
            if not _text(source.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        revision = source.get("revision")
        if not isinstance(revision, str) or not SHA40.fullmatch(revision):
            errors.append(f"{prefix}.revision must be a lowercase 40-character SHA")
        url = source.get("url")
        if _text(url):
            if not str(url).startswith("https://"):
                errors.append(f"{prefix}.url must use https")
            if isinstance(revision, str) and revision not in str(url):
                errors.append(f"{prefix}.url must include the pinned revision")
        relation = str(source.get("targetRelation", "")).lower()
        if not any(word in relation for word in ("exact", "different", "older", "omit", "analogue", "does not")):
            errors.append(f"{prefix}.targetRelation must state a limiting platform relation")

    missing_sources = REQUIRED_SOURCE_IDS - source_ids
    if missing_sources:
        errors.append(f"missing required source ids: {sorted(missing_sources)}")

    matches = index.get("matches")
    match_ids: set[str] = set()
    covered_families: set[str] = set()
    if not isinstance(matches, list) or len(matches) < 10:
        errors.append("matches must contain at least ten indexed analogues")
        matches = []
    for position, match in enumerate(matches):
        prefix = f"matches[{position}]"
        if not isinstance(match, dict):
            errors.append(f"{prefix} must be an object")
            continue
        match_id = match.get("id")
        if not _text(match_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif match_id in match_ids:
            errors.append(f"duplicate match id {match_id}")
        else:
            match_ids.add(str(match_id))
            if f"`{match_id}`" not in document:
                errors.append(f"document is missing match id {match_id}")
        if match.get("sourceId") not in source_ids:
            errors.append(f"{prefix}.sourceId references unknown source")
        if match.get("relation") not in VALID_RELATIONS:
            errors.append(f"{prefix}.relation is invalid")
        if match.get("equivalenceClaimed") is not False:
            errors.append(f"{prefix}.equivalenceClaimed must be false")
        families = match.get("targetFamilies")
        if not _text_list(families):
            errors.append(f"{prefix}.targetFamilies must be a non-empty text list")
        else:
            covered_families.update(families)
        if not isinstance(match.get("paths"), list) or not match["paths"] or not all(_safe_path(path) for path in match["paths"]):
            errors.append(f"{prefix}.paths must contain safe repository-relative paths")
        if not _text_list(match.get("symbols")):
            errors.append(f"{prefix}.symbols must be a non-empty text list")
        for field in ("finding", "platformDifference"):
            if not _text(match.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if "equivalent" in str(match.get("finding", "")).lower():
            errors.append(f"{prefix}.finding must not claim equivalence")

    for group in REQUIRED_FAMILY_GROUPS:
        if not (group & covered_families):
            errors.append(f"missing required family coverage: {sorted(group)}")

    differences = index.get("platformDifferences")
    difference_ids: set[str] = set()
    if not isinstance(differences, list) or len(differences) < 5:
        errors.append("platformDifferences must contain at least five entries")
        differences = []
    for position, difference in enumerate(differences):
        prefix = f"platformDifferences[{position}]"
        if not isinstance(difference, dict):
            errors.append(f"{prefix} must be an object")
            continue
        difference_id = difference.get("id")
        if not _text(difference_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif difference_id in difference_ids:
            errors.append(f"duplicate platform difference id {difference_id}")
        else:
            difference_ids.add(str(difference_id))
            if f"`{difference_id}`" not in document:
                errors.append(f"document is missing platform difference id {difference_id}")
        if not _text(difference.get("statement")) or not _text(difference.get("consequence")):
            errors.append(f"{prefix}.statement and consequence must be non-empty")

    hypotheses = index.get("hypotheses")
    hypothesis_ids: set[str] = set()
    if not isinstance(hypotheses, list) or len(hypotheses) < 6:
        errors.append("hypotheses must contain at least six testable entries")
        hypotheses = []
    for position, hypothesis in enumerate(hypotheses):
        prefix = f"hypotheses[{position}]"
        if not isinstance(hypothesis, dict):
            errors.append(f"{prefix} must be an object")
            continue
        hypothesis_id = hypothesis.get("id")
        if not _text(hypothesis_id):
            errors.append(f"{prefix}.id must be non-empty")
        elif hypothesis_id in hypothesis_ids:
            errors.append(f"duplicate hypothesis id {hypothesis_id}")
        else:
            hypothesis_ids.add(str(hypothesis_id))
            if f"`{hypothesis_id}`" not in document:
                errors.append(f"document is missing hypothesis id {hypothesis_id}")
        if not _text_list(hypothesis.get("targetFamilies")):
            errors.append(f"{prefix}.targetFamilies must be a non-empty text list")
        evidence_ids = hypothesis.get("evidenceMatchIds")
        if not _text_list(evidence_ids):
            errors.append(f"{prefix}.evidenceMatchIds must be a non-empty text list")
        else:
            unknown = set(evidence_ids) - match_ids
            if unknown:
                errors.append(f"{prefix}.evidenceMatchIds references unknown matches: {sorted(unknown)}")
        for field in ("claim", "testProtocol", "falsifier"):
            if not _text(hypothesis.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if not _text_list(hypothesis.get("expectedObservations")):
            errors.append(f"{prefix}.expectedObservations must be a non-empty text list")
        if not _issue_list(hypothesis.get("relatedIssues")):
            errors.append(f"{prefix}.relatedIssues must be a unique positive-integer list")

    non_claims = index.get("nonClaims")
    if not isinstance(non_claims, list) or len(non_claims) < 5 or not all(_text(item) for item in non_claims):
        errors.append("nonClaims must contain at least five explicit boundaries")
    else:
        for position, statement in enumerate(non_claims):
            if not any(word in statement.lower() for word in ("does not", "not treated", "do not", "does not authorize")):
                errors.append(f"nonClaims[{position}] must explicitly limit interpretation")

    maintenance = index.get("maintenance")
    if not isinstance(maintenance, dict):
        errors.append("maintenance must be an object")
    else:
        if not _text_list(maintenance.get("updateTriggers")):
            errors.append("maintenance.updateTriggers must be a non-empty text list")
        if maintenance.get("validationTool") != "tools/validate-mediatek-public-cross-reference.py":
            errors.append("maintenance.validationTool is incorrect")
        if maintenance.get("document") != str(DOCUMENT_PATH):
            errors.append("maintenance.document is incorrect")

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
    print("MediaTek public camera cross-reference is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
