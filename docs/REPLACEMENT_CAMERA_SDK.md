# Replacement camera SDK and engineering guide

This guide is the implementation entry point for the CMF Phone 2 Pro (`galaga`) replacement camera. It translates the committed capability matrix, routing specification, and portable architecture contracts into contributor rules and examples.

The machine-readable companion is [`spec/replacement-camera-sdk-guide.v1.json`](../spec/replacement-camera-sdk-guide.v1.json). The capability and routing sources of truth are [`spec/camera-capability-matrix.v1.json`](../spec/camera-capability-matrix.v1.json) and [`spec/camera-routing-spec.v1.json`](../spec/camera-routing-spec.v1.json).

## Evidence and enablement rules

Use these terms precisely:

- **Verified contract**: the interface, validation, state transition, or fallback behavior is implemented and tested in the repository. It does not necessarily prove physical-device quality or access.
- **Partially verified**: a bounded implementation exists, but device integration, coverage, or measurements remain incomplete.
- **Experimental adapter**: disabled by default. It requires an exact build allowlist, a safe probe, and a public fallback before it can affect production behavior.
- **Unknown**: do not infer a value, endpoint, sensor, or effect. Link the active research issue and fail closed.

A feature may be enabled only when its module record permits production use and the current firmware matches the declared build policy. A verified Java contract does not convert an unknown auxiliary camera route or vendor value into verified device behavior.

## Build compatibility

### Observed Galaga builds

The safe baseline is public rear camera ID `0`, the public CameraX/direct-Camera2 binders, private on-device processing, and the committed portable contracts. Auxiliary optical routes and MediaTek/Nothing controls remain disabled unless the exact build fingerprint and an isolated probe are both verified.

### Future or untested builds

Start with all vendor and auxiliary features disabled. Run the capability, route, privacy, and firmware-validation diagnostics again. Do not carry forward a vendor allowlist merely because the device codename is unchanged.

