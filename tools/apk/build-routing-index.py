#!/usr/bin/env python3
"""Build a ranked Nothing Camera routing index from local static-analysis output.

The tool reads JADX/apktool/string-analysis output produced by
``tools/apk/analyze-nothing-camera.sh``. It creates a derived index of files and
line-level signals relevant to Expert 0.6x/1x/2x routing without copying source
files into the repository.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

TEXT_EXTENSIONS = {
    ".java",
    ".kt",
    ".xml",
    ".smali",
    ".txt",
    ".json",
    ".properties",
    ".cfg",
    ".conf",
    ".yaml",
    ".yml",
}
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_SNIPPET_LENGTH = 280
MAX_MATCHES_PER_SIGNAL_PER_FILE = 20


@dataclasses.dataclass(frozen=True)
class Signal:
    id: str
    label: str
    weight: int
    patterns: tuple[re.Pattern[str], ...]


SIGNALS = (
    Signal(
        "expert-ui",
        "Expert/manual lens UI",
        7,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"\bexpert\b",
                r"\bmanual(?:mode)?\b",
                r"0[._]?6\s*[x×]",
                r"\b15\s*mm\b",
                r"\b24\s*mm\b",
                r"\b50\s*mm\b",
                r"lens(?:button|selector|switch|state)",
                r"focal(?:length)?(?:button|selector|state|value)",
            )
        ),
    ),
    Signal(
        "camera-id-routing",
        "Camera ID selection",
        10,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"openCamera\s*\(",
                r"getCameraCharacteristics\s*\(",
                r"cameraId",
                r"camera_id",
                r"physicalCameraId",
                r"setPhysicalCameraId\s*\(",
                r"setPhysicalCameraKey\s*\(",
            )
        ),
    ),
    Signal(
        "session-configuration",
        "Session and stream configuration",
        9,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"SessionConfiguration",
                r"setSessionParameters\s*\(",
                r"createCaptureSession",
                r"configureStreams",
                r"OutputConfiguration",
                r"InputConfiguration",
                r"createCaptureRequest",
                r"setRepeatingRequest",
                r"captureBurst",
            )
        ),
    ),
    Signal(
        "vendor-routing-key",
        "MediaTek/Nothing routing metadata",
        12,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"com\.mediatek\.configure\.setting\.(?:initrequest|proprietaryRequest)",
                r"com\.mediatek\.cameraflex\.",
                r"com\.mediatek\.multicamfeature\.",
                r"com\.mediatek\.insensorzoomfeature\.",
                r"com\.mediatek\.seamlessfeature\.",
                r"com\.mediatek\.streamingfeature\.pipDevices",
                r"com\.mediatek\.streamingfeature\.tnrOffByPhysicalIds",
                r"com\.nothing\.camera\.",
                r"nothing\.camera\.",
            )
        ),
    ),
    Signal(
        "sat-multicam",
        "SAT/multicamera routing",
        11,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"\bSAT\b",
                r"multi.?cam",
                r"camera.?flex",
                r"logical.?camera",
                r"physical.?camera",
                r"seamless",
                r"sensorScenario",
                r"forceSensorMode",
                r"pipDevices",
            )
        ),
    ),
    Signal(
        "widget-intent",
        "Widget/intent launch state",
        6,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"WIDGET_CAMERA",
                r"CAMERA_PREFIX_FOCALLENGTH_VALUE",
                r"CAMERA_PREFIX_MAIN_MODE",
                r"CAMERA_PREFIX_SUB_MODE",
                r"getIntent\s*\(",
                r"getStringExtra\s*\(",
                r"onNewIntent\s*\(",
                r"shortcut",
                r"widget",
            )
        ),
    ),
    Signal(
        "state-persistence",
        "Route state persistence/restoration",
        7,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"SharedPreferences",
                r"DataStore",
                r"savedInstanceState",
                r"restore",
                r"persist",
                r"lastLens",
                r"selectedLens",
                r"currentLens",
                r"zoomState",
                r"focalState",
            )
        ),
    ),
    Signal(
        "jni-native",
        "JNI/native boundary",
        10,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"System\.loadLibrary",
                r"\bnative\s+[A-Za-z0-9_$<>\[\].?, ]+\s+[A-Za-z0-9_$]+\s*\(",
                r"JNI_OnLoad",
                r"registerNatives",
                r"ACameraManager_openCamera",
                r"ACameraDevice_createCaptureRequest",
            )
        ),
    ),
    Signal(
        "privilege-permission",
        "Camera privilege/permission",
        8,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"android\.permission\.SYSTEM_CAMERA",
                r"android\.permission\.CAMERA",
                r"privapp",
                r"signature",
                r"system.?camera",
                r"checkPermission",
                r"enforceCallingPermission",
            )
        ),
    ),
    Signal(
        "camera-id-constant",
        "Candidate internal camera ID constants",
        5,
        tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                r"(?:camera|lens|sensor|sat)[A-Za-z0-9_$]*\s*=\s*[2345]\b",
                r"case\s+[2345]\s*:",
                r"[\"'](?:2|3|4|5)[\"']",
            )
        ),
    ),
)

SIGNAL_BY_ID = {signal.id: signal for signal in SIGNALS}


def find_analysis_root(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(path)
    if (path / "jadx").is_dir() or (path / "apktool").is_dir():
        return path
    candidates = sorted(
        (
            child
            for child in path.iterdir()
            if child.is_dir()
            and ((child / "jadx").is_dir() or (child / "apktool").is_dir())
        ),
        key=lambda item: item.name,
    )
    if not candidates:
        raise FileNotFoundError(f"no analysis run found below {path}")
    return candidates[-1]


def iter_text_files(root: Path) -> Iterator[Path]:
    search_roots = [
        root / "jadx",
        root / "apktool",
        root / "reports",
        root / "native-analysis",
    ]
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in sorted(search_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def normalize_snippet(line: str) -> str:
    value = " ".join(line.strip().split())
    if len(value) <= MAX_SNIPPET_LENGTH:
        return value
    return value[:MAX_SNIPPET_LENGTH] + "…"


def source_identity(path: Path, text: str) -> dict[str, Any]:
    package = None
    class_name = None
    package_match = re.search(
        r"^\s*package\s+([A-Za-z0-9_.$]+)\s*;?",
        text,
        re.MULTILINE,
    )
    if package_match:
        package = package_match.group(1)
    class_match = re.search(
        r"\b(?:class|interface|object|enum\s+class|enum)\s+([A-Za-z0-9_$]+)",
        text,
    )
    if class_match:
        class_name = class_match.group(1)
    return {"package": package, "className": class_name, "suffix": path.suffix.lower()}


def scan_file(root: Path, path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    lines = text.splitlines()
    matches: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for line_number, line in enumerate(lines, 1):
        for signal in SIGNALS:
            if len(matches[signal.id]) >= MAX_MATCHES_PER_SIGNAL_PER_FILE:
                continue
            matched_patterns = [
                pattern.pattern for pattern in signal.patterns if pattern.search(line)
            ]
            if not matched_patterns:
                continue
            matches[signal.id].append(
                {
                    "line": line_number,
                    "snippet": normalize_snippet(line),
                    "patterns": matched_patterns,
                }
            )

    if not matches:
        return None

    signal_ids = sorted(matches)
    base_score = sum(SIGNAL_BY_ID[signal_id].weight for signal_id in signal_ids)
    density_bonus = min(20, sum(len(items) for items in matches.values()) // 3)
    bridge_bonus = 0
    if "expert-ui" in matches and "camera-id-routing" in matches:
        bridge_bonus += 14
    if "expert-ui" in matches and "session-configuration" in matches:
        bridge_bonus += 12
    if "expert-ui" in matches and "vendor-routing-key" in matches:
        bridge_bonus += 18
    if "widget-intent" in matches and "state-persistence" in matches:
        bridge_bonus += 8
    if "session-configuration" in matches and "jni-native" in matches:
        bridge_bonus += 10
    if "sat-multicam" in matches and "vendor-routing-key" in matches:
        bridge_bonus += 12

    relative = path.relative_to(root).as_posix()
    return {
        "path": relative,
        "identity": source_identity(path, text),
        "score": base_score + density_bonus + bridge_bonus,
        "baseScore": base_score,
        "densityBonus": density_bonus,
        "bridgeBonus": bridge_bonus,
        "signalIds": signal_ids,
        "signals": dict(matches),
    }


def extract_edges(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identities: dict[str, str] = {}
    for item in files:
        class_name = item["identity"].get("className")
        package = item["identity"].get("package")
        if class_name:
            identities[class_name] = item["path"]
        if class_name and package:
            identities[f"{package}.{class_name}"] = item["path"]

    edges: set[tuple[str, str, str]] = set()
    for item in files:
        snippets = [
            match["snippet"]
            for values in item["signals"].values()
            for match in values
        ]
        combined = "\n".join(snippets)
        for identity, target in identities.items():
            if target == item["path"] or len(identity) < 4:
                continue
            short_name = identity.rsplit(".", 1)[-1]
            if re.search(rf"\b{re.escape(short_name)}\b", combined):
                edges.add((item["path"], target, "signal-snippet-reference"))
    return [
        {"from": source, "to": target, "kind": kind}
        for source, target, kind in sorted(edges)
    ]


def build_report(input_path: Path) -> dict[str, Any]:
    root = find_analysis_root(input_path)
    files = [
        item
        for path in iter_text_files(root)
        if (item := scan_file(root, path)) is not None
    ]
    files.sort(key=lambda item: (-item["score"], item["path"]))

    category_counts: dict[str, int] = collections.Counter(
        signal_id for item in files for signal_id in item["signalIds"]
    )
    bridge_files = [item["path"] for item in files if item["bridgeBonus"] > 0]
    route_candidates = [
        item["path"]
        for item in files
        if (
            "expert-ui" in item["signalIds"]
            and (
                "camera-id-routing" in item["signalIds"]
                or "session-configuration" in item["signalIds"]
                or "vendor-routing-key" in item["signalIds"]
                or "sat-multicam" in item["signalIds"]
            )
        )
    ]

    return {
        "schemaVersion": 1,
        "analysisRoot": str(root),
        "scannedFileCount": sum(1 for _ in iter_text_files(root)),
        "matchedFileCount": len(files),
        "signalDefinitions": [
            {"id": signal.id, "label": signal.label, "weight": signal.weight}
            for signal in SIGNALS
        ],
        "categoryFileCounts": dict(sorted(category_counts.items())),
        "routeCandidateFiles": route_candidates,
        "bridgeFiles": bridge_files,
        "files": files,
        "derivedEdges": extract_edges(files[:100]),
    }


def render_markdown(report: dict[str, Any], limit: int) -> str:
    lines = [
        "# Nothing Camera Routing Static Index",
        "",
        f"- Analysis root: `{report['analysisRoot']}`",
        f"- Scanned text files: **{report['scannedFileCount']}**",
        f"- Files with routing signals: **{report['matchedFileCount']}**",
        f"- UI-to-camera bridge candidates: **{len(report['routeCandidateFiles'])}**",
        "",
        "## Signal coverage",
        "",
        "| Signal | Files |",
        "|---|---:|",
    ]
    labels = {item["id"]: item["label"] for item in report["signalDefinitions"]}
    for signal_id, count in report["categoryFileCounts"].items():
        lines.append(f"| {labels.get(signal_id, signal_id)} | {count} |")

    lines.extend(["", "## Ranked files", ""])
    for item in report["files"][:limit]:
        identity = item["identity"]
        title = identity.get("className") or Path(item["path"]).name
        lines.append(f"### {item['score']} — `{title}`")
        lines.append("")
        lines.append(f"Path: `{item['path']}`")
        if identity.get("package"):
            lines.append(f"Package: `{identity['package']}`")
        lines.append(f"Signals: `{', '.join(item['signalIds'])}`")
        lines.append(
            f"Score: base {item['baseScore']} + density {item['densityBonus']} + bridge {item['bridgeBonus']}"
        )
        lines.append("")
        shown = 0
        for signal_id in item["signalIds"]:
            for match in item["signals"][signal_id][:3]:
                snippet = match["snippet"].replace("`", "'")
                lines.append(f"- `{signal_id}` L{match['line']}: `{snippet}`")
                shown += 1
                if shown >= 10:
                    break
            if shown >= 10:
                break
        lines.append("")

    lines.extend(
        [
            "## Review order",
            "",
            "1. Review files that bridge `expert-ui` to camera ID, session, SAT or vendor-key signals.",
            "2. Trace field assignments and listeners backward from the lens control.",
            "3. Trace camera/session builders forward to `openCamera`, session parameters, request keys or JNI.",
            "4. Treat obfuscated indirect calls and reflection as unresolved edges requiring runtime hooks.",
            "5. Do not infer causality from a string hit; confirm execution with controlled 0.6x/1x/2x traces.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path, help="Analysis run or parent directory.")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=40)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    try:
        report = build_report(args.analysis)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    markdown = render_markdown(report, args.limit)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown, encoding="utf-8")
    if not args.json and not args.markdown:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
