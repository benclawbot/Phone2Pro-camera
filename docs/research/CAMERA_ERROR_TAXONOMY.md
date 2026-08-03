# Camera-open and session error taxonomy

Status: executable Camera2 lifecycle taxonomy for CAM-083.

## Purpose

The same integer has different meanings in different Android camera APIs. For
example:

```text
CameraAccessException reason 4
  -> CAMERA_IN_USE

CameraDevice.StateCallback error 4
  -> ERROR_CAMERA_DEVICE
```

The taxonomy therefore records the API namespace, lifecycle stage, exception
type, message, timing, caller identity and enforcing-path evidence rather than
classifying a bare number.

## Run

Analyze the controlled numeric camera probe and attach its known caller identity:

```bash
python3 tools/trace/analyze-camera-error-taxonomy.py \
  ordinary=/private/camera_open.json \
  --caller-package com.phone2pro.camera \
  --caller-uid 10123 \
  --caller-selinux-domain u:r:untrusted_app:s0 \
  --caller-role ordinary \
  --json /private/camera-error-taxonomy.json \
  --markdown /private/camera-error-taxonomy.md
```

Multiple diagnostic JSON or JSON-lines/Frida logs may be supplied. Embedded
caller and timing fields override the command-line defaults.

## Lifecycle stages

| Stage | Examples |
|---|---|
| `ENUMERATION` | camera ID list and availability visibility |
| `CHARACTERISTICS` | `getCameraCharacteristics()` |
| `OPEN_PREFLIGHT` | an open probe stopped by its own characteristics check |
| `OPEN_CONNECT` | CameraService connection or CameraDevice state callback |
| `SESSION_CONFIGURATION` | stream/session construction and `onConfigureFailed` |
| `REQUEST_SUBMISSION` | repeating/capture request submission and `CaptureFailure` |

A failure at one stage does not establish that a later stage was reached.

## Required category separation

The analyzer emits distinct categories for:

- `SECURITY`;
- `DISCONNECTED`;
- `IN_USE`;
- `MAX_CAMERAS`;
- `INVALID_ARGUMENT`;
- `DEVICE_SPECIFIC`;
- `SERVICE`;
- `CONFIGURATION`;
- `REQUEST_FAILURE`;
- `TIMEOUT`;
- `UNKNOWN`.

## Galaga baseline

The ordinary diagnostic record currently establishes:

- IDs `2`–`5`: `SECURITY / SYSTEM_CAMERA_PERMISSION` during characteristics;
- their open entries: the same security error during `OPEN_PREFLIGHT`, not an
  independently reached connect rejection;
- IDs `6`–`15`: `INVALID_ARGUMENT / CAMERA_ID_NOT_FOUND`;
- public IDs `0` and `1`: opened successfully and therefore absent from the
  error-only observation list.

The exact system-only message is anchored to AOSP
`CameraService::shouldRejectSystemCameraConnection`. The generic
`CameraAccessException` reason `3` must not overwrite this more specific error
signature with a vague device-error classification.

## Timing and caller identity

Every observation preserves available:

```text
timestampMs / elapsedRealtimeMillis
durationMs / durationMillis
package name and role
UID, PID and TID
process name
SELinux domain
```

The report contains explicit timing and caller-identity coverage counters.
Absent fields remain `UNKNOWN`; they are not inferred from a filename or a
neighboring experiment.

## Evidence classification

### VERIFIED

API namespaces, exact codes, exception types, messages, recorded timings and
caller fields are copied from the source evidence. Exact system-only and
unknown-device strings are classified separately.

### PARTIALLY VERIFIED

AOSP/API symbols identify the expected enforcement or reporting path. The OEM
framework, provider or HAL may add checks that are not represented by the
public error.

### UNKNOWN

A public exception does not by itself identify the exact vendor HAL line or
prove that later session/request stages ran. Those claims require synchronized
framework, service and HAL evidence.
