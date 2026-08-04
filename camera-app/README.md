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

## Capture mode policy

`CaptureProfile.plan(CaptureEnvironment)` now exposes a deterministic future-pipeline contract without changing the current CameraX execution path.

```text
Quick       1..1 frames
Auto        1..6 frames
Max Detail  1..12 frames
```

The plan records the exact frame count, exposure strategy, processing stages, active degradation reasons, requested/effective mode, natural rendering constraints, and user-facing summary. Motion, low light, thermal state and memory pressure are explicit strongly typed inputs.

Latency budgets are design targets with `HYPOTHESIS` confidence until measured on Galaga hardware. Critical thermal or memory pressure falls back to Quick. High motion suppresses fragile HDR/super-resolution work. Constrained resources cap frame count rather than failing unpredictably.

Natural rendering constraints remain active in every mode:

```text
PRESERVE_NATURAL_COLOR
PROTECT_HIGHLIGHTS
PREFER_DEGHOSTING_OVER_DETAIL
CONSERVATIVE_SHARPENING
AVOID_SYNTHETIC_TEXTURE
```

The complete contract is documented in `docs/architecture/CAPTURE_MODE_POLICY.md`.

## Lens policy

Only the verified 24 mm-equivalent public main route is enabled by the initial backend.

The 0.6× and 2× controls remain visible but report `Unavailable`. They are not silently mapped to a crop of the main sensor. This preserves the product rule that digital zoom must never masquerade as an optical ultrawide or telephoto route.

Every `OpticalRoute` now owns an evidence-backed `LensIdentity` containing:

```text
physical focal length
35 mm-equivalent focal length
optional aperture
crop factor
per-field and aggregate evidence confidence
source evidence note
```

The verified Galaga focal geometry is recorded for 0.6×, 1× and 2×. Exact aperture values are currently `UNKNOWN` and remain absent rather than being guessed. Because geometry is verified while aperture is unknown, the aggregate identity is `PARTIALLY_VERIFIED`.

Route transport and image rendering are independent:

```text
RouteMechanism
  PUBLIC_CAMERA
  PUBLIC_VENDOR_SAT
  SYSTEM_CAMERA
  STOCK_CAMERA_HANDOFF

RouteRendering
  OPTICAL
  IN_SENSOR
  DIGITAL
  UNAVAILABLE
```

A public Camera2 backend can therefore report an optical main route or an explicitly digital crop without confusing either result with how the endpoint was reached.

Backends are selected through:

```text
OpticalRoute
  -> RouteNegotiator
     -> ordered RouteBackend capability decisions
        -> CameraSessionController binder
```

Installed backend policies:

```text
galaga-system-camera2
  routes: 0.6× → ID 2, 1× → ID 0, 2× → ID 3
  mechanism: SYSTEM_CAMERA
  rendering: OPTICAL
  state: fail-closed until an independent authorization probe succeeds

public-main-camera2
  route: 1× / 24 mm equivalent
  mechanism: PUBLIC_CAMERA
  rendering: OPTICAL
  Camera2 ID: 0
```

Concrete IDs are owned by backend route tables rather than `OpticalRoute`. The Galaga table records verified static stock-camera configuration, while `SystemEndpointAccess` independently determines whether the current process is authorized to bind the endpoint. The production policy is unverified and always denies system-camera access, so current ordinary-app behavior remains unchanged.

Planned optional backends remain isolated:

- verified public MediaTek/Nothing SAT adapter;
- authorized OEM/system-camera session binder and access probe;
- rooted/custom-ROM integration;
- official-camera handoff.

A backend is not enabled until its capability check, rendering classification and output verification are build-specific and evidence-backed.

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
    GalagaManualRouteTable.java
    GalagaSystemCameraBackend.java
    PublicMainBackend.java
    SystemEndpointAccess.java
    UnverifiedSystemEndpointAccess.java
  capture/
    CameraSessionController.java
  core/
    CaptureEnvironment.java
    CaptureModePolicy.java
    CapturePlan.java
    CaptureProfile.java
    CaptureStage.java
    DegradationReason.java
    DeviceCapabilitySnapshot.java
    EvidenceConfidence.java
    ExposureStrategy.java
    LensIdentity.java
    OpticalRoute.java
    RenderingConstraint.java
    RouteBackend.java
    RouteDecision.java
    RouteMechanism.java
    RouteRendering.java
    ResolvedCameraEndpoint.java
    RouteNegotiator.java
    RouteSupport.java
```

## Initial tests

Routing and identity tests verify:

- the main route selects the public optical Camera2 backend;
- ultrawide does not fall back to a digital crop;
- optical, in-sensor and digital rendering remain separate from backend transport;
- a digital route can never report optical rendering;
- the recovered Galaga table resolves `2`, `0` and `3` only after an independent authorization probe succeeds;
- the default system-endpoint policy fails closed;
- focal geometry, crop factor, aperture availability and confidence remain internally consistent;
- missing aperture evidence cannot claim verified confidence.

`CaptureModePolicyTest` additionally verifies every combination of mode, motion, light, thermal and memory state remains within deterministic bounds, retains natural rendering constraints, and follows the documented degradation ladder.

## Next implementation slices

1. Persist and restore app mode and last verified route.
2. Query output sizes and select a known-safe preview/JPEG combination.
3. Add focus/metering gestures, orientation handling and capture-state feedback.
4. Add frame/result correlation and structured diagnostic bundles.
5. Implement burst acquisition, frame scoring and gyro timestamp capture against the mode-policy contracts.
6. Implement the `SystemEndpointAccess` probe and direct Camera2 session binder only after the privilege boundary is reproduced lawfully.
