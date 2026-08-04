# Camera backend and capability-negotiation contracts

Status: executable backend specification for CAM-100.

The application selects optical routes through build-aware runtime backends. Android framework objects remain in capture/session adapters; portable code consumes typed capabilities, lifecycle, errors and normalized metadata.

## Evidence classification

- **VERIFIED:** Runtime/build-aware route negotiation, explicit unsupported-route decisions, the shared backend contract and unit tests are implemented.
- **PARTIALLY VERIFIED:** The public CameraX binder currently implements the practical lifecycle; future vendor and system-camera binders must emit all shared lifecycle/status events when they become authorized.
- **UNKNOWN:** No ordinary-app vendor or privileged auxiliary binder is production-enabled.

## Capability discovery

`DeviceCapabilitySnapshot` records manufacturer, model, device and currently public camera IDs at runtime. Backends evaluate each `OpticalRoute` against that snapshot.

Device-specific endpoint IDs remain inside backend route tables. `OpticalRoute` contains physical field-of-view identity, not Camera2 identifiers.

`RouteSupport` always returns either:

- available, with transport mechanism, optical/in-sensor/digital rendering and an evidence reason; or
- unavailable, with an explicit reason.

The negotiator never silently substitutes a digital main-camera crop for an unavailable optical auxiliary lens.

## Shared backend contract

Every `RouteBackend` exposes `CameraBackendContract` containing:

- backend ID;
- build-aware capability requirement;
- runtime discovery requirement;
- one shared lifecycle graph;
- stable backend error categories;
- normalized metadata fields.

The default contract is complete and inherited by current backends. A future backend may narrow metadata only when the missing field is genuinely unavailable and documented.

## Lifecycle

The portable lifecycle is:

```text
IDLE
→ DISCOVERING
→ READY
→ OPENING
→ OPEN
→ CONFIGURING
→ STREAMING
↔ CAPTURING
→ CLOSING
→ CLOSED
```

Failures transition to `ERROR`; supported recovery paths enter `RECOVERING` and then return to ready/opening or close. Direct jumps such as `IDLE → CAPTURING` or `CLOSED → STREAMING` are invalid.

`BackendStatusSnapshot` records backend ID, lifecycle state, monotonic timestamp and a non-empty detail. `ERROR` requires a normalized error category; non-error states cannot carry one.

## Errors

All backends map native/framework failures into:

- unsupported;
- permission;
- disconnected;
- in use;
- maximum cameras;
- configuration;
- request;
- timeout;
- thermal;
- resource;
- device;
- service;
- internal.

The diagnostics/UI layer maps these stable categories to user-visible messages without depending on CameraX or Camera2 exception classes.

## Metadata

`NormalizedBackendMetadata` is immutable and framework-independent. Standard fields include:

- frame number and sensor timestamp;
- exposure, sensitivity and frame duration;
- focus distance, focal length and aperture;
- white balance and crop;
- active route and optional physical ID;
- orientation;
- normalized error category.

Values remain typed. Requesting a field with the wrong expected type fails instead of coercing or silently dropping it.

Vendor/native metadata stays inside adapters until it is mapped to a standard field or an explicitly versioned vendor extension contract.

## Android interoperability boundary

`RouteBackend` does not expose CameraDevice, CameraCaptureSession, CameraX UseCase or vendor objects. It resolves a safe endpoint and contract. The capture/session adapter owns:

- framework object creation;
- stream/session setup;
- request submission;
- callback translation;
- lifecycle/status emission;
- metadata normalization.

This permits CameraX public capture today and future direct Camera2/vendor binders without contaminating application features.

## Current implementation boundary

Public Camera2 ID 0 is functional. The Galaga system-camera table is recorded but remains fail-closed until authorization is verified. The contract does not grant access or claim an unavailable binder exists.
