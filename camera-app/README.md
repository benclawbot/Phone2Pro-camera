# Phone2Pro Replacement Camera

Status: production bootstrap, version `0.1.0`.

This standalone Android project starts the replacement camera application without waiting for the unresolved auxiliary-lens route. It implements the verified ordinary-app baseline while keeping lens routing pluggable and explicit.

## Current functionality

- Camera permission flow.
- CameraX preview bound to the verified public rear main camera ID `0`.
- MediaStore JPEG capture under `Pictures/Phone2Pro`.
- Bottom-left latest-photo thumbnail that opens the exact image in the system viewer.
- `Quick`, `Auto` and `Max Detail` product controls.
- Explicit 0.6×, 1× and 2× route controls.
- Runtime public-camera capability inventory through Camera2 interop.
- No Internet permission and no cloud processing.

The first implementation is intentionally honest about unfinished processing:

- `Quick` uses CameraX's low-latency single-frame policy.
- `Auto` uses the quality-oriented single-frame baseline while the adaptive burst pipeline is developed.
- `Max Detail` uses the same single-frame baseline while alignment, merge and super-resolution are developed.

The UI reports those states instead of presenting unfinished multi-frame processing as active.

## Lens policy

Only the verified 24 mm-equivalent public main route is enabled by the initial backend.

The 0.6× and 2× controls remain visible but report `Unavailable`. They are not silently mapped to a crop of the main sensor. This preserves the product rule that digital zoom must never masquerade as an optical ultrawide or telephoto route.

Backends are selected through:

```text
OpticalRoute
  -> RouteNegotiator
     -> ordered RouteBackend capability decisions
        -> CameraSessionController binder
```

Current backend:

```text
public-main-camera2
  route: 1× / 24 mm equivalent
  mechanism: PUBLIC_CAMERA
  Camera2 ID: 0
```

Planned optional backends remain isolated:

- verified public MediaTek/Nothing SAT adapter;
- authorized OEM/system-camera adapter;
- rooted/custom-ROM integration;
- official-camera handoff.

A backend is not enabled until its capability check and output verification are build-specific and evidence-backed.

## Build

Requirements:

- JDK 17
- Android SDK 36
- Build Tools 36.0.0
- Gradle 9.5.0

```bash
gradle -p camera-app testDebugUnitTest lintDebug assembleDebug
```

APK:

```text
camera-app/app/build/outputs/apk/debug/app-debug.apk
```

The GitHub Actions workflow `.github/workflows/camera-app-android.yml` runs tests, lint and assembly and publishes the debug APK as a temporary workflow artifact.

## Source layout

```text
app/src/main/java/com/phone2pro/camera/
  MainActivity.java
  backend/
    PublicMainBackend.java
  capture/
    CameraSessionController.java
  core/
    CaptureProfile.java
    DeviceCapabilitySnapshot.java
    OpticalRoute.java
    RouteBackend.java
    RouteDecision.java
    RouteMechanism.java
    RouteNegotiator.java
    RouteSupport.java
```

## Initial tests

`RouteNegotiatorTest` verifies:

- the main route selects the public Camera2 backend;
- ultrawide does not fall back to a digital crop;
- a future higher-priority verified vendor backend can supersede a lower-priority handoff backend.

## Next implementation slices

1. Persist and restore app mode and last verified route.
2. Query output sizes and select a known-safe preview/JPEG combination.
3. Add focus/metering gestures, orientation handling and capture-state feedback.
4. Add frame/result correlation and structured diagnostic bundles.
5. Implement burst acquisition, frame scoring and gyro timestamp capture.
6. Add optional auxiliary-lens backends only after the stock route is reproduced and its privilege boundary is known.
