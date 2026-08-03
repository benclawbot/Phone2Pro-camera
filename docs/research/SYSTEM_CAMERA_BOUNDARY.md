# Android System-camera Boundary

Status: target-confirmed classification for IDs `2`–`5`, cross-referenced with current AOSP CameraService and official Android system-camera documentation.

This note records the standard Android contract and the target evidence relevant to CAM-052, CAM-080, CAM-081, CAM-083, CAM-085 and CAM-086. Nothing-specific conclusions still require package, provider and stock-process traces.

## Target device evidence

The daylight routing diagnostic queried numeric camera IDs `0` through `31` through `CameraManager.getCameraCharacteristics()`.

- Public IDs: `0` and `1`.
- IDs `2`, `3`, `4` and `5` are recognized by CameraService but rejected with `CameraAccessException`, reason `CAMERA_ERROR (3)`.
- The service message for each is:

```text
Unable to retrieve cameracharacteristics for system only device <id>
```

The same IDs failed the ordinary-app open probe because characteristic access was rejected before a useful session could be constructed.

This is stronger than an unknown-ID failure. It confirms that the target framework classifies IDs `2`–`5` as system-only camera devices for the diagnostic caller.

Source artifact:

- `phone2pro-daylight-lens-routing-20260803_092933_170.json`
- SHA-256: `a4ba4f653490dc927f260a03b0a3b455589b17a020461738327c4270370d9d41`

## Standard Android contract

A camera HAL marks a device as a system camera by advertising:

```text
ANDROID_REQUEST_AVAILABLE_CAPABILITIES_SYSTEM_CAMERA
```

CameraProviderManager classifies provider devices into:

```text
PUBLIC
SYSTEM_ONLY_CAMERA
HIDDEN_SECURE_CAMERA
```

A `SYSTEM_ONLY_CAMERA` is visible only to processes that pass the `android.permission.SYSTEM_CAMERA` check and is intentionally excluded from ordinary third-party discovery.

Primary references:

- https://source.android.com/docs/core/camera/system-cameras
- https://android.googlesource.com/platform/frameworks/av/+/master/services/camera/libcameraservice/common/CameraProviderManager.h
- https://android.googlesource.com/platform/frameworks/av/+/master/services/camera/libcameraservice/CameraService.cpp

## Required application permissions

System-camera access requires both:

```text
android.permission.CAMERA
android.permission.SYSTEM_CAMERA
```

The current AOSP framework manifest defines `SYSTEM_CAMERA` as hidden/System API with protection level:

```text
system|signature|role
```

Official Android implementation guidance also requires an eligible application to be allowlisted in device-specific privileged-permission configuration. An ordinary Play-distributed or sideloaded APK cannot obtain this access merely by declaring the permission.

Primary references:

- https://android.googlesource.com/platform/frameworks/base/+/main/core/res/AndroidManifest.xml
- https://source.android.com/docs/core/camera/system-cameras

## CameraService enforcement points

AOSP does not enforce the distinction only in `CameraManager.getCameraIdList()`. CameraService applies caller-sensitive filtering and rejection at multiple points:

1. Status/listener updates for a system-only camera are skipped when the caller lacks `SYSTEM_CAMERA`.
2. Client-facing camera lists exclude system-only devices for unauthorized callers.
3. Characteristic and camera-info retrieval reject an unauthorized system-only ID.
4. Device connection rejects system-camera use before normal Camera2 operation proceeds.
5. Normal `CAMERA` permission remains required for an application that is authorized for system cameras.

Therefore, guessing or reflecting the hidden numeric ID does not bypass the boundary.

The target exception text matches AOSP's system-camera rejection path, providing strong evidence that the standard enforcement model or a close OEM derivative is active on the tested build.

## Current target topology

| ID | Framework classification | Leading role | Role confidence |
|---|---|---|---|
| `0` | public | rear main/public route | confirmed |
| `1` | public | front route | confirmed |
| `2` | system-only | ultrawide candidate | supported, not traced |
| `3` | system-only | telephoto candidate | supported, not traced |
| `4` | system-only | SAT/logical rear candidate | supported, not traced |
| `5` | system-only | portrait/composite candidate | supported, not traced |

