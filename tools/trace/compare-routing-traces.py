#!/usr/bin/env python3
"""Compare Nothing Camera routing traces from controlled 0.6x, 1x and 2x runs.

The parser accepts:
- one JSON object per line;
- Frida CLI `send()` wrappers containing a `payload` object;
- log lines with a JSON object after a textual prefix.

It does not infer causal meaning from a single difference. The generated report separates
common events, route-specific events and values whose ordering changed between runs.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ROUTING_EVENT_KINDS = {
    "open-camera",
    "ndk-open-camera",
    "set-output-physical-id",
    "set-session-parameters",
    "session-parameters",
    "builder-set",
    "builder-set-physical-key",
    "builder-build",
    "create-session",
    "submit-request",
    "get-characteristics",
    "camera-id-list",
}

NOISE_FIELDS = {
    "timestampMs",
    "pid",
    "tid",
    "stack",
    "schema",
    "source",
}

ROUTING_KEY_PATTERN = re.compile(
    r"zoom|crop|focal|physical|sensorScenario|forceSensorMode|seamless|"
    r"insensor|remosaic|multicam|cameraFlex|flexibleCapabilities|pipDevices|"
    r"proprietaryRequest|initrequest|tnrOffByPhysicalIds|nothing\.camera|sois|supereis",
    re.IGNORECASE,
)


@dataclasses.dataclass(frozen=True)
class TraceInput:
    label: str
    path: Path


@dataclasses.dataclass
class ParsedTrace:
    source: TraceInput
    events: list[dict[str, Any]]
    rejected_lines: int


def extract_json_object(line: str) -> Any | None:
    text = line.strip()
    if not text:
        return None

    candidates = [text]
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Frida may print Python-style dictionaries. Convert only the common wrapper form;
    # do not use eval on untrusted traces.
    wrapper_match = re.search(r"payload['\"]?\s*:\s*(\{.*\})\s*,?\s*['\"]data", text)
    if wrapper_match:
        candidate = wrapper_match.group(1)
        candidate = re.sub(r"\bNone\b", "null", candidate)
        candidate = re.sub(r"\bTrue\b", "true", candidate)
        candidate = re.sub(r"\bFalse\b", "false", candidate)
        candidate = candidate.replace("'", '"')
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    return None


def unwrap_event(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    if value.get("type") == "send" and isinstance(value.get("payload"), dict):
        return dict(value["payload"])

    message = value.get("message")
    if isinstance(message, dict) and message.get("type") == "send":
        payload = message.get("payload")
        if isinstance(payload, dict):
            return dict(payload)

    if isinstance(value.get("payload"), dict) and "kind" in value["payload"]:
        return dict(value["payload"])

    if "kind" in value:
        return dict(value)

    return None


def parse_trace(source: TraceInput) -> ParsedTrace:
    events: list[dict[str, Any]] = []
    rejected = 0

    with source.path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            decoded = extract_json_object(line)
            event = unwrap_event(decoded)
            if event is None:
                rejected += 1
                continue
            events.append(event)

    return ParsedTrace(source=source, events=events, rejected_lines=rejected)


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: canonical(item)
            for key, item in sorted(value.items())
            if key not in NOISE_FIELDS
        }
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def json_key(value: Any) -> str:
    return json.dumps(canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_signature(event: dict[str, Any]) -> str:
    return json_key(event)


def filtered_events(trace: ParsedTrace, routing_only: bool) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for event in trace.events:
        kind = str(event.get("kind", ""))
        if routing_only and kind not in ROUTING_EVENT_KINDS:
            continue

        if routing_only and kind in {"builder-set", "builder-build", "submit-request", "session-parameters"}:
            serialized = json.dumps(event, ensure_ascii=False, sort_keys=True)
            if not ROUTING_KEY_PATTERN.search(serialized):
                continue

        output.append(event)
    return output


def occurrence_counter(events: Iterable[dict[str, Any]]) -> collections.Counter[str]:
    return collections.Counter(event_signature(event) for event in events)


def decode_signature(signature: str) -> Any:
    return json.loads(signature)


def select_route_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    opened_ids: list[str] = []
    physical_output_ids: list[str | None] = []
    session_methods: list[str] = []
    builder_values: dict[str, list[Any]] = collections.defaultdict(list)
    session_values: dict[str, list[Any]] = collections.defaultdict(list)

    for event in events:
        kind = event.get("kind")
        if kind in {"open-camera", "ndk-open-camera"}:
            camera_id = event.get("cameraId")
            if camera_id is not None:
                opened_ids.append(str(camera_id))
        elif kind == "set-output-physical-id":
            physical_output_ids.append(event.get("physicalCameraId"))
        elif kind == "create-session":
            method = event.get("methodName")
            if method is not None:
                session_methods.append(str(method))
        elif kind == "builder-set":
            key = event.get("key")
            if isinstance(key, dict):
                key = key.get("name")
            if key is not None:
                builder_values[str(key)].append(event.get("value"))
        elif kind in {"set-session-parameters", "session-parameters"}:
            request = event.get("request")
            if isinstance(request, dict):
                for key, value in request.items():
                    session_values[str(key)].append(value)
            values = event.get("values")
            if isinstance(values, list):
                for entry in values:
                    if not isinstance(entry, dict):
                        continue
                    key = entry.get("key")
                    if isinstance(key, dict):
                        key = key.get("name")
                    if key is not None:
                        session_values[str(key)].append(entry.get("value"))

    return {
        "openedCameraIds": opened_ids,
        "physicalOutputIds": physical_output_ids,
        "sessionMethods": session_methods,
        "builderValues": dict(sorted(builder_values.items())),
        "sessionValues": dict(sorted(session_values.items())),
    }


def compute_comparison(traces: list[ParsedTrace], routing_only: bool) -> dict[str, Any]:
    selected: dict[str, list[dict[str, Any]]] = {
        trace.source.label: filtered_events(trace, routing_only)
        for trace in traces
    }
    counters = {
        label: occurrence_counter(events)
        for label, events in selected.items()
    }

    labels = [trace.source.label for trace in traces]
    all_signatures = set().union(*(set(counter) for counter in counters.values()))

    common: list[dict[str, Any]] = []
    route_specific: dict[str, list[dict[str, Any]]] = {label: [] for label in labels}
    varying_counts: list[dict[str, Any]] = []

    for signature in sorted(all_signatures):
        counts = {label: counters[label].get(signature, 0) for label in labels}
        present_labels = [label for label, count in counts.items() if count > 0]
        decoded = decode_signature(signature)

        if len(present_labels) == len(labels) and len(set(counts.values())) == 1:
            common.append({"countPerTrace": next(iter(counts.values())), "event": decoded})
        elif len(present_labels) == 1:
            label = present_labels[0]
            route_specific[label].append({"count": counts[label], "event": decoded})
        else:
            varying_counts.append({"counts": counts, "event": decoded})

    return {
        "schemaVersion": 1,
        "routingOnly": routing_only,
        "traces": {
            trace.source.label: {
                "path": str(trace.source.path),
                "parsedEvents": len(trace.events),
                "selectedEvents": len(selected[trace.source.label]),
                "rejectedLines": trace.rejected_lines,
                "routeSummary": select_route_summary(selected[trace.source.label]),
            }
            for trace in traces
        },
        "common": common,
        "routeSpecific": route_specific,
        "varyingCounts": varying_counts,
    }


def markdown_value(value: Any) -> str:
    return "`" + json.dumps(value, ensure_ascii=False, sort_keys=True) + "`"


def event_label(event: dict[str, Any]) -> str:
    kind = str(event.get("kind", "unknown"))
    if kind in {"open-camera", "ndk-open-camera"}:
        return f"{kind}: camera {event.get('cameraId')}"
    if kind in {"builder-set", "builder-set-physical-key"}:
        key = event.get("key")
        if isinstance(key, dict):
            key = key.get("name")
        return f"{kind}: {key} = {json.dumps(event.get('value'), ensure_ascii=False)}"
    if kind == "set-output-physical-id":
        return f"set-output-physical-id: {event.get('physicalCameraId')}"
    if kind == "create-session":
        return f"create-session: {event.get('methodName')}"
    return kind


def write_markdown(comparison: dict[str, Any], path: Path) -> None:
    lines = [
        "# Expert Routing Differential Report",
        "",
        "This report is generated from observation-only traces. A differing event is a candidate discriminator, not automatically the cause of lens selection.",
        "",
        "## Trace summary",
        "",
        "| Route | Parsed | Selected | Rejected lines | Opened IDs | Physical output IDs |",
        "|---|---:|---:|---:|---|---|",
    ]

    for label, info in comparison["traces"].items():
        summary = info["routeSummary"]
        lines.append(
            f"| {label} | {info['parsedEvents']} | {info['selectedEvents']} | {info['rejectedLines']} | "
            f"{markdown_value(summary['openedCameraIds'])} | {markdown_value(summary['physicalOutputIds'])} |"
        )

    lines.extend(["", "## Route-specific events", ""])
    for label, entries in comparison["routeSpecific"].items():
        lines.extend([f"### {label}", ""])
        if not entries:
            lines.append("No event signature was unique to this trace.")
        else:
            for entry in entries:
                lines.append(f"- ×{entry['count']} — {event_label(entry['event'])}")
        lines.append("")

    lines.extend(["## Events present in multiple routes with differing counts", ""])
    if not comparison["varyingCounts"]:
        lines.append("None.")
    else:
        for entry in comparison["varyingCounts"]:
            lines.append(f"- {markdown_value(entry['counts'])} — {event_label(entry['event'])}")

    lines.extend([
        "",
        "## Interpretation order",
        "",
        "1. Compare opened camera IDs.",
        "2. Compare physical output IDs and per-physical request keys.",
        "3. Compare session parameters before session creation.",
        "4. Compare routing-related repeating-request keys.",
        "5. Compare still-capture-only keys.",
        "6. If Camera2 state is identical, move the discriminator below Camera2 to JNI, Binder, provider or HAL tracing.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_input(value: str) -> TraceInput:
    if "=" not in value:
        raise argparse.ArgumentTypeError("trace must use LABEL=PATH")
    label, raw_path = value.split("=", 1)
    label = label.strip()
    path = Path(raw_path).expanduser()
    if not label:
        raise argparse.ArgumentTypeError("trace label is empty")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"trace does not exist: {path}")
    return TraceInput(label=label, path=path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace",
        action="append",
        type=parse_input,
        required=True,
        help="Trace input in LABEL=PATH form; provide at least two.",
    )
    parser.add_argument("--json", type=Path, required=True, help="Output comparison JSON.")
    parser.add_argument("--markdown", type=Path, required=True, help="Output human-readable report.")
    parser.add_argument(
        "--all-events",
        action="store_true",
        help="Compare every parsed event instead of routing-focused events.",
    )
    args = parser.parse_args()

    if len(args.trace) < 2:
        parser.error("at least two --trace inputs are required")
    labels = [item.label for item in args.trace]
    if len(set(labels)) != len(labels):
        parser.error("trace labels must be unique")

    traces = [parse_trace(source) for source in args.trace]
    comparison = compute_comparison(traces, routing_only=not args.all_events)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(comparison, args.markdown)

    print(
        f"Compared {len(traces)} traces; wrote {args.json} and {args.markdown}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
