#!/usr/bin/env python3
"""Normalize and compare read-only camera authorization evidence bundles.

The analyzer consumes output from ``capture-camera-authorization.sh``. It never
assumes that a permission, package flag, SELinux domain, or allowlist entry
causes successful camera access. It reports observed differences and identifies
the first unresolved authorization layer that a follow-up experiment should
exercise.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

PERMISSION_CAMERA = "android.permission.CAMERA"
PERMISSION_SYSTEM_CAMERA = "android.permission.SYSTEM_CAMERA"
COMMAND_EXIT_RE = re.compile(r"^# command_exit_code:\s*(\d+)\s*$", re.MULTILINE)
UID_PATTERNS = (
    re.compile(r"\buid:(\d+)\b"),
    re.compile(r"\buserId=(\d+)\b"),
    re.compile(r"\buid=(\d+)\b"),
)
APP_OP_RE = re.compile(
    r"(?im)^\s*(?:android:)?CAMERA\s*:\s*(allow|deny|ignore|foreground|default)\b"
)
SELINUX_RE = re.compile(r"\bu:r:[A-Za-z0-9_]+:s0(?:[:A-Za-z0-9_,.-]+)?\b")


@dataclass(frozen=True)
class CommandText:
    text: str
    exit_code: int | None
    exists: bool

    @property
    def successful(self) -> bool:
        return self.exists and (self.exit_code is None or self.exit_code == 0)


@dataclass
class PackageObservation:
    role: str
    package: str
    directory: str
    camera_permission: str
    system_camera_permission: str
    camera_requested: bool | None
    system_camera_requested: bool | None
    camera_app_op: str
    uid: int | None
    install_partition: str
    privileged_install: bool | None
    system_flag: bool | None
    privileged_flag: bool | None
    privapp_allowlist_system_camera: bool | None
    privapp_denylist_system_camera: bool | None
    selinux_domains: list[str]
    process_observed: bool
    role_service_mentions: bool | None
    source_files: list[str]


class AnalysisError(ValueError):
    """Raised when a bundle cannot be analyzed safely."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare stock and ordinary-app camera authorization evidence."
    )
    parser.add_argument(
        "input",
        help="capture run directory or a parent containing timestamped runs",
    )
    parser.add_argument("--json", dest="json_path", help="write JSON report")
    parser.add_argument("--markdown", dest="markdown_path", help="write Markdown report")
    parser.add_argument("--stock-role", default="stock", help="stock package role prefix")
    parser.add_argument(
        "--ordinary-role",
        default="replacement",
        help="ordinary comparison package role prefix",
    )
    return parser.parse_args(argv)


def select_run(path: Path) -> Path:
    if (path / "manifest.yaml").is_file() and (path / "packages").is_dir():
        return path
    candidates = sorted(
        child
        for child in path.iterdir()
        if child.is_dir()
        and (child / "manifest.yaml").is_file()
        and (child / "packages").is_dir()
    )
    if not candidates:
        raise AnalysisError(f"no camera authorization capture found under {path}")
    return candidates[-1]


def read_command(path: Path) -> CommandText:
    if not path.is_file():
        return CommandText("", None, False)
    text = path.read_text(encoding="utf-8", errors="replace")
    match = COMMAND_EXIT_RE.search(text)
    exit_code = int(match.group(1)) if match else None
    return CommandText(text, exit_code, True)


def payload(command: CommandText) -> str:
    lines = command.text.splitlines()
    if lines and lines[0].startswith("# command:"):
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(
        line for line in lines if not line.startswith("# command_exit_code:")
    ).strip()


def permission_state(command: CommandText) -> str:
    if not command.successful:
        return "UNKNOWN"
    value = payload(command).strip().lower()
    if re.search(r"(^|\s)granted($|\s)", value):
        return "GRANTED"
    if re.search(r"(^|\s)denied($|\s)", value):
        return "DENIED"
    return "UNKNOWN"


def requested_permission(command: CommandText, permission: str) -> bool | None:
    if not command.successful:
        return None
    return permission in payload(command)


def camera_app_op(command: CommandText) -> str:
    if not command.successful:
        return "UNKNOWN"
    match = APP_OP_RE.search(payload(command))
    if not match:
        return "UNKNOWN"
    return match.group(1).upper()


def parse_uid(commands: Iterable[CommandText]) -> int | None:
    for command in commands:
        if not command.successful:
            continue
        text = payload(command)
        for pattern in UID_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
    return None


