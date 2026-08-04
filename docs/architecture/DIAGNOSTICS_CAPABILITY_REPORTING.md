# Testability, diagnostics and capability reporting

Status: executable diagnostic contracts for CAM-111.

The production application can report camera configuration and failures without exporting user photos. Diagnostics remain disabled unless explicitly enabled.

## Evidence classification

- **VERIFIED:** Capture-report fields, redaction boundaries, feature-flag states, error categories, safe firmware plans and tests are implemented.
- **PARTIALLY VERIFIED:** The standalone diagnostics application already validates the current firmware; the production capture controller has not yet emitted every new report type.
- **UNKNOWN:** Final JSON serialization format, long-term bundle retention and device-specific firmware regression thresholds remain unverified.

## Capture reports

`CaptureDiagnosticReport` contains:

- stable report ID;
- build fingerprint and app version;
- backend ID;
- optical route;
- route mechanism and optical/in-sensor/digital rendering classification;
- capture profile;
- stream roles, formats, dimensions and buffer counts;
- redacted session, repeating-request and still-request key descriptions;
- route, session, shutter, image, processing and persistence timings;
- optional typed user-facing error.

Reports have no field for image bytes, thumbnails, content URIs or file paths. Configuration entries reject URI and storage-path summaries.

## Timings

`TimingReport` uses non-negative monotonic durations for:

```text
route resolution
session configuration
shutter
image availability
processing
persistence
```

The total is derived with checked arithmetic. Clock-domain calibration remains governed by the burst/alignment contracts.

## Feature flags

Feature decisions use:

- `ENABLED`
- `DISABLED`
- `BLOCKED_BY_BUILD`
- `BLOCKED_BY_CAPABILITY`
- `BLOCKED_BY_PROBE`
- `BLOCKED_BY_RESOURCE`

Every decision records evidence confidence and a reason. An enabled feature cannot have `UNKNOWN` confidence.

## User-visible errors

Application errors are normalized into:

- hardware unavailable;
- permission denied;
- thermal limit;
- unsupported feature;
- resource limit;
- session failure;
- capture failure;
- storage failure;
- processing failure;
- internal error.

Each error provides a redacted message and retryability flag. Backend exception class names and opaque numeric values may be retained in local developer traces only after privacy review; users receive the stable category and actionable message.

## Internal hooks

`DiagnosticHook` observes capture reports and feature decisions. `NoopDiagnosticHook` is the production default and retains nothing. An opt-in implementation must pass reports through the privacy/redaction policy before persistence or export.

## Bug bundles

`BugBundle` records:

- bundle ID;
- protocol version;
- capture reports;
- feature-flag reports.

It rejects empty bundles and reports containing user pixels. Protocol versions allow future readers to reproduce the exact schema and scenario without inferring fields from prose.

## New-firmware validation

`FirmwareValidationPlan.safeBaseline()` includes only bounded, safe-by-default modules:

- public capability inventory;
- camera-open probe;
- stream/session matrix;
- request-template inventory;
- redacted capture trace;
- bounded burst benchmark;
- vendor-key inventory.

Guarded vendor writes and system-camera open probes are excluded. They require explicit risk consent and a separate versioned protocol.

A firmware run must record the exact build fingerprint and diagnostic application version. Results become a new baseline rather than silently replacing prior evidence.

## Current integration boundary

The standalone diagnostics application already exercises most safe baseline modules. The production controller still uses callback strings for several runtime events and will migrate incrementally to `CaptureDiagnosticReport` and `UserFacingError`. This architecture must not be described as complete runtime bug-bundle export until that adapter and device test are implemented.
