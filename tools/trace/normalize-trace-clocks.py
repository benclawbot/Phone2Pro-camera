#!/usr/bin/env python3
"""Normalize ADB clock samples and epoch logcat onto Perfetto BOOTTIME."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

LOGCAT_EPOCH = re.compile(r"^(\d+(?:\.\d+)?)\s+(.*)$")


def load_samples(path: pathlib.Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON on sample line {line_number}: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"sample line {line_number} must contain an object")
        errors = validate_sample(value)
        if errors:
            raise ValueError(f"sample line {line_number}: {'; '.join(errors)}")
        samples.append(value)
    if len(samples) < 2:
        raise ValueError("at least two clock samples are required")
    return samples


def validate_sample(sample: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "hostSendEpochNs",
        "hostReceiveEpochNs",
        "hostMidpointEpochNs",
        "roundTripNs",
        "deviceBoottimeNs",
        "deviceRealtimeNs",
        "deviceRealtimePrecisionNs",
    )
    for field in required:
        value = sample.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{field} must be a non-negative integer")
    send = sample.get("hostSendEpochNs")
    receive = sample.get("hostReceiveEpochNs")
    midpoint = sample.get("hostMidpointEpochNs")
    if all(isinstance(value, int) for value in (send, receive, midpoint)):
        if send > receive:
            errors.append("host send time exceeds receive time")
        if midpoint != (send + receive) // 2:
            errors.append("host midpoint is inconsistent")
        if sample.get("roundTripNs") != receive - send:
            errors.append("round trip is inconsistent")
    return errors


def median_int(values: Iterable[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot compute median of empty values")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def build_normalization(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if len(samples) < 2:
        raise ValueError("at least two clock samples are required")
    for index, sample in enumerate(samples):
        errors = validate_sample(sample)
        if errors:
            raise ValueError(f"samples[{index}]: {'; '.join(errors)}")

    boottime_offsets = [
        sample["hostMidpointEpochNs"] - sample["deviceBoottimeNs"]
        for sample in samples
    ]
    realtime_offsets = [
        sample["hostMidpointEpochNs"] - sample["deviceRealtimeNs"]
        for sample in samples
    ]
    device_realtime_minus_boottime = [
        sample["deviceRealtimeNs"] - sample["deviceBoottimeNs"]
        for sample in samples
    ]
    boottime_offset = median_int(boottime_offsets)
    realtime_offset = median_int(realtime_offsets)
    realtime_to_boottime_offset = median_int(device_realtime_minus_boottime)
    max_half_rtt = max(sample["roundTripNs"] // 2 for sample in samples)
    max_clock_precision = max(sample["deviceRealtimePrecisionNs"] for sample in samples)
    max_boottime_deviation = max(abs(value - boottime_offset) for value in boottime_offsets)
    max_realtime_deviation = max(abs(value - realtime_offset) for value in realtime_offsets)
    uncertainty = max_half_rtt + max_clock_precision + max(
        max_boottime_deviation, max_realtime_deviation
    )

    ordered_offsets = sorted(
        (sample["deviceBoottimeNs"], offset)
        for sample, offset in zip(samples, boottime_offsets)
    )
    elapsed_device = ordered_offsets[-1][0] - ordered_offsets[0][0]
    offset_change = ordered_offsets[-1][1] - ordered_offsets[0][1]
    drift_ppm = (
        offset_change * 1_000_000 / elapsed_device if elapsed_device > 0 else None
    )

    return {
        "schemaVersion": 1,
        "primaryTraceClock": "BUILTIN_CLOCK_BOOTTIME",
        "sampleCount": len(samples),
        "deviceBoottimeToHostEpochOffsetNs": boottime_offset,
        "deviceRealtimeToHostEpochOffsetNs": realtime_offset,
        "deviceBoottimeToDeviceRealtimeOffsetNs": realtime_to_boottime_offset,
        "estimatedUncertaintyNs": uncertainty,
        "maxRoundTripNs": max(sample["roundTripNs"] for sample in samples),
        "maxDeviceRealtimePrecisionNs": max_clock_precision,
        "observedBoottimeOffsetRangeNs": [min(boottime_offsets), max(boottime_offsets)],
        "observedRealtimeOffsetRangeNs": [min(realtime_offsets), max(realtime_offsets)],
        "estimatedDriftPpm": drift_ppm,
        "conversion": {
            "hostEpochToDeviceBoottime": (
                "deviceBoottimeNs = hostEpochNs - deviceBoottimeToHostEpochOffsetNs"
            ),
            "deviceBoottimeToHostEpoch": (
                "hostEpochNs = deviceBoottimeNs + deviceBoottimeToHostEpochOffsetNs"
            ),
            "deviceRealtimeToDeviceBoottime": (
                "deviceBoottimeNs = deviceRealtimeNs - "
                "deviceBoottimeToDeviceRealtimeOffsetNs"
            ),
        },
        "samples": samples,
    }


def epoch_text_to_ns(value: str) -> int:
    try:
        decimal = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"invalid epoch timestamp: {value}") from error
    if decimal < 0:
        raise ValueError("epoch timestamp cannot be negative")
    return int(decimal * Decimal(1_000_000_000))


def normalize_logcat_lines(
    lines: Iterable[str], normalization: dict[str, Any]
) -> list[dict[str, Any]]:
    offset = normalization.get("deviceBoottimeToDeviceRealtimeOffsetNs")
    if not isinstance(offset, int):
        raise ValueError("normalization is missing device realtime/BOOTTIME offset")
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.rstrip("\n")
        match = LOGCAT_EPOCH.match(line)
        if not match:
            continue
        host_epoch_ns = epoch_text_to_ns(match.group(1))
        events.append(
            {
                "schemaVersion": 1,
                "source": "logcat-epoch",
                "sourceLine": line_number,
                "hostEpochNs": host_epoch_ns,
                "deviceBoottimeNs": host_epoch_ns - offset,
                "estimatedUncertaintyNs": normalization["estimatedUncertaintyNs"],
                "message": match.group(2),
            }
        )
    return events


def write_json_lines(path: pathlib.Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("samples", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--logcat", type=pathlib.Path)
    parser.add_argument("--normalized-logcat", type=pathlib.Path)
    args = parser.parse_args()

    if (args.logcat is None) != (args.normalized_logcat is None):
        parser.error("--logcat and --normalized-logcat must be supplied together")
    try:
        samples = load_samples(args.samples)
        normalization = build_normalization(samples)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(normalization, indent=2) + "\n", encoding="utf-8"
        )
        if args.logcat is not None and args.normalized_logcat is not None:
            events = normalize_logcat_lines(
                args.logcat.read_text(encoding="utf-8", errors="replace").splitlines(),
                normalization,
            )
            write_json_lines(args.normalized_logcat, events)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"normalized {normalization['sampleCount']} samples; "
        f"uncertainty_ns={normalization['estimatedUncertaintyNs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