def install_characteristics(command: CommandText) -> tuple[str, bool | None]:
    if not command.successful:
        return "UNKNOWN", None
    paths = re.findall(r"(?:package:)?(/[A-Za-z0-9_./@+-]+)", payload(command))
    if not paths:
        return "UNKNOWN", None
    path = paths[0]
    if path.startswith("/system_ext/"):
        partition = "SYSTEM_EXT"
    elif path.startswith("/product/"):
        partition = "PRODUCT"
    elif path.startswith("/vendor/"):
        partition = "VENDOR"
    elif path.startswith("/odm/"):
        partition = "ODM"
    elif path.startswith("/system/"):
        partition = "SYSTEM"
    elif path.startswith("/data/"):
        partition = "DATA"
    else:
        partition = "OTHER"
    return partition, "/priv-app/" in path


def package_flags(command: CommandText) -> tuple[bool | None, bool | None]:
    if not command.successful:
        return None, None
    text = payload(command)
    flag_blocks = " ".join(
        match.group(1)
        for match in re.finditer(r"(?:pkgFlags|privateFlags)=\[([^]]*)\]", text)
    )
    if not flag_blocks:
        return None, None
    tokens = {token.upper() for token in re.split(r"[\s,|]+", flag_blocks) if token}
    system = "SYSTEM" in tokens
    privileged = "PRIVILEGED" in tokens or "PRIVATE_FLAG_PRIVILEGED" in tokens
    return system, privileged


def list_membership(command: CommandText, value: str) -> bool | None:
    if not command.successful:
        return None
    return value in payload(command)


def find_role_service_files(device_dir: Path) -> list[Path]:
    names = (
        "role-service.txt",
        "roles.txt",
        "role-holders.txt",
        "cmd-role.txt",
    )
    return [device_dir / name for name in names if (device_dir / name).is_file()]


def analyze_package(run: Path, directory: Path) -> PackageObservation:
    role, separator, safe_package = directory.name.partition("-")
    if not separator or not safe_package:
        raise AnalysisError(f"invalid package evidence directory: {directory.name}")

    summary = read_command(directory / "summary.txt")
    package_match = re.search(r"(?m)^package=([^\s]+)$", summary.text)
    package = package_match.group(1) if package_match else safe_package.replace("_", ".")

    dumpsys = read_command(directory / "dumpsys-package.txt")
    package_uid = read_command(directory / "package-uid.txt")
    package_path = read_command(directory / "package-path.txt")
    appops = read_command(directory / "appops.txt")
    camera_check = read_command(directory / "check-camera-permission.txt")
    system_camera_check = read_command(directory / "check-system-camera-permission.txt")
    allowlist = read_command(directory / "privapp-permissions.txt")
    denylist = read_command(directory / "privapp-deny-permissions.txt")

    partition, privileged_install = install_characteristics(package_path)
    system_flag, privileged_flag = package_flags(dumpsys)

    process_contexts = read_command(run / "device" / "process-contexts.txt")
    matching_process_lines = [
        line
        for line in payload(process_contexts).splitlines()
        if package in line
    ] if process_contexts.successful else []
    domains = sorted({
        match.group(0)
        for line in matching_process_lines
        for match in SELINUX_RE.finditer(line)
    })

    role_files = find_role_service_files(run / "device")
    if not role_files:
        role_mentions: bool | None = None
    else:
        role_mentions = any(
            command.successful and package in payload(command)
            for command in (read_command(path) for path in role_files)
        )

    source_files = sorted(
        path.relative_to(run).as_posix()
        for path in directory.iterdir()
        if path.is_file()
    )
    if process_contexts.exists:
        source_files.append("device/process-contexts.txt")
    source_files.extend(path.relative_to(run).as_posix() for path in role_files)

    return PackageObservation(
        role=role,
        package=package,
        directory=directory.relative_to(run).as_posix(),
        camera_permission=permission_state(camera_check),
        system_camera_permission=permission_state(system_camera_check),
        camera_requested=requested_permission(dumpsys, PERMISSION_CAMERA),
        system_camera_requested=requested_permission(dumpsys, PERMISSION_SYSTEM_CAMERA),
        camera_app_op=camera_app_op(appops),
        uid=parse_uid((package_uid, dumpsys)),
        install_partition=partition,
        privileged_install=privileged_install,
        system_flag=system_flag,
        privileged_flag=privileged_flag,
        privapp_allowlist_system_camera=list_membership(allowlist, PERMISSION_SYSTEM_CAMERA),
        privapp_denylist_system_camera=list_membership(denylist, PERMISSION_SYSTEM_CAMERA),
        selinux_domains=domains,
        process_observed=bool(matching_process_lines),
        role_service_mentions=role_mentions,
        source_files=sorted(set(source_files)),
    )


