# System-only Camera IDs 2–5

Status: direct device finding, cross-referenced with AOSP CameraService.

## Device evidence

The daylight routing diagnostic queried numeric camera IDs `0` through `31` through `CameraManager.getCameraCharacteristics()`.

- Public IDs: `0` and `1`.
- IDs `2`, `3`, `4` and `5` are recognized by the camera service but rejected with `CameraAccessException`, reason `CAMERA_ERROR (3)`.
- The service message for each is:

```text
Unable to retrieve cameracharacteristics for system only device <id>
```

The same four IDs failed the explicit open probe before an open request could be completed because characteristics access was rejected.

This is stronger than a generic unknown-ID or unsupported-ID failure. It establishes that the target camera stack classifies IDs `2`–`5` as **system-only camera devices** for the caller used by the diagnostic application.

Source artifact:

- `phone2pro-daylight-lens-routing-20260803_092933_170.json`
- SHA-256: `a4ba4f653490dc927f260a03b0a3b455589b17a020461738327c4270370d9d41`

## AOSP enforcement path

Primary sources:

- https://android.googlesource.com/platform/frameworks/av/+/master/services/camera/libcameraservice/CameraService.cpp
- https://android.googlesource.com/platform/frameworks/base/+/main/core/res/AndroidManifest.xml

AOSP `CameraService::getCameraCharacteristics()` calls `shouldRejectSystemCameraConnection()` before retrieving metadata. That function rejects a HAL device classified as `SYSTEM_ONLY_CAMERA` when a non-system caller lacks system-camera permissions. The exact AOSP error text matches the target-device exception.

AOSP requires both:

- `android.permission.CAMERA`
- `android.permission.SYSTEM_CAMERA`

The framework manifest describes `SYSTEM_CAMERA` as a hidden System API permission with protection level `system|signature|role` on current AOSP. It is not an ordinary runtime permission available to a normal third-party application.

## Revised platform model

The previous hypotheses can now be narrowed:

| ID | Framework classification evidenced | Likely project role | Exact role confirmed? |
|---|---|---|---|
| `0` | public | rear public/main route | yes for public route |
| `1` | public | front route | yes |
| `2` | system-only | ultrawide candidate | no |
| `3` | system-only | telephoto candidate | no |
| `4` | system-only | SAT/logical rear candidate | no |
| `5` | system-only | portrait or other composite candidate | no |

The candidate roles come from prior stock-app static reasoning and Expert-mode observations. The system-only classification is confirmed; the mapping of each ID to a physical or logical role still requires privileged characteristics, APK tracing or provider/HAL metadata.

## Consequence for the replacement application

A conventional Play-distributed or sideloaded application cannot rely on opening IDs `2`–`5` directly unless the OEM changes their classification or grants an eligible system/signature/role permission path.

This does **not** yet prove that auxiliary optical capture is impossible for an ordinary app. Two materially distinct routes remain:

1. **Direct system-camera route:** Nothing Camera may hold `SYSTEM_CAMERA` and open IDs `2`, `3`, `4` or `5` directly.
2. **Public logical/vendor route:** Nothing Camera may open public ID `0` and select auxiliary sensors through proprietary session parameters, vendor metadata, or a service-owned pipeline.

The next decisive artifact is the stock camera package manifest and grant state. If `com.nothing.camera` holds `android.permission.SYSTEM_CAMERA`, direct ID opens become the leading explanation. If it does not, the session/vendor route becomes substantially more likely.

## Next tests

1. Capture `dumpsys package com.nothing.camera` and requested/granted permissions.
2. Decode the stock APK manifest and privapp allowlists.
3. Hook `CameraManager.openCamera()` and `getCameraCharacteristics()` inside Nothing Camera.
4. Compare fresh Expert 0.6×, 1× and 2× runs.
5. Inspect CameraService connect logs and package attribution.
6. Extract provider/HAL metadata for IDs `2`–`5` under a permitted/root diagnostic context.
7. Determine whether ID `4` is a system logical camera exposing IDs `0`, `2` and `3` as hidden physical devices.

## Confidence

- IDs `2`–`5` are known system-only devices for the ordinary caller: **C4 — Confirmed**.
- Ordinary third-party direct access is blocked at CameraService on the tested build: **C4 — Confirmed**.
- Exact lens/logical mapping of IDs `2`–`5`: **C2 — Supported but unresolved**.
- Stock application direct-open versus public/vendor routing: **C1 — Active hypothesis**.