Stock Expert mode independently confirms real 15 mm, 24 mm and 50 mm optical outputs. It does not yet prove which CameraDevice endpoint is opened for each output.

## Two remaining routing classes

### Direct system-camera route

Nothing Camera holds `SYSTEM_CAMERA` or an equivalent OEM authorization and opens IDs `2`, `3`, `4` or `5`.

Examples:

```text
0.6× -> ID 2
1×   -> ID 0
2×   -> ID 3
```

or:

```text
0.6× / 1× / 2× -> logical ID 4
```

with a separate physical-sensor selection state.

### Public-ID vendor/SAT route

Nothing Camera opens public ID `0`, then selects a sensor below Android's public logical-camera contract through session parameters, proprietary initialization, CameraFlex/multicam, seamless sensor scenarios, another Binder service or provider/HAL-native state.

These classes can coexist. For example, ID `4` may be a system-only logical SAT camera that still requires route-specific MediaTek session configuration.

## Evidence required from the target build

Collect and retain:

```text
dumpsys package com.nothing.camera
pm path com.nothing.camera
cmd appops get com.nothing.camera
APK manifest and signing certificate
privapp-permissions XML entries
role-holder output where applicable
CameraService client/open traces
provider device metadata and device kind
```

Confirm specifically:

- whether Nothing Camera requests `android.permission.SYSTEM_CAMERA`;
- whether the package dump reports it granted;
- whether the APK is installed under `system`, `system_ext`, `product` or `vendor`;
- whether it is privileged, platform-signed or receives a qualifying role;
- which allowlist or role grants access;
- whether IDs `2`–`5` advertise the system-camera capability at provider/HAL level;
- which ID the stock process actually opens for each Expert route.

`tools/device/run-expert-route-trace.sh` collects the package and CameraService evidence, while `tools/trace/analyze-expert-routing-bundles.py` classifies the resulting route pattern and privilege indicators.

## Consequences for the replacement application

### If stock Expert opens IDs `2`, `3` or `4`

A normal unprivileged replacement APK cannot reproduce that direct route under the standard Android contract. Deployment classes must remain separate:

1. **Ordinary application:** public ID `0` and any verified public vendor/SAT mechanism.
2. **OEM/system deployment:** legitimate system/signature/role grant plus required allowlist.
3. **User-modified device:** custom-ROM or rooted system integration, implemented as a separate backend with separate installation and safety requirements.
4. **Stock-camera handoff:** launches the official application but is not a complete replacement and does not provide in-process frame access.

### If stock Expert always opens public ID `0`

System-camera permission is not the immediate routing gate. Investigation moves to session parameters, proprietary initialization, CameraFlex/multicam, seamless sensor scenarios, Binder services or native/provider configuration.

## Widget-launch implication

The failed exported widget focal route does not by itself demonstrate a permission failure. After launch, camera operations execute under the Nothing Camera process identity, not the external caller's package identity. Stronger explanations are internal state restoration, route eligibility, initialization order, camera/session recreation or a missing controller transition.

## Decision rules

- Do not classify auxiliary-lens access as impossible until the controlled stock trace identifies the opened camera ID and the first route-specific session/native state.
- Do not classify a direct system-camera route as available to the production ordinary APK unless that package identity can pass CameraService's permission and connection checks on the target build.
- Do not treat a system-only ID's numerical discovery as access.

## Confidence

- IDs `2`–`5` are system-only devices for the ordinary diagnostic caller: **C4 — Confirmed**.
- Ordinary third-party direct access is blocked at CameraService on the tested build: **C4 — Confirmed**.
- Exact physical/logical role of IDs `2`–`5`: **C2 — Supported but unresolved**.
- Stock direct-open versus public/vendor routing: **C1 — Active hypothesis pending controlled trace**.
