#!/usr/bin/env python3
"""Capture one bounded host/device clock correlation sample over ADB."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from typing import Any

UPTIME = re.compile(r"^uptime=(\d+)(?:\.(\d+))?$")
REALTIME_NS = re.compile(r"^realtime_ns=(\d+)$")
REALTIME_S = re.compile(r"^realtime_s=(\d+)$")

Runner = Callable[..., subprocess.CompletedProcess[str]]

REMOTE_COMMAND = r"""
set -eu
uptime_value=$(cut -d ' ' -f 1 /proc/uptime)
printf 'uptime=%s\n' "$uptime_value"
realtime_ns=$(date +%s%N 2>/dev/null || true)
case "$realtime_ns" in
  *N*|'') printf 'realtime_s=%s\n' "$(date +%s)" ;;
  *) printf 'realtime_ns=%s\n' "$realtime_ns" ;;
esac
""".strip()


def decimal_seconds_to_ns(integer: str, fraction: str | None) -> int:
    fraction = (fraction or "")[:9].ljust(9, "0")
    return int(integer) * 1_000_000_000 + int(fraction or "0")


def parse_device_clock_output(output: str) -> tuple[int, int, int]:
    uptime_ns: int | None = None
    realtime_ns: int | None = None
    realtime_precision_ns: int | None = None
    for raw_line in output.replace("\r", "").splitlines():
        line = raw_line.strip()
        match = UPTIME.fullmatch(line)
        if match:
            uptime_ns = decimal_seconds_to_ns(match.group(1), match.group(2))
            continue
        match = REALTIME_NS.fullmatch(line)
        if match:
            realtime_ns = int(match.group(1))
            realtime_precision_ns = 1
            continue
        match = REALTIME_S.fullmatch(line)
        if match:
            realtime_ns = int(match.group(1)) * 1_000_000_000
            realtime_precision_ns = 1_000_000_000
    if uptime_ns is None:
        raise ValueError("ADB clock sample is missing /proc/uptime")
    if realtime_ns is None or realtime_precision_ns is None:
        raise ValueError("ADB clock sample is missing device realtime")
    return uptime_ns, realtime_ns, realtime_precision_ns


def capture_sample(
    phase: str,
    adb: Sequence[str],
    runner: Runner = subprocess.run,
    time_ns: Callable[[], int] = time.time_ns,
) -> dict[str, Any]:
    if not phase or not phase.strip():
        raise ValueError("phase must be non-empty")
    command = [*adb, "shell", "sh", "-c", REMOTE_COMMAND]
    host_send_ns = time_ns()
    completed = runner(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    host_receive_ns = time_ns()
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown ADB error"
        raise ValueError(f"ADB clock sample failed: {detail}")
    uptime_ns, realtime_ns, precision_ns = parse_device_clock_output(completed.stdout)
    return {
        "schemaVersion": 1,
        "phase": phase,
        "hostSendEpochNs": host_send_ns,
        "hostReceiveEpochNs": host_receive_ns,
        "hostMidpointEpochNs": (host_send_ns + host_receive_ns) // 2,
        "roundTripNs": host_receive_ns - host_send_ns,
        "deviceBoottimeNs": uptime_ns,
        "deviceRealtimeNs": realtime_ns,
        "deviceRealtimePrecisionNs": precision_ns,
    }


def validate_sample(sample: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if sample.get("schemaVersion") != 1:
        errors.append("sample schemaVersion must be 1")
    if not isinstance(sample.get("phase"), str) or not sample.get("phase"):
        errors.append("sample phase must be non-empty")
    numeric = (
        "hostSendEpochNs",
        "hostReceiveEpochNs",
        "hostMidpointEpochNs",
        "roundTripNs",
        "deviceBoottimeNs",
        "deviceRealtimeNs",
        "deviceRealtimePrecisionNs",
    )
    for field in numeric:
        value = sample.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"sample {field} must be a non-negative integer")
    send = sample.get("hostSendEpochNs")
    receive = sample.get("hostReceiveEpochNs")
    midpoint = sample.get("hostMidpointEpochNs")
    if all(isinstance(value, int) for value in (send, receive, midpoint)):
        if send > receive:
            errors.append("sample host send time exceeds receive time")
        if midpoint != (send + receive) // 2:
            errors.append("sample host midpoint is inconsistent")
        if sample.get("roundTripNs") != receive - send:
            errors.append("sample round trip is inconsistent")
    return errors


def append_json_line(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--serial")
    args = parser.parse_args()

    adb = ["adb"]
    if args.serial:
        adb.extend(["-s", args.serial])
    try:
        sample = capture_sample(args.phase, adb)
        errors = validate_sample(sample)
        if errors:
            raise ValueError("; ".join(errors))
        append_json_line(args.output, sample)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"captured clock sample phase={args.phase} "
        f"rtt_ns={sample['roundTripNs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