def finding(
    finding_id: str,
    classification: str,
    statement: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "classification": classification,
        "statement": statement,
        "evidence": evidence,
    }


def compare(stock: PackageObservation, ordinary: PackageObservation) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    if stock.system_camera_permission == "GRANTED" and ordinary.system_camera_permission == "DENIED":
        findings.append(finding(
            "stock-only-system-camera-grant",
            "VERIFIED",
            "The capture records SYSTEM_CAMERA granted for the stock package and denied for the ordinary package.",
            [
                f"{stock.directory}/check-system-camera-permission.txt",
                f"{ordinary.directory}/check-system-camera-permission.txt",
            ],
        ))

    if stock.privapp_allowlist_system_camera is True and ordinary.privapp_allowlist_system_camera is False:
        findings.append(finding(
            "privapp-allowlist-difference",
            "VERIFIED",
            "SYSTEM_CAMERA appears in the stock package privapp grant output and not in the ordinary package output.",
            [
                f"{stock.directory}/privapp-permissions.txt",
                f"{ordinary.directory}/privapp-permissions.txt",
            ],
        ))

    if stock.install_partition != "UNKNOWN" and ordinary.install_partition != "UNKNOWN" and stock.install_partition != ordinary.install_partition:
        findings.append(finding(
            "install-partition-difference",
            "VERIFIED",
            f"The stock package is installed on {stock.install_partition}; the ordinary package is installed on {ordinary.install_partition}.",
            [
                f"{stock.directory}/package-path.txt",
                f"{ordinary.directory}/package-path.txt",
            ],
        ))

    if stock.selinux_domains and ordinary.selinux_domains and stock.selinux_domains != ordinary.selinux_domains:
        findings.append(finding(
            "selinux-domain-difference",
            "VERIFIED",
            "The running stock and ordinary packages were observed in different SELinux domains.",
            ["device/process-contexts.txt"],
        ))

    if ordinary.camera_permission == "DENIED":
        primary_gate = "MISSING_CAMERA_PERMISSION"
        primary_statement = "The ordinary package lacks the normal CAMERA grant."
        primary_classification = "VERIFIED"
    elif ordinary.camera_permission == "UNKNOWN":
        primary_gate = "CAMERA_PERMISSION_UNKNOWN"
        primary_statement = "The normal CAMERA grant could not be established from the capture."
        primary_classification = "UNKNOWN"
    elif ordinary.system_camera_permission == "DENIED":
        primary_gate = "MISSING_SYSTEM_CAMERA_GRANT"
        primary_statement = (
            "The ordinary package has CAMERA but lacks SYSTEM_CAMERA; this is a sufficient observed permission-layer blocker for system-camera access."
        )
        primary_classification = "VERIFIED"
    elif ordinary.system_camera_permission == "UNKNOWN":
        primary_gate = "SYSTEM_CAMERA_GRANT_UNKNOWN"
        primary_statement = "The SYSTEM_CAMERA grant could not be established from the capture."
        primary_classification = "UNKNOWN"
    elif ordinary.camera_app_op in {"DENY", "IGNORE"}:
        primary_gate = "CAMERA_APPOP_DENIED"
        primary_statement = "The ordinary package has both permission grants, but the CAMERA AppOp is not allowed."
        primary_classification = "VERIFIED"
    elif ordinary.camera_app_op == "UNKNOWN":
        primary_gate = "CAMERA_APPOP_UNKNOWN"
        primary_statement = "Both permission grants are recorded, but the CAMERA AppOp could not be established."
        primary_classification = "UNKNOWN"
    else:
        primary_gate = "PERMISSION_PARITY_DEEPER_GATE_REQUIRED"
        primary_statement = (
            "The ordinary package has CAMERA, SYSTEM_CAMERA, and a non-denied CAMERA AppOp in this capture; endpoint failure would require inspection of package allowlisting, UID/service checks, SELinux, provider, or HAL policy."
        )
        primary_classification = "PARTIALLY_VERIFIED"

    findings.append(finding(
        "ordinary-primary-gate",
        primary_classification,
        primary_statement,
        sorted(set(
            [
                f"{ordinary.directory}/check-camera-permission.txt",
                f"{ordinary.directory}/check-system-camera-permission.txt",
                f"{ordinary.directory}/appops.txt",
            ]
        )),
    ))

    next_checks: list[str] = []
    if primary_gate in {"MISSING_CAMERA_PERMISSION", "MISSING_SYSTEM_CAMERA_GRANT"}:
        next_checks.append(
            "Do not attribute an ordinary-build endpoint failure to CameraService, SELinux, or the HAL until a lawfully authorized comparison build reaches permission parity."
        )
    else:
        next_checks.extend([
            "Run controlled enumeration, characteristics, open, session, and request probes while recording exact errors and caller identity.",
            "Correlate CameraService rejection logs with the package UID and SELinux domain.",
        ])
    if not ordinary.selinux_domains:
        next_checks.append("Start the ordinary package during capture so its SELinux process domain is observed.")
    if ordinary.role_service_mentions is None:
        next_checks.append("Capture role-service state if the target build uses role-derived permission grants.")

    return {
        "stockRole": stock.role,
        "ordinaryRole": ordinary.role,
        "primaryGate": {
            "id": primary_gate,
            "classification": primary_classification,
            "statement": primary_statement,
        },
        "findings": findings,
        "nextChecks": next_checks,
    }