Build variance is tracked by CAM-059 (#54). Diagnostic revalidation is defined by the firmware validation plan and CAM-111.

## Architecture map

### Backend and routing

Use `RouteBackend` for capability evaluation and endpoint resolution. Every backend exposes the shared lifecycle, error taxonomy, and normalized metadata contract through `CameraBackendContract`.

Optical intent is represented by `OpticalRoute`, not by a guessed Camera2 ID. `RouteRendering` and `RoutePresentation` must disclose whether the result is optical, in-sensor, digital, a stock handoff, or unavailable.

Source references:

- `docs/architecture/CAMERA_BACKEND_CONTRACTS.md`
- `docs/CAMERA_ROUTING_SPEC.md`
- `camera-app/app/src/main/java/com/phone2pro/camera/core/RouteBackend.java`

### Capture sessions and requests

Construct a `CaptureSessionPlan` before allocating Android surfaces. Keep `SESSION`, `REPEATING`, and `STILL` parameters in their declared scopes. Use `SessionRecreationDecision` to determine whether a plan change requires rebuilding the session.

Use `CaptureRequestPlanner` for generation-bound still bursts, cancellation, and backend modifiers. Use `SessionRecoveryPolicy` for bounded retries. Pair image and metadata timestamps through `TimestampCorrelator` before processing.

CameraX public plans must not claim arbitrary session parameters, physical outputs, reprocessing inputs, or vendor keys. Direct Camera2 owns those capabilities when verified. Vendor keys belong only to the isolated vendor adapter.

Source reference: `docs/architecture/CAPTURE_SESSION_REQUEST_ENGINE.md`.

### Quick, Auto, and Max Detail

Use `CaptureProfile` and `CaptureModePolicy` to derive deterministic work. Resource conditions are applied through `ResourceBudgetPolicy`.

The degradation ladder is:

1. Max Detail
2. Auto
3. Quick
4. block capture only when Quick cannot fit safely

The policy is executable, but numerical memory, latency, battery, and thermal targets remain hypotheses until Galaga benchmarks replace them. Do not present those targets as measured performance.

Source reference: `docs/architecture/RESOURCE_BUDGETS.md`.

### Burst, motion, scoring, and alignment

Use `FrameMetadata`, `TimestampDomain`, `ClockCalibration`, `FrameScorer`, `ReferenceSelector`, and `FrameAligner` as replaceable contracts. Implementations must preserve local motion fields and confidence/validity masks.

Do not enter multi-frame processing when timestamps are uncalibrated or alignment confidence is insufficient. The conservative fallback is the selected reference frame.

Source reference: `docs/architecture/BURST_ALIGNMENT_CONTRACTS.md`.

### Rendering and encoding

Use `RenderPipelinePlan` to validate stage ordering, color spaces, transfer functions, bit depths, and metadata propagation before processing. Each stage is replaceable through `RenderStageProcessor`.

Use `ConservativeFallbackPolicy` when alignment, ghosting, or detail artefacts are detected. The pipeline may mask unreliable regions, disable risky stages, or collapse to the reference frame. Natural output takes priority over forcing super-resolution or sharpening.

Source reference: `docs/architecture/IMAGE_RENDERING_PIPELINE.md`.

### UI and lifecycle

Keep `CameraBackendSnapshot` immutable and separate from `CameraUiState`. Apply user events through `CameraUiReducer` and combine the states in `CameraScreenModel`.

The shutter may become ready after a durable asset save while earlier computational work remains queued. Route labels must remain truthful; a crop from the main sensor is not “Optical 2×.”

Source reference: `docs/architecture/UI_STATE_ARCHITECTURE.md`.

### Storage and gallery

Reserve a hidden MediaStore row, write/process while pending, and publish only after complete durable bytes exist. Use `AssetLifecyclePolicy` and `AssetRecoveryPolicy`; never expose a partial file.

Use `MetadataPrivacyPolicy.privateByDefault()` and derive an explicit `MetadataWritePlan`. Location, device identity, diagnostics, and processing XMP require affirmative policy choices.

Source reference: `docs/architecture/STORAGE_GALLERY_CONTRACTS.md`.

### Privacy and security

The production manifest requests camera access only, disables backup, and denies cleartext traffic. Processing stages declare `NetworkPolicy.DENIED`.

Temporary frames, intermediates, metadata, diagnostics, and crash context have explicit lifetimes. Diagnostic exports are opt-in and exclude pixels, thumbnails, content URIs, paths, location, serials, user text, and arbitrary metadata values by default.

Source reference: `docs/architecture/PRIVACY_SECURITY.md`.

### Diagnostics

Use `CaptureDiagnosticReport`, `FeatureFlagReport`, typed `UserFacingError` categories, and `BugBundle` for pixel-free reports. Production may use `NoopDiagnosticHook` when diagnostics are disabled.

Firmware validation is safe by default. Vendor writes and system-camera opens require explicit risk consent and a guarded protocol.

Source reference: `docs/architecture/DIAGNOSTICS_CAPABILITY_REPORTING.md`.

## Verified main camera session

<a id="verified-main-camera-session"></a>

**Classification: VERIFIED INTERFACE.** This example uses the public main route and no vendor keys. Stream sizes still need to be selected from the verified runtime capability snapshot for the current build.

```java
import com.phone2pro.camera.capture.CaptureSessionPlan;
import com.phone2pro.camera.capture.RequestParameter;
import com.phone2pro.camera.capture.RequestParameterScope;
import com.phone2pro.camera.capture.SessionBinderKind;
import com.phone2pro.camera.capture.StreamRole;
import com.phone2pro.camera.capture.StreamSpec;
import com.phone2pro.camera.core.CaptureProfile;
import com.phone2pro.camera.core.OpticalRoute;
import com.phone2pro.camera.core.ResolvedCameraEndpoint;
import com.phone2pro.camera.core.RouteMechanism;
import com.phone2pro.camera.imaging.TimestampDomain;

import java.util.Arrays;
import java.util.Collections;

ResolvedCameraEndpoint endpoint = new ResolvedCameraEndpoint(
        "0",
        RouteMechanism.PUBLIC_CAMERA,
        "Verified public rear endpoint on the observed Galaga build"
);

CaptureSessionPlan sessionPlan = new CaptureSessionPlan(
        1L,
        "camera2-public",
        SessionBinderKind.CAMERA2_DIRECT,
        OpticalRoute.MAIN,
        endpoint,
        CaptureProfile.AUTO,
        TimestampDomain.CAMERA_SENSOR,
        Arrays.asList(
                StreamSpec.publicOutput(StreamRole.PREVIEW, "PRIVATE", 1920, 1080, 3),
                StreamSpec.publicOutput(StreamRole.STILL_JPEG, "JPEG", 4080, 3072, 2)
        ),
        Collections.emptyList(),
        Collections.emptyList(),
        Collections.<RequestParameter<?>>singletonList(
                new RequestParameter<>(
                        "android.jpeg.quality",
                        Integer.class,
                        95,
                        RequestParameterScope.STILL
                )
        )
);
```

Before binding, compare this plan with the active plan. On a transient failure, follow `SessionRecoveryPolicy`; do not create an unbounded reopen loop. If the public configuration becomes invalid on a new build, return a typed unsupported/session error and rerun diagnostics.

## Verified private metadata plan

<a id="verified-private-metadata-plan"></a>

**Classification: VERIFIED INTERFACE.** Optional sensitive fields are omitted unless policy explicitly enables them.

```java
import com.phone2pro.camera.storage.MetadataPrivacyPolicy;
import com.phone2pro.camera.storage.MetadataWritePlan;

MetadataPrivacyPolicy privacy = MetadataPrivacyPolicy.privateByDefault();
MetadataWritePlan writePlan = MetadataWritePlan.from(privacy);
```

The fallback is omission, not inferred consent. A missing location fix must not delay or fail an otherwise valid capture when location metadata is disabled.

## Experimental vendor adapter

<a id="experimental-vendor-adapter"></a>

**Classification: EXPERIMENTAL ADAPTER — DISABLED BY DEFAULT.** Do not paste a discovered vendor key into portable request code.

A vendor feature may be considered only in this order:

1. identify the exact manufacturer, model, device, and build fingerprint;
2. create a feature policy allowlisted for that exact build;
3. run an isolated probe that distinguishes accepted, effective, rejected, timed out, mismatched, and unknown outcomes;
4. preserve `SESSION` versus `PER_FRAME` scope;
5. attach a known public Camera2 fallback before execution;
6. revalidate the applied result at runtime;
7. fall back on every non-verified outcome.

No MediaTek/Nothing feature is currently enabled merely because the adapter contract exists. Active work is tracked by CAM-060 through CAM-071 and the guarded probe issue CAM-062.

## Experimental auxiliary route

<a id="experimental-auxiliary-route"></a>

**Classification: EXPERIMENTAL ADAPTER — UNAVAILABLE TO PRODUCTION.** The stock camera demonstrates 0.6× and 2× optical outputs, but the ordinary-app endpoint, logical/SAT policy, sensor scenario, and caller-identity requirements are unresolved.

A new route backend must not resolve ultrawide or telephoto until it has:

- an exact-build mechanism;
- positive and negative reproduction tests;
- active-sensor/output evidence;
- a bounded timeout and cleanup path;
- a transparent fallback;
- no dependency on an unapproved privilege or identity bypass.

Until then, return unavailable, offer an explicit stock-camera handoff, or offer a main-camera digital crop labelled as digital. Never label the fallback as auxiliary optical capture.

## Error and fallback policy

Use typed errors instead of framework exception text in product state. Distinguish at minimum:

- permission denial;
- hardware/device fatal error;
- camera busy or disconnected;
- unsupported stream/session configuration;
- thermal or memory degradation;
- capture, processing, storage, and internal errors.

Fallbacks must preserve truthfulness and data safety. They may reduce work, use the reference frame, recreate public ID `0`, omit optional metadata, or keep an asset hidden. They must not enable an unverified vendor key, expose a partial file, or mislabel digital output.

## Contributor workflow

Before implementing a feature:

1. read the capability-matrix row and route-spec entry;
2. locate the module record in `spec/replacement-camera-sdk-guide.v1.json`;
3. verify the current build scope;
4. decide whether the work uses a verified interface or an experimental adapter;
5. define the public fallback first;
6. keep Android framework objects behind the binder/adapter boundary;
7. add unit tests for valid, rejected, timeout, mismatch, cancellation, and fallback paths;
8. update the matrix, route spec, guide manifest, and active issues when evidence changes;
9. pass evidence validation and the Android unit/lint/assembly workflow when Android files change.

Do not repeat platform discovery already captured in the specifications. Open the linked research issue when a required value remains unknown rather than filling the gap from assumption.

## Required validation

Run the repository validation suite and, for this guide specifically:

```sh
python3 tools/validate-sdk-guide.py
```

The validator checks module and example vocabulary, repository paths, build scopes, guide anchors, fallbacks, unknown-issue links, and the rule that experimental modules/examples remain disabled and explicitly labelled.
