#!/usr/bin/env python3
"""Normalize Camera2/framework/service errors by lifecycle stage and code namespace.

The analyzer accepts diagnostic JSON documents and JSON-lines/Frida logs. Numeric
camera error values are interpreted only within their declared API namespace;
CameraAccessException reason 4 and CameraDevice.StateCallback error 4 are not
the same error.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Iterator

STAGES = (
    "ENUMERATION",
    "CHARACTERISTICS",
    "OPEN_PREFLIGHT",
    "OPEN_CONNECT",
    "SESSION_CONFIGURATION",
    "REQUEST_SUBMISSION",
)

CATEGORIES = (
    "SECURITY",
    "DISCONNECTED",
    "IN_USE",
    "MAX_CAMERAS",
    "INVALID_ARGUMENT",
    "DEVICE_SPECIFIC",
    "SERVICE",
    "CONFIGURATION",
    "REQUEST_FAILURE",
    "TIMEOUT",
    "UNKNOWN",
)

CAMERA_ACCESS_REASONS = {
    1: ("CAMERA_DISABLED", "SECURITY", "Camera access disabled by device policy or service policy."),
    2: ("CAMERA_DISCONNECTED", "DISCONNECTED", "Camera disconnected or became unavailable."),
    3: ("CAMERA_ERROR", "DEVICE_SPECIFIC", "Camera service or device reported a generic camera error."),
    4: ("CAMERA_IN_USE", "IN_USE", "The requested camera is already in use."),
    5: ("MAX_CAMERAS_IN_USE", "MAX_CAMERAS", "The concurrent-camera limit has been reached."),
}

STATE_CALLBACK_ERRORS = {
    1: ("ERROR_CAMERA_IN_USE", "IN_USE", "CameraDevice state callback reported camera in use."),
    2: ("ERROR_MAX_CAMERAS_IN_USE", "MAX_CAMERAS", "CameraDevice state callback reported the maximum camera count in use."),
    3: ("ERROR_CAMERA_DISABLED", "SECURITY", "CameraDevice state callback reported camera disabled by policy."),
    4: ("ERROR_CAMERA_DEVICE", "DEVICE_SPECIFIC", "CameraDevice state callback reported a fatal device error."),
    5: ("ERROR_CAMERA_SERVICE", "SERVICE", "CameraDevice state callback reported a fatal camera-service error."),
}

CAPTURE_FAILURE_REASONS = {
    0: ("REASON_ERROR", "REQUEST_FAILURE", "Capture failed because of a request or device error."),
    1: ("REASON_FLUSHED", "REQUEST_FAILURE", "Capture was flushed before completion."),
}

SYSTEM_ONLY_RE = re.compile(r"system only device\s+(\S+)", re.IGNORECASE)
UNKNOWN_DEVICE_RE = re.compile(r"unknown device\s+(\S+)", re.IGNORECASE)
SECURITY_RE = re.compile(r"securityexception|permission denial|permission denied|not allowed", re.IGNORECASE)
DISCONNECTED_RE = re.compile(r"disconnect(?:ed|ion)?|camera service (?:died|is unavailable)", re.IGNORECASE)
IN_USE_RE = re.compile(r"camera(?:\s+is)?\s+in use|already in use|camera_in_use", re.IGNORECASE)
MAX_CAMERAS_RE = re.compile(r"max(?:imum)? cameras|too many cameras|max_cameras", re.IGNORECASE)
INVALID_RE = re.compile(r"illegalargumentexception|invalid argument|bad value|unknown device", re.IGNORECASE)
TIMEOUT_RE = re.compile(r"timed?\s*out|timeout", re.IGNORECASE)
DEVICE_RE = re.compile(r"camera device error|fatal device|hardware error|device-specific", re.IGNORECASE)
SERVICE_RE = re.compile(r"camera service error|service-specific|service died|binder.*dead", re.IGNORECASE)


class AnalysisError(ValueError):
    """Raised when an input cannot be interpreted safely."""


@dataclasses.dataclass(frozen=True)
class SourceInput:
    label: str
    path: Path


@dataclasses.dataclass
class CallerIdentity:
    package_name: str | None = None
    uid: int | None = None
    pid: int | None = None
    tid: int | None = None
    process_name: str | None = None
    selinux_domain: str | None = None
    role: str | None = None


@dataclasses.dataclass
class ErrorObservation:
    source_label: str
    source_path: str
    stage: str
    operation: str
    outcome: str
    camera_id: str | None
    category: str
    family: str
    classification: str
    code_namespace: str | None
    code: int | str | None
    code_name: str | None
    exception_type: str | None
    message: str | None
    timestamp_ms: int | float | None
    duration_ms: int | float | None
    caller: CallerIdentity
    enforcing_paths: list[dict[str, str]]
    evidence: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a stage-aware Camera2 error taxonomy from diagnostic JSON and trace logs."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        metavar="[LABEL=]PATH",
        help="diagnostic JSON or JSON-lines/Frida log",
    )
    parser.add_argument("--json", dest="json_path", help="write JSON report")
    parser.add_argument("--markdown", dest="markdown_path", help="write Markdown report")
    parser.add_argument("--caller-package", help="default caller package for records without one")
    parser.add_argument("--caller-uid", type=int, help="default caller UID")
    parser.add_argument("--caller-selinux-domain", help="default caller SELinux domain")
    parser.add_argument("--caller-role", help="default caller role, for example stock or ordinary")
    return parser


def parse_source(value: str) -> SourceInput:
    if "=" in value:
        label, path_text = value.split("=", 1)
        if label and path_text:
            return SourceInput(label, Path(path_text))
    path = Path(value)
    return SourceInput(path.stem, path)


def first_value(mapping: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def to_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return None
    return None


def to_int(value: Any) -> int | None:
    number = to_number(value)
    return int(number) if number is not None else None


def error_fields(value: Any) -> tuple[str | None, str | None, int | None]:
    if isinstance(value, dict):
        exception_type = first_value(value, ("type", "exceptionType", "className"))
        message = first_value(value, ("message", "string", "error", "detail"))
        reason = to_int(first_value(value, ("cameraAccessReason", "reason", "errorCode")))
        return (
            str(exception_type) if exception_type is not None else None,
            str(message) if message is not None else None,
            reason,
        )
    if isinstance(value, str):
        return None, value, None
    return None, None, None


def merge_caller(record: dict[str, Any], default: CallerIdentity) -> CallerIdentity:
    nested = record.get("caller") if isinstance(record.get("caller"), dict) else {}

    def choose(*keys: str) -> Any:
        for source in (nested, record):
            value = first_value(source, keys)
            if value is not None:
                return value
        return None

    package_value = choose("packageName", "package", "callerPackage")
    uid_value = choose("uid", "callerUid")
    pid_value = choose("pid")
    tid_value = choose("tid")
    process_value = choose("processName", "process")
    selinux_value = choose("selinuxDomain", "seLinuxDomain", "context")
    role_value = choose("callerRole", "role")
    return CallerIdentity(
        package_name=str(package_value) if package_value is not None else default.package_name,
        uid=to_int(uid_value) if uid_value is not None else default.uid,
        pid=to_int(pid_value) if pid_value is not None else default.pid,
        tid=to_int(tid_value) if tid_value is not None else default.tid,
        process_name=str(process_value) if process_value is not None else default.process_name,
        selinux_domain=str(selinux_value) if selinux_value is not None else default.selinux_domain,
        role=str(role_value) if role_value is not None else default.role,
    )


def enforcing_paths(stage: str, family: str) -> list[dict[str, str]]:
    paths: list[dict[str, str]] = []
    if family == "SYSTEM_CAMERA_PERMISSION":
        paths.extend([
            {
                "layer": "CameraService",
                "symbol": "CameraService::shouldRejectSystemCameraConnection",
                "classification": "VERIFIED_AOSP_ERROR_MATCH",
            },
            {
                "layer": "permission",
                "symbol": "android.permission.SYSTEM_CAMERA",
                "classification": "VERIFIED_AOSP_CONTRACT",
            },
        ])
    elif family == "CAMERA_ID_NOT_FOUND":
        paths.append({
            "layer": "CameraService/provider",
            "symbol": "getCameraCharacteristics provider-device lookup",
            "classification": "PARTIALLY_VERIFIED",
        })
    elif stage == "OPEN_CONNECT":
        paths.append({
            "layer": "CameraService",
            "symbol": "CameraService::connectHelper / CameraDevice.StateCallback",
            "classification": "PARTIALLY_VERIFIED",
        })
    elif stage == "SESSION_CONFIGURATION":
        paths.append({
            "layer": "Camera2 session",
            "symbol": "CameraCaptureSession.StateCallback::onConfigureFailed",
            "classification": "VERIFIED_API_REPORTING_PATH",
        })
    elif stage == "REQUEST_SUBMISSION":
        paths.append({
            "layer": "Camera2 request",
            "symbol": "CameraCaptureSession request submission / CaptureFailure",
            "classification": "VERIFIED_API_REPORTING_PATH",
        })
    elif stage == "CHARACTERISTICS":
        paths.append({
            "layer": "CameraManager/CameraService",
            "symbol": "getCameraCharacteristics",
            "classification": "VERIFIED_OPERATION",
        })
    return paths


def classify_error(
    stage: str,
    exception_type: str | None,
    message: str | None,
    *,
    namespace: str | None = None,
    code: int | None = None,
    explicit_family: str | None = None,
) -> tuple[str, str, str, str | None, str]:
    text = " ".join(part for part in (exception_type, message) if part)
    if explicit_family:
        return "UNKNOWN", explicit_family, "VERIFIED", None, "Explicit event family."
    if SYSTEM_ONLY_RE.search(text):
        return (
            "SECURITY",
            "SYSTEM_CAMERA_PERMISSION",
            "VERIFIED",
            "SYSTEM_ONLY_CAMERA",
            "Recognized system-only endpoint rejected for caller authorization.",
        )
    if UNKNOWN_DEVICE_RE.search(text):
        return (
            "INVALID_ARGUMENT",
            "CAMERA_ID_NOT_FOUND",
            "VERIFIED",
            None,
            "Camera ID is not known by the service/provider lookup.",
        )
    if namespace == "CameraAccessException.reason" and code in CAMERA_ACCESS_REASONS:
        name, category, statement = CAMERA_ACCESS_REASONS[code]
        return category, name, "VERIFIED", name, statement
    if namespace == "CameraDevice.StateCallback.error" and code in STATE_CALLBACK_ERRORS:
        name, category, statement = STATE_CALLBACK_ERRORS[code]
        return category, name, "VERIFIED", name, statement
    if namespace == "CaptureFailure.reason" and code in CAPTURE_FAILURE_REASONS:
        name, category, statement = CAPTURE_FAILURE_REASONS[code]
        return category, name, "VERIFIED", name, statement
    if "onConfigureFailed" in text or "configure failed" in text.lower():
        return "CONFIGURATION", "SESSION_CONFIGURE_FAILED", "VERIFIED", None, "Capture session configuration failed."
    if SECURITY_RE.search(text):
        return "SECURITY", "PERMISSION_OR_POLICY_DENIED", "VERIFIED", None, "Permission or policy rejected the operation."
    if MAX_CAMERAS_RE.search(text):
        return "MAX_CAMERAS", "MAX_CAMERAS_IN_USE", "VERIFIED", None, "Concurrent-camera limit reached."
    if IN_USE_RE.search(text):
        return "IN_USE", "CAMERA_IN_USE", "VERIFIED", None, "Requested camera is already in use."
    if DISCONNECTED_RE.search(text):
        return "DISCONNECTED", "CAMERA_DISCONNECTED", "VERIFIED", None, "Camera or camera service disconnected."
    if TIMEOUT_RE.search(text):
        return "TIMEOUT", "OPERATION_TIMEOUT", "VERIFIED", None, "Camera operation timed out."
    if INVALID_RE.search(text) or (exception_type and exception_type.endswith("IllegalArgumentException")):
        return "INVALID_ARGUMENT", "ILLEGAL_ARGUMENT", "VERIFIED", None, "Caller supplied an invalid ID, configuration, or argument."
    if SERVICE_RE.search(text):
        return "SERVICE", "CAMERA_SERVICE_ERROR", "PARTIALLY_VERIFIED", None, "Camera service or Binder path reported an error."
    if DEVICE_RE.search(text):
        return "DEVICE_SPECIFIC", "CAMERA_DEVICE_ERROR", "PARTIALLY_VERIFIED", None, "Camera device or HAL reported an error."
    return "UNKNOWN", "UNCLASSIFIED", "UNKNOWN", None, "No supported error signature matched."


def make_observation(
    source: SourceInput,
    stage: str,
    operation: str,
    outcome: str,
    record: dict[str, Any],
    error: Any,
    default_caller: CallerIdentity,
    *,
    namespace: str | None = None,
    code: int | None = None,
    camera_id: Any = None,
) -> ErrorObservation:
    exception_type, message, nested_reason = error_fields(error)
    if namespace is None and nested_reason is not None:
        namespace = "CameraAccessException.reason"
        code = nested_reason
    category, family, classification, code_name, statement = classify_error(
        stage,
        exception_type,
        message,
        namespace=namespace,
        code=code,
    )
    timestamp = to_number(first_value(record, ("timestampMs", "elapsedRealtimeMillis", "startTimestampMs")))
    duration = to_number(first_value(record, ("durationMs", "durationMillis")))
    return ErrorObservation(
        source_label=source.label,
        source_path=str(source.path),
        stage=stage,
        operation=operation,
        outcome=outcome,
        camera_id=str(camera_id) if camera_id is not None else None,
        category=category,
        family=family,
        classification=classification,
        code_namespace=namespace,
        code=code,
        code_name=code_name,
        exception_type=exception_type,
        message=message,
        timestamp_ms=timestamp,
        duration_ms=duration,
        caller=merge_caller(record, default_caller),
        enforcing_paths=enforcing_paths(stage, family),
        evidence={"statement": statement, "eventKind": record.get("kind")},
    )


def walk(value: Any) -> Iterator[tuple[tuple[str, ...], Any]]:
    stack: list[tuple[tuple[str, ...], Any]] = [((), value)]
    while stack:
        path, current = stack.pop()
        yield path, current
        if isinstance(current, dict):
            stack.extend((path + (str(key),), child) for key, child in reversed(list(current.items())))
        elif isinstance(current, list):
            stack.extend((path + (str(index),), child) for index, child in reversed(list(enumerate(current))))


def probe_observations(
    source: SourceInput,
    document: Any,
    default_caller: CallerIdentity,
) -> list[ErrorObservation]:
    output: list[ErrorObservation] = []
    seen_probe_objects: set[int] = set()
    for _path, value in walk(document):
        if not isinstance(value, dict):
            continue
        probes = value.get("probes")
        if not isinstance(value.get("publicCameraIds"), list) or not isinstance(probes, list):
            continue
        for probe in probes:
            if not isinstance(probe, dict) or id(probe) in seen_probe_objects:
                continue
            seen_probe_objects.add(id(probe))
            camera_id = first_value(probe, ("cameraId", "id"))
            characteristics_error = probe.get("characteristicsError")
            if characteristics_error is not None:
                # durationMillis spans the full open probe and is not a separately
                # measured characteristics duration.
                characteristics_record = dict(probe)
                characteristics_record.pop("durationMillis", None)
                characteristics_record.pop("durationMs", None)
                output.append(make_observation(
                    source,
                    "CHARACTERISTICS",
                    "getCameraCharacteristics",
                    "ERROR",
                    characteristics_record,
                    characteristics_error,
                    default_caller,
                    camera_id=camera_id,
                ))
            open_error = probe.get("openError")
            if open_error is not None:
                stage = "OPEN_CONNECT"
                operation = "openCamera"
                _, characteristics_message, _ = error_fields(characteristics_error)
                _, open_message, _ = error_fields(open_error)
                if characteristics_message and open_message == characteristics_message and "getCameraCharacteristics" in open_message:
                    stage = "OPEN_PREFLIGHT"
                    operation = "openCamera characteristics preflight"
                output.append(make_observation(
                    source,
                    stage,
                    operation,
                    "ERROR",
                    probe,
                    open_error,
                    default_caller,
                    camera_id=camera_id,
                ))
    return output


def extract_json_object(line: str) -> Any | None:
    text = line.strip()
    if not text:
        return None
    candidate_slice = text[text.find("{"):text.rfind("}") + 1] if "{" in text and "}" in text else ""
    for candidate in (text, candidate_slice):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def unwrap_event(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if value.get("type") == "send" and isinstance(value.get("payload"), dict):
        return value["payload"]
    message = value.get("message")
    if isinstance(message, dict) and message.get("type") == "send" and isinstance(message.get("payload"), dict):
        return message["payload"]
    if isinstance(value.get("payload"), dict) and "kind" in value["payload"]:
        return value["payload"]
    return value if "kind" in value or "stage" in value else None


def event_stage(kind: str, event: dict[str, Any]) -> tuple[str, str] | None:
    mapping = {
        "camera-id-list-error": ("ENUMERATION", "getCameraIdList"),
        "get-characteristics-error": ("CHARACTERISTICS", "getCameraCharacteristics"),
        "open-camera-error": ("OPEN_CONNECT", "openCamera"),
        "ndk-open-camera-return": ("OPEN_CONNECT", "ACameraManager_openCamera"),
        "camera-device-error": ("OPEN_CONNECT", "CameraDevice.StateCallback.onError"),
        "create-session-error": ("SESSION_CONFIGURATION", "createCaptureSession"),
        "session-configure-failed": ("SESSION_CONFIGURATION", "onConfigureFailed"),
        "submit-request-error": ("REQUEST_SUBMISSION", "submitCaptureRequest"),
        "capture-failed": ("REQUEST_SUBMISSION", "CaptureFailure"),
    }
    if kind in mapping:
        return mapping[kind]
    stage = event.get("stage")
    if isinstance(stage, str) and stage in STAGES:
        return stage, str(event.get("operation") or kind or "unknown")
    return None


def event_observations(
    source: SourceInput,
    events: Iterable[dict[str, Any]],
    default_caller: CallerIdentity,
) -> list[ErrorObservation]:
    output: list[ErrorObservation] = []
    for event in events:
        kind = str(event.get("kind", ""))
        stage_operation = event_stage(kind, event)
        if stage_operation is None:
            continue
        stage, operation = stage_operation
        error = first_value(event, ("error", "exception", "failure", "thrown", "message"))
        namespace: str | None = None
        code: int | None = None
        if kind == "camera-device-error":
            namespace = "CameraDevice.StateCallback.error"
            code = to_int(first_value(event, ("errorCode", "code")))
        elif kind == "capture-failed":
            namespace = "CaptureFailure.reason"
            code = to_int(first_value(event, ("reason", "failureReason")))
        elif kind == "ndk-open-camera-return":
            code = to_int(first_value(event, ("status", "code")))
            namespace = "camera_status_t"
            if code == 0:
                continue
        elif isinstance(error, dict):
            reason = to_int(first_value(error, ("cameraAccessReason", "reason")))
            if reason is not None:
                namespace = "CameraAccessException.reason"
                code = reason
        if error is None and code is None:
            continue
        output.append(make_observation(
            source,
            stage,
            operation,
            "ERROR",
            event,
            error if error is not None else {"message": f"nonzero status {code}"},
            default_caller,
            namespace=namespace,
            code=code,
            camera_id=first_value(event, ("cameraId", "physicalCameraId")),
        ))
    return output


def load_source(source: SourceInput, default_caller: CallerIdentity) -> list[ErrorObservation]:
    if not source.path.is_file():
        raise AnalysisError(f"input not found: {source.path}")
    text = source.path.read_text(encoding="utf-8", errors="replace")
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        events: list[dict[str, Any]] = []
        for line in text.splitlines():
            event = unwrap_event(extract_json_object(line))
            if event is not None:
                events.append(event)
        if not events:
            raise AnalysisError(f"no JSON events found in {source.path}")
        return event_observations(source, events, default_caller)

    observations = probe_observations(source, document, default_caller)
    events = [
        event
        for _path, value in walk(document)
        if (event := unwrap_event(value)) is not None
    ]
    observations.extend(event_observations(source, events, default_caller))
    return deduplicate(observations)


def observation_key(observation: ErrorObservation) -> str:
    payload = dataclasses.asdict(observation)
    payload.pop("source_path", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def deduplicate(observations: Iterable[ErrorObservation]) -> list[ErrorObservation]:
    output: list[ErrorObservation] = []
    seen: set[str] = set()
    for observation in observations:
        key = observation_key(observation)
        if key not in seen:
            seen.add(key)
            output.append(observation)
    return output


def coverage(observations: list[ErrorObservation]) -> dict[str, Any]:
    def count(predicate: Any) -> int:
        return sum(1 for item in observations if predicate(item))

    total = len(observations)
    return {
        "observationCount": total,
        "withTimestamp": count(lambda item: item.timestamp_ms is not None),
        "withDuration": count(lambda item: item.duration_ms is not None),
        "withCallerPackage": count(lambda item: item.caller.package_name is not None),
        "withCallerUid": count(lambda item: item.caller.uid is not None),
        "withCallerPid": count(lambda item: item.caller.pid is not None),
        "withCallerTid": count(lambda item: item.caller.tid is not None),
        "withSelinuxDomain": count(lambda item: item.caller.selinux_domain is not None),
        "timingComplete": total > 0 and count(lambda item: item.timestamp_ms is not None or item.duration_ms is not None) == total,
        "callerIdentityComplete": total > 0 and count(
            lambda item: item.caller.package_name is not None and item.caller.uid is not None
        ) == total,
    }


def summarize(observations: list[ErrorObservation]) -> dict[str, Any]:
    by_stage = collections.Counter(item.stage for item in observations)
    by_category = collections.Counter(item.category for item in observations)
    by_family = collections.Counter(item.family for item in observations)
    by_camera = collections.Counter(item.camera_id or "<none>" for item in observations)
    return {
        "byStage": dict(sorted(by_stage.items())),
        "byCategory": dict(sorted(by_category.items())),
        "byFamily": dict(sorted(by_family.items())),
        "byCameraId": dict(sorted(by_camera.items())),
    }


def build_report(sources: list[SourceInput], default_caller: CallerIdentity) -> dict[str, Any]:
    observations: list[ErrorObservation] = []
    for source in sources:
        observations.extend(load_source(source, default_caller))
    observations = deduplicate(observations)
    if not observations:
        raise AnalysisError("inputs contain no supported camera error observations")
    return {
        "schemaVersion": 1,
        "sources": [dataclasses.asdict(source) | {"path": str(source.path)} for source in sources],
        "defaultCaller": dataclasses.asdict(default_caller),
        "observations": [dataclasses.asdict(item) for item in observations],
        "summary": summarize(observations),
        "coverage": coverage(observations),
        "codeNamespaces": {
            "CameraAccessException.reason": {
                str(code): {"name": value[0], "category": value[1]}
                for code, value in CAMERA_ACCESS_REASONS.items()
            },
            "CameraDevice.StateCallback.error": {
                str(code): {"name": value[0], "category": value[1]}
                for code, value in STATE_CALLBACK_ERRORS.items()
            },
            "CaptureFailure.reason": {
                str(code): {"name": value[0], "category": value[1]}
                for code, value in CAPTURE_FAILURE_REASONS.items()
            },
        },
        "evidenceBoundary": {
            "verified": "Exact API namespace, error code, exception type, message, timing, and caller fields are preserved when present.",
            "partiallyVerified": "Enforcing paths are AOSP/API anchors; an OEM build may add checks below or beside those paths.",
            "unknown": "Missing timing or caller fields remain explicit, and an error at one stage does not prove later stages were reached.",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Camera-open and session error taxonomy",
        "",
        "| Source | Stage | Camera | Category | Family | Namespace/code | Duration | Caller |",
        "|---|---|---:|---|---|---|---:|---|",
    ]
    for item in report["observations"]:
        caller = item["caller"]
        caller_text = caller.get("package_name") or caller.get("process_name") or "UNKNOWN"
        if caller.get("uid") is not None:
            caller_text += f" (uid {caller['uid']})"
        namespace = item.get("code_namespace") or "—"
        if item.get("code") is not None:
            namespace += f"/{item['code']}"
        duration = item.get("duration_ms") if item.get("duration_ms") is not None else "UNKNOWN"
        lines.append(
            f"| {item['source_label']} | {item['stage']} | `{item.get('camera_id') or '—'}` | "
            f"{item['category']} | `{item['family']}` | `{namespace}` | {duration} | {caller_text} |"
        )
    lines.extend([
        "",
        "## Coverage",
        "",
        f"- Observations: {report['coverage']['observationCount']}",
        f"- Timing complete: {report['coverage']['timingComplete']}",
        f"- Caller identity complete: {report['coverage']['callerIdentityComplete']}",
        "",
        "## Evidence boundary",
        "",
        f"- **VERIFIED:** {report['evidenceBoundary']['verified']}",
        f"- **PARTIALLY VERIFIED:** {report['evidenceBoundary']['partiallyVerified']}",
        f"- **UNKNOWN:** {report['evidenceBoundary']['unknown']}",
        "",
    ])
    return "\n".join(lines)


def write_output(path_text: str | None, text: str) -> None:
    if path_text is None:
        return
    path = Path(path_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sources = [parse_source(value) for value in args.inputs]
    default_caller = CallerIdentity(
        package_name=args.caller_package,
        uid=args.caller_uid,
        selinux_domain=args.caller_selinux_domain,
        role=args.caller_role,
    )
    try:
        report = build_report(sources, default_caller)
    except (OSError, AnalysisError) as error:
        print(f"camera error analysis failed: {error}", file=sys.stderr)
        return 2
    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)
    write_output(args.json_path, json_text)
    write_output(args.markdown_path, markdown_text)
    if not args.json_path and not args.markdown_path:
        sys.stdout.write(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