def build_report(run: Path, stock_role: str, ordinary_role: str) -> dict[str, Any]:
    package_dirs = sorted(path for path in (run / "packages").iterdir() if path.is_dir())
    packages = [analyze_package(run, path) for path in package_dirs]
    by_role = {package.role: package for package in packages}
    if stock_role not in by_role:
        raise AnalysisError(f"stock role {stock_role!r} not found in {run / 'packages'}")
    if ordinary_role not in by_role:
        raise AnalysisError(f"ordinary role {ordinary_role!r} not found in {run / 'packages'}")

    report = {
        "schemaVersion": 1,
        "sourceCapture": str(run),
        "packages": [asdict(package) for package in packages],
        "comparison": compare(by_role[stock_role], by_role[ordinary_role]),
        "evidenceBoundary": {
            "verified": (
                "Package-manager, AppOps, package-path, UID, process-context, and allow/deny outputs are reported only when present and successful in the capture."
            ),
            "partiallyVerified": (
                "The primary-gate classification identifies the first observed authorization layer, not proof that later layers would permit or reject a camera endpoint."
            ),
            "unknown": (
                "Successful opening and optical use of IDs 2 or 3 require a separate controlled endpoint/session/capture experiment."
            ),
        },
    }
    return report


def markdown_bool(value: bool | None) -> str:
    if value is None:
        return "UNKNOWN"
    return "yes" if value else "no"


def render_markdown(report: dict[str, Any]) -> str:
    comparison = report["comparison"]
    lines = [
        "# Camera authorization comparison",
        "",
        f"Source capture: `{report['sourceCapture']}`",
        "",
        "## Primary observed gate",
        "",
        f"**{comparison['primaryGate']['classification']} — `{comparison['primaryGate']['id']}`**",
        "",
        comparison["primaryGate"]["statement"],
        "",
        "## Package observations",
        "",
        "| Role | Package | CAMERA | SYSTEM_CAMERA | AppOp | Partition | Priv-app | UID | SELinux domain |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for package in report["packages"]:
        lines.append(
            "| {role} | `{package}` | {camera_permission} | {system_camera_permission} | "
            "{camera_app_op} | {install_partition} | {privileged} | {uid} | {domains} |".format(
                role=package["role"],
                package=package["package"],
                camera_permission=package["camera_permission"],
                system_camera_permission=package["system_camera_permission"],
                camera_app_op=package["camera_app_op"],
                install_partition=package["install_partition"],
                privileged=markdown_bool(package["privileged_install"]),
                uid=package["uid"] if package["uid"] is not None else "UNKNOWN",
                domains=", ".join(f"`{domain}`" for domain in package["selinux_domains"]) or "UNKNOWN",
            )
        )

    lines.extend(["", "## Findings", ""])
    for item in comparison["findings"]:
        lines.append(f"- **{item['classification']} — `{item['id']}`:** {item['statement']}")
    lines.extend(["", "## Next checks", ""])
    lines.extend(f"- {item}" for item in comparison["nextChecks"])
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        f"- **VERIFIED:** {report['evidenceBoundary']['verified']}",
        f"- **PARTIALLY VERIFIED:** {report['evidenceBoundary']['partiallyVerified']}",
        f"- **UNKNOWN:** {report['evidenceBoundary']['unknown']}",
        "",
    ])
    return "\n".join(lines)


def write_text(path: str | None, text: str) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run = select_run(Path(args.input))
        report = build_report(run, args.stock_role, args.ordinary_role)
    except (OSError, AnalysisError) as error:
        print(f"authorization analysis failed: {error}", file=sys.stderr)
        return 2

    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)
    write_text(args.json_path, json_text)
    write_text(args.markdown_path, markdown_text)
    if not args.json_path and not args.markdown_path:
        sys.stdout.write(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
