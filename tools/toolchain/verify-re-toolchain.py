#!/usr/bin/env python3
"""Verify a host against the pinned reverse-engineering toolchain lock."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any


class LockError(ValueError):
    """Raised when the toolchain lock is malformed."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe installed reverse-engineering tools against the project lockfile."
    )
    parser.add_argument(
        "--lock",
        default=str(
            Path(__file__).resolve().parents[2]
            / "config"
            / "reverse-engineering-toolchain.json"
        ),
        help="toolchain lock JSON",
    )
    parser.add_argument(
        "--profile",
        help="profile to verify; defaults to defaultProfile in the lock",
    )
    parser.add_argument(
        "--tool",
        action="append",
        default=[],
        metavar="ID=COMMAND",
        help="override a tool command; may be repeated",
    )
    parser.add_argument(
        "--include-host-utilities",
        action="store_true",
        help="also check the hostUtilities command list",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return status 1 when a required selected tool is missing or mismatched",
    )
    parser.add_argument("--json", dest="json_path", help="write JSON report to a file")
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="per-command timeout in seconds (default: 15)",
    )
    return parser


def load_lock(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LockError(f"unable to read lock {path}: {error}") from error
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise LockError("unsupported or missing schemaVersion")
    profiles = data.get("profiles")
    tools = data.get("tools")
    if not isinstance(profiles, dict) or not profiles:
        raise LockError("profiles must be a non-empty object")
    if not isinstance(tools, list) or not tools:
        raise LockError("tools must be a non-empty array")
    seen: set[str] = set()
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise LockError(f"tools[{index}] must be an object")
        tool_id = tool.get("id")
        if not isinstance(tool_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", tool_id):
            raise LockError(f"tools[{index}].id is invalid")
        if tool_id in seen:
            raise LockError(f"duplicate tool id: {tool_id}")
        seen.add(tool_id)
        version = tool.get("version")
        tool_profiles = tool.get("profiles")
        probe = tool.get("probe")
        if not isinstance(version, str) or not version:
            raise LockError(f"{tool_id}: version must be a non-empty string")
        if not isinstance(tool_profiles, list) or not tool_profiles:
            raise LockError(f"{tool_id}: profiles must be a non-empty array")
        unknown_profiles = sorted(set(tool_profiles) - set(profiles))
        if unknown_profiles:
            raise LockError(f"{tool_id}: unknown profiles: {unknown_profiles}")
        if not isinstance(probe, dict) or probe.get("type") not in {
            "command",
            "pythonDistribution",
        }:
            raise LockError(f"{tool_id}: unsupported probe")
        if probe["type"] == "command":
            if not isinstance(probe.get("command"), str) or not probe["command"]:
                raise LockError(f"{tool_id}: command probe requires command")
            if not isinstance(probe.get("args", []), list):
                raise LockError(f"{tool_id}: probe args must be an array")
            pattern = probe.get("versionRegex")
            if not isinstance(pattern, str):
                raise LockError(f"{tool_id}: command probe requires versionRegex")
            try:
                re.compile(pattern)
            except re.error as error:
                raise LockError(f"{tool_id}: invalid versionRegex: {error}") from error
        else:
            if not isinstance(probe.get("distribution"), str):
                raise LockError(f"{tool_id}: pythonDistribution requires distribution")
    return data


def parse_overrides(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise LockError(f"tool override must use ID=COMMAND: {value}")
        tool_id, command = value.split("=", 1)
        if not tool_id or not command:
            raise LockError(f"tool override must use ID=COMMAND: {value}")
        overrides[tool_id] = command
    return overrides


def override_environment_name(tool_id: str) -> str:
    return "RE_TOOL_" + re.sub(r"[^A-Z0-9]", "_", tool_id.upper())


def resolve_command(tool: dict[str, Any], overrides: dict[str, str]) -> list[str]:
    tool_id = tool["id"]
    configured = overrides.get(tool_id) or os.environ.get(override_environment_name(tool_id))
    if configured:
        return shlex.split(configured)
    probe = tool["probe"]
    return [probe.get("command", "python3")]


def run_command(argv: list[str], timeout: float) -> tuple[int, str]:
    completed = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return completed.returncode, output


def probe_command(
    tool: dict[str, Any], overrides: dict[str, str], timeout: float
) -> dict[str, Any]:
    probe = tool["probe"]
    command = resolve_command(tool, overrides)
    executable = command[0]
    if "/" not in executable and shutil.which(executable) is None:
        return {
            "status": "missing",
            "command": command,
            "message": f"executable not found: {executable}",
        }
    if "/" in executable and not Path(executable).is_file():
        return {
            "status": "missing",
            "command": command,
            "message": f"executable not found: {executable}",
        }
    argv = command + [str(value) for value in probe.get("args", [])]
    try:
        return_code, output = run_command(argv, timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "status": "error",
            "command": argv,
            "message": str(error),
        }
    if return_code != 0:
        return {
            "status": "error",
            "command": argv,
            "returnCode": return_code,
            "output": output,
            "message": "version command failed",
        }
    match = re.search(probe["versionRegex"], output, flags=re.MULTILINE)
    if not match:
        return {
            "status": "mismatch",
            "command": argv,
            "output": output,
            "message": "version output did not match the locked pattern",
        }
    group = int(tool.get("versionGroup", 1))
    try:
        detected = match.group(group)
    except IndexError as error:
        return {
            "status": "error",
            "command": argv,
            "output": output,
            "message": f"versionGroup {group} is absent from the pattern: {error}",
        }
    return {
        "status": "pass" if detected == tool["version"] else "mismatch",
        "command": argv,
        "detectedVersion": detected,
        "output": output,
        "message": (
            "locked version detected"
            if detected == tool["version"]
            else f"expected {tool['version']}, detected {detected}"
        ),
    }


def probe_python_distribution(
    tool: dict[str, Any], overrides: dict[str, str], timeout: float
) -> dict[str, Any]:
    python_tool = {
        "id": "python",
        "probe": {"command": "python3"},
    }
    python_command = resolve_command(python_tool, overrides)
    executable = python_command[0]
    if "/" not in executable and shutil.which(executable) is None:
        return {
            "status": "missing",
            "command": python_command,
            "message": f"Python executable not found: {executable}",
        }
    distribution = tool["probe"]["distribution"]
    script = (
        "import importlib.metadata,sys;"
        f"sys.stdout.write(importlib.metadata.version({distribution!r}))"
    )
    argv = python_command + ["-c", script]
    try:
        return_code, output = run_command(argv, timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "error", "command": argv, "message": str(error)}
    if return_code != 0:
        missing = "PackageNotFoundError" in output
        return {
            "status": "missing" if missing else "error",
            "command": argv,
            "returnCode": return_code,
            "output": output,
            "message": (
                f"Python distribution not installed: {distribution}"
                if missing
                else "Python distribution probe failed"
            ),
        }
    detected = output.strip()
    return {
        "status": "pass" if detected == tool["version"] else "mismatch",
        "command": argv,
        "detectedVersion": detected,
        "message": (
            "locked version detected"
            if detected == tool["version"]
            else f"expected {tool['version']}, detected {detected}"
        ),
    }


def verify_tool(
    tool: dict[str, Any], overrides: dict[str, str], timeout: float
) -> dict[str, Any]:
    probe_type = tool["probe"]["type"]
    if probe_type == "command":
        result = probe_command(tool, overrides, timeout)
    else:
        result = probe_python_distribution(tool, overrides, timeout)
    return {
        "id": tool["id"],
        "displayName": tool.get("displayName", tool["id"]),
        "expectedVersion": tool["version"],
        "required": bool(tool.get("required", False)),
        **result,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"Reverse-engineering toolchain profile: {report['profile']}",
        f"Lock: {report['lockPath']}",
        "",
    ]
    for result in report["results"]:
        status = result["status"].upper().ljust(8)
        detected = result.get("detectedVersion", "-")
        lines.append(
            f"{status} {result['id']}: expected={result['expectedVersion']} detected={detected}"
        )
        if result["status"] != "pass":
            lines.append(f"         {result.get('message', '')}")
    if report["hostUtilities"]:
        lines.append("")
        for utility in report["hostUtilities"]:
            lines.append(
                f"{'PASS' if utility['available'] else 'MISSING'} host utility: {utility['command']}"
            )
    summary = report["summary"]
    lines.extend(
        [
            "",
            "Summary: "
            + ", ".join(f"{key}={value}" for key, value in summary.items()),
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        lock_path = Path(args.lock).resolve()
        lock = load_lock(lock_path)
        overrides = parse_overrides(args.tool)
        profile = args.profile or lock.get("defaultProfile")
        if profile not in lock["profiles"]:
            raise LockError(f"unknown profile: {profile}")
        known_ids = {tool["id"] for tool in lock["tools"]}
        unknown_overrides = sorted(set(overrides) - known_ids)
        if unknown_overrides:
            raise LockError(f"unknown tool overrides: {unknown_overrides}")
    except LockError as error:
        print(f"toolchain verification failed: {error}", file=sys.stderr)
        return 2

    selected = [tool for tool in lock["tools"] if profile in tool["profiles"]]
    results = [verify_tool(tool, overrides, args.timeout) for tool in selected]
    host_utilities = []
    if args.include_host_utilities:
        for command in lock.get("hostUtilities", []):
            host_utilities.append(
                {"command": command, "available": shutil.which(command) is not None}
            )

    summary = {status: 0 for status in ("pass", "missing", "mismatch", "error")}
    for result in results:
        summary[result["status"]] += 1
    report = {
        "schemaVersion": 1,
        "lockPath": str(lock_path),
        "lockVerifiedAtUtc": lock.get("verifiedAtUtc"),
        "profile": profile,
        "results": results,
        "hostUtilities": host_utilities,
        "summary": summary,
    }
    rendered_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_path:
        output = Path(args.json_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered_json, encoding="utf-8")
    sys.stdout.write(render_text(report))

    strict_failure = any(
        result["required"] and result["status"] != "pass" for result in results
    )
    if args.include_host_utilities:
        strict_failure = strict_failure or any(
            not utility["available"] for utility in host_utilities
        )
    return 1 if args.strict and strict_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
