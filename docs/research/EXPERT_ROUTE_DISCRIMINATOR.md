# Expert Lens-routing Discriminator

Status: active plan for CAM-024, CAM-026, CAM-042, CAM-043 and CAM-047.

## Established facts

1. Stock Expert mode produces three optical outputs:
   - 0.6×: 1.64 mm / 15 mm equivalent / 3264 × 2448.
   - 1×: 5.56 mm / 24 mm equivalent / 4080 × 3072.
   - 2×: 7.1 mm / 50 mm equivalent / 4096 × 3072.
2. Public Camera2 exposes only IDs `0` and `1`.
3. CameraService recognizes IDs `2`, `3`, `4` and `5` as system-only devices.
4. Public ID `0` zooming remains on the main sensor and performs a crop.
5. The stock app's exported widget focal strings enter Nothing Camera, but the tested 15/24/50 mm external launches remained on the 24 mm route.
6. The leading physical-sensor map is main `s5kgn9sp`, ultrawide `gc08a8`, telephoto `ov50d40`, front `gc16b3c`.

## Two remaining architecture classes

### A. Direct system-camera route

Nothing Camera has system-camera authorization and opens a system-only device:

```text
0.6× -> open ID 2
1×   -> open ID 0 or logical ID 4
2×   -> open ID 3
```

A variant is that the app always opens system-only logical ID `4`, whose hidden physical devices include the three rear sensors.

Evidence that would confirm this class:

- PackageManager grants `android.permission.SYSTEM_CAMERA`, a qualifying role or an equivalent OEM privilege.
- Java/native hooks observe `openCamera("2")`, `openCamera("3")`, `openCamera("4")` or another system-only ID.
- CameraService connect records identify those IDs under the Nothing Camera UID/package.
- Privileged characteristics for ID `4` expose logical/physical relationships.

### B. Public-ID vendor/SAT route

Nothing Camera opens public ID `0`, then configures an OEM logical route through session parameters, vendor metadata, proprietary initialization or another camera service:

```text
open ID 0
  + SAT / CameraFlex / seamless / physical-status session configuration
  -> active rear sensor selected below Camera2's public logical-camera contract
```

Evidence that would confirm this class:

- Hooks observe only `openCamera("0")` while optical routes change.
- Session configuration differs before `configureStreams` for 0.6×, 1× and 2×.
- Routing-relevant vendor keys or proprietary requests differ causally.
- Provider/HAL traces report different sensor scenarios or physical sensor state under the same framework ID.

These classes can coexist. For example, ID `4` may be a system-only logical SAT camera configured further by vendor session metadata.

## What the widget failure means

The widget route executes inside the stock camera process after launch. Therefore, the external caller's lack of `SYSTEM_CAMERA` permission is not by itself a sufficient explanation for the resulting 24 mm capture; the camera process retains its own identity and grants.

The failure instead prioritizes application-state and ordering explanations:

- the focal extra is parsed after a camera/session route has already been fixed;
- the parser changes a UI/manual focal state but not the lens-routing state object;
- fresh-launch initialization overwrites the requested state;
- a later eligibility check rejects auxiliary selection for widget/shortcut launches;
- the lens change needs an internal event sequence, camera reopen or session recreation not triggered by the exported path;
- required proprietary initialization is tied to an internal controller transition rather than the final focal value alone.

## Camera availability evidence limitation

The third-party diagnostic observed public ID `0` availability transitions while Nothing Camera captured through all three lenses. This does not prove that the stock app opened ID `0` for every route:

- ordinary callbacks do not enumerate the system-only IDs;
- opening a system logical camera can reserve or conflict with a related public device;
- the stock app may close and reopen a public or system logical endpoint between steps.

Availability events are timing anchors, not route identity evidence.

## Minimal decisive collection

### Package privilege

Collect:

```text
dumpsys package com.nothing.camera
pm path com.nothing.camera
cmd appops get com.nothing.camera
privapp permission XML entries
role holders where supported
APK manifest and signing certificate
```

Decision:

- granted `SYSTEM_CAMERA` substantially raises the direct-system route probability;
- absence from a basic manifest is not sufficient—runtime grants, role protection and OEM framework changes still require examination.

### Java Camera2 hook

For each fresh process launch, capture:

1. `CameraManager.getCameraCharacteristics(id)`
2. every `CameraManager.openCamera(...)` overload
3. `CameraDevice.createCaptureSession(...)`
4. `SessionConfiguration.setSessionParameters(...)`
5. `OutputConfiguration.setPhysicalCameraId(...)`
6. `CaptureRequest.Builder.set(...)`
7. `CaptureRequest.Builder.setPhysicalCameraKey(...)`

Run separate controlled traces for 0.6×, 1× and 2×.

### Service/provider trace

Correlate the app trace with:

- CameraService connect/disconnect and client records;
- Binder transaction identity;
- provider device name and device kind;
- `configureStreams` metadata;
- per-request vendor metadata;
- active sensor/scenario results.

## Routing-key priority list

Capture every key, but prioritize changes in:

```text
android.control.zoomRatio
android.scaler.cropRegion
android.lens.focalLength
com.mediatek.configure.setting.initrequest
com.mediatek.configure.setting.proprietaryRequest
com.mediatek.cameraflex.flexibleCapabilities
com.mediatek.insensorzoomfeature.*
com.mediatek.seamlessfeature.*
com.mediatek.multicamfeature.*
com.mediatek.streamingfeature.pipDevices
com.mediatek.streamingfeature.tnrOffByPhysicalIds
com.mediatek.control.capture.remosaicenable
com.mediatek.control.capture.seamless.remosaicenable
com.nothing.camera.*
nothing.camera.*
```

## Differential interpretation

| Observed open ID | Session differences | Leading interpretation |
|---|---|---|
| `2`, `0`, `3` | minor | direct physical system cameras |
| always `4` | physical ID/status differs | system logical SAT camera |
| always `0` | routing vendor/session keys differ | public-ID vendor/SAT route |
| always `0` | no Camera2 metadata difference | separate Binder/native service or in-process native configuration |
| route IDs differ only after internal UI action | exported parser/state transition incomplete |

## Completion criterion

The routing mechanism is considered reproduced only when a minimal implementation can select a target optical sensor under controlled positive and negative tests, and the output is verified by focal length, geometry and scene field of view. Logging a candidate key or opening a candidate ID is not sufficient on its own.
