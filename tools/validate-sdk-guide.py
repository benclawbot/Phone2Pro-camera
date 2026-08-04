#!/usr/bin/env python3
"""Validate the replacement-camera SDK guide manifest and documentation."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

MANIFEST_PATH = pathlib.Path("spec/replacement-camera-sdk-guide.v1.json")
GUIDE_PATH = pathlib.Path("docs/REPLACEMENT_CAMERA_SDK.md")
VALID_CONFIDENCE = {"VERIFIED", "PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"}
VALID_STATUS = {
    "VERIFIED_CONTRACT",
    "PARTIALLY_VERIFIED",
    "HYPOTHESIS",
    "EXPERIMENTAL_ADAPTER",
}
VALID_PRODUCTION_USE = {"ENABLED", "ENABLED_WITH_FALLBACK", "DISABLED"}
VALID_EXAMPLE_CLASSIFICATION = {"VERIFIED_INTERFACE", "EXPERIMENTAL_ADAPTER"}
REQUIRED_HEADINGS = {
    "## Evidence and enablement rules",
    "## Build compatibility",
    "## Architecture map",
    "## Verified main camera session",
    "## Verified private metadata plan",
    "## Experimental vendor adapter",
    "## Experimental auxiliary route",
    "## Error and fallback policy",
    "## Contributor workflow",
    "## Required validation",
}
ANCHOR_PATTERN = re.compile(r'<a id="([a-z0-9-]+)"></a>')


def load_manifest(root: pathlib.Path) -> dict[str, Any]:
    return json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))


def validate(
    root: pathlib.Path,
    manifest: dict[str, Any] | None = None,
    guide_text: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if manifest is None:
        try:
            manifest = load_manifest(root)
        except (OSError, json.JSONDecodeError) as error:
            return [f"cannot load {MANIFEST_PATH}: {error}"]
    if guide_text is None:
        try:
            guide_text = (root / GUIDE_PATH).read_text(encoding="utf-8")
        except OSError as error:
            return [f"cannot load {GUIDE_PATH}: {error}"]

    if manifest.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not _text(manifest.get("guideVersion")):
        errors.append("guideVersion must be non-empty")

    device = manifest.get("device")
    if not isinstance(device, dict):
        errors.append("device must be an object")
    else:
        for field in ("marketingName", "codename", "soc"):
            if not _text(device.get(field)):
                errors.append(f"device.{field} must be non-empty")

    build_scopes = manifest.get("buildCompatibility")
    build_ids: set[str] = set()
    if not isinstance(build_scopes, list) or not build_scopes:
        errors.append("buildCompatibility must be a non-empty list")
    else:
        for index, build in enumerate(build_scopes):
            prefix = f"buildCompatibility[{index}]"
            if not isinstance(build, dict):
                errors.append(f"{prefix} must be an object")
                continue
            build_id = build.get("id")
            if not _text(build_id):
                errors.append(f"{prefix}.id must be non-empty")
            elif build_id in build_ids:
                errors.append(f"duplicate build compatibility id {build_id}")
            else:
                build_ids.add(build_id)
            if not _text(build.get("policy")):
                errors.append(f"{prefix}.policy must be non-empty")
            confidence = build.get("confidence")
            if confidence not in VALID_CONFIDENCE:
                errors.append(f"{prefix}.confidence is invalid")
            issue_count = _validate_issue_list(build.get("unknownIssues"), prefix, errors)
            if confidence in {"PARTIALLY_VERIFIED", "HYPOTHESIS", "UNKNOWN"} and issue_count == 0:
                errors.append(f"{prefix} unresolved confidence requires unknownIssues")

    modules = manifest.get("modules")
    module_ids: set[str] = set()
    module_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(modules, list) or not modules:
        errors.append("modules must be a non-empty list")
    else:
        for index, module in enumerate(modules):
            prefix = f"modules[{index}]"
            if not isinstance(module, dict):
                errors.append(f"{prefix} must be an object")
                continue
            module_id = module.get("id")
            if not _text(module_id):
                errors.append(f"{prefix}.id must be non-empty")
            elif module_id in module_ids:
                errors.append(f"duplicate module id {module_id}")
            else:
                module_ids.add(module_id)
                module_by_id[module_id] = module
            status = module.get("status")
            production_use = module.get("productionUse")
            if status not in VALID_STATUS:
                errors.append(f"{prefix}.status is invalid")
            if production_use not in VALID_PRODUCTION_USE:
                errors.append(f"{prefix}.productionUse is invalid")
            if status == "EXPERIMENTAL_ADAPTER" and production_use != "DISABLED":
                errors.append(f"{prefix} experimental adapter must be DISABLED")
            if module.get("buildScope") not in build_ids:
                errors.append(f"{prefix}.buildScope references an unknown build")
            if not _text(module.get("fallback")):
                errors.append(f"{prefix}.fallback must be non-empty")
            _validate_paths(root, module.get("entryPoints"), f"{prefix}.entryPoints", errors)
            _validate_paths(root, module.get("documentation"), f"{prefix}.documentation", errors)
            issue_count = _validate_issue_list(module.get("unknownIssues"), prefix, errors)
            if status in {"PARTIALLY_VERIFIED", "HYPOTHESIS", "EXPERIMENTAL_ADAPTER"} and issue_count == 0:
                errors.append(f"{prefix} unresolved module requires unknownIssues")

    anchors = set(ANCHOR_PATTERN.findall(guide_text))
    examples = manifest.get("examples")
    example_ids: set[str] = set()
    if not isinstance(examples, list) or not examples:
        errors.append("examples must be a non-empty list")
    else:
        for index, example in enumerate(examples):
            prefix = f"examples[{index}]"
            if not isinstance(example, dict):
                errors.append(f"{prefix} must be an object")
                continue
            example_id = example.get("id")
            if not _text(example_id):
                errors.append(f"{prefix}.id must be non-empty")
            elif example_id in example_ids:
                errors.append(f"duplicate example id {example_id}")
            else:
                example_ids.add(example_id)
            classification = example.get("classification")
            if classification not in VALID_EXAMPLE_CLASSIFICATION:
                errors.append(f"{prefix}.classification is invalid")
            anchor = example.get("guideAnchor")
            if anchor not in anchors:
                errors.append(f"{prefix}.guideAnchor {anchor!r} is missing from the guide")
            if example.get("buildScope") not in build_ids:
                errors.append(f"{prefix}.buildScope references an unknown build")
            if not _text(example.get("fallback")):
                errors.append(f"{prefix}.fallback must be non-empty")

            uses_modules = example.get("usesModules")
            used: list[dict[str, Any]] = []
            if not isinstance(uses_modules, list) or not uses_modules:
                errors.append(f"{prefix}.usesModules must be a non-empty list")
            else:
                for module_id in uses_modules:
                    if module_id not in module_by_id:
                        errors.append(f"{prefix}.usesModules references unknown module {module_id!r}")
                    else:
                        used.append(module_by_id[module_id])
            issue_count = _validate_issue_list(example.get("unknownIssues"), prefix, errors)
            uses_experimental = any(
                module.get("status") == "EXPERIMENTAL_ADAPTER" for module in used
            )
            if classification == "VERIFIED_INTERFACE" and uses_experimental:
                errors.append(f"{prefix} verified example cannot use an experimental module")
            if classification == "EXPERIMENTAL_ADAPTER":
                if not uses_experimental:
                    errors.append(f"{prefix} experimental example must use an experimental module")
                if issue_count == 0:
                    errors.append(f"{prefix} experimental example requires unknownIssues")
                marker = "Classification: EXPERIMENTAL ADAPTER"
                if anchor in anchors and marker not in _anchor_section(guide_text, anchor):
                    errors.append(f"{prefix} guide section lacks experimental classification marker")
            elif anchor in anchors:
                marker = "Classification: VERIFIED INTERFACE"
                if marker not in _anchor_section(guide_text, anchor):
                    errors.append(f"{prefix} guide section lacks verified classification marker")

    for heading in REQUIRED_HEADINGS:
        if heading not in guide_text:
            errors.append(f"guide is missing required heading: {heading}")

    prohibited_unmarked = ("com.mediatek.", "com.nothing.")
    verified_sections = [
        _anchor_section(guide_text, "verified-main-camera-session"),
        _anchor_section(guide_text, "verified-private-metadata-plan"),
    ]
    for key_prefix in prohibited_unmarked:
        if any(key_prefix in section for section in verified_sections):
            errors.append(f"verified guide example contains vendor key prefix {key_prefix}")

    return errors


def _validate_paths(
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
            errors.append(f"{name} entries must be non-empty paths")
            continue
        if value in seen:
            errors.append(f"{name} contains duplicate path {value}")
            continue
        seen.add(value)
        path = pathlib.PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{name} contains non-relative path {value}")
        elif not (root / value).is_file():
            errors.append(f"{name} path does not exist: {value}")


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


def _anchor_section(guide_text: str, anchor: str) -> str:
    marker = f'<a id="{anchor}"></a>'
    start = guide_text.find(marker)
    if start < 0:
        return ""
    next_heading = guide_text.find("\n## ", start + len(marker))
    if next_heading < 0:
        return guide_text[start:]
    return guide_text[start:next_heading]


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
        f"Validated {len(manifest['modules'])} SDK modules and "
        f"{len(manifest['examples'])} examples for {manifest['guideVersion']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
