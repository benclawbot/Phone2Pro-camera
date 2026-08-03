# System-camera filtering model

Status: executable separation of enumeration, characteristics and connection evidence for CAM-081.

## Why the stages are separate

Android applies caller-sensitive system-camera policy at more than one boundary:

1. provider devices are classified as `PUBLIC`, `SYSTEM_ONLY_CAMERA` or `HIDDEN_SECURE_CAMERA`;
2. unauthorized system-only IDs are omitted from client enumeration and status updates;
3. characteristics access rejects a recognized system-only ID when the caller lacks `SYSTEM_CAMERA`;
4. connection performs an independent system-camera rejection before normal Camera2 operation.

A diagnostic that calls `getCameraCharacteristics()` before `openCamera()` can fail at stage 3 and never independently exercise stage 4. Repeating the same characteristics exception in an `openError` field is therefore not connect-path evidence.

## Analyzer

```bash
python3 tools/device/analyze-system-camera-filtering.py \
  /private/camera_open.json \
  --json /private/system-camera-filtering.json \
  --markdown /private/system-camera-filtering.md
```

The input may be a focused `camera_open.json` record or a larger JSON document containing an object with `publicCameraIds` and `probes`.

## Target baseline result

For the controlled Galaga ordinary-app probe:

| IDs | Enumeration | Characteristics | Open/connect |
|---|---|---|---|
| `0`, `1` | public | readable | opened |
| `2`, `3`, `4`, `5` | not publicly listed | exact “system only device” rejection | blocked by the same characteristics preflight error; connect not independently observed |
| `6`–`15` | not publicly listed | unknown-device rejection | blocked by the same characteristics preflight error |

This distinguishes recognized system-only IDs from nonexistent IDs without overstating the connect evidence.

## AOSP anchors

- `CameraProviderManager::SystemCameraKind` defines `PUBLIC`, `SYSTEM_ONLY_CAMERA` and `HIDDEN_SECURE_CAMERA`.
- `CameraProviderManager::collectDeviceIdsLocked` separates public and system device IDs.
- `CameraService::shouldSkipStatusUpdates` suppresses caller-ineligible status visibility.
- `CameraService::shouldRejectSystemCameraConnection` checks the device kind and caller permission for characteristics and connection paths.
- `CameraService::connectHelper` applies the connection path independently.

Primary source locations:

```text
frameworks/av/services/camera/libcameraservice/common/CameraProviderManager.h
frameworks/av/services/camera/libcameraservice/common/CameraProviderManager.cpp
frameworks/av/services/camera/libcameraservice/CameraService.h
frameworks/av/services/camera/libcameraservice/CameraService.cpp
frameworks/base/core/java/android/hardware/camera2/CameraManager.java
```

## Evidence classification

### VERIFIED

IDs `2`–`5` are omitted from the public list and return the exact system-only characteristics rejection for the ordinary diagnostic caller. IDs `6` and above in the tested range return a distinct unknown-device error.

### PARTIALLY VERIFIED

The target error matches AOSP system-camera enforcement and the target behaves consistently with that contract. The OEM source running on the device has not yet been shown byte-for-byte identical to current AOSP.

### UNKNOWN

The existing ordinary-app open probe does not independently reach CameraService connection for IDs `2`–`5`; it records the same characteristics preflight exception. A permission-parity or privileged comparison run is required to observe the connect boundary directly.
