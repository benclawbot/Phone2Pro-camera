# Capture session and request engine

## Scope

This package defines the portable contract between product capture policy and Android camera binders. It does not expose `CameraDevice`, `CameraCaptureSession`, `CaptureRequest`, `Surface`, `ImageReader`, or CameraX use-case objects.

## Binder boundary

`SessionBinderKind` selects one of three implementations:

- `CAMERAX_PUBLIC` for verified public preview/still configurations;
- `CAMERA2_DIRECT` for public direct-Camera2 sessions that need explicit streams or request control;
- `CAMERA2_VENDOR_ADAPTER` for isolated, build-allowlisted vendor settings.

A CameraX public plan cannot promise arbitrary session parameters, physical outputs, reprocessing inputs, or vendor keys. Vendor keys are rejected unless the plan uses the isolated vendor adapter.

## Session planning and recreation

`CaptureSessionPlan` owns the backend, route, endpoint, profile, metadata clock domain, negotiated streams, and three parameter scopes:

- `SESSION` values require session construction;
- `REPEATING` values update preview/repeating requests;
- `STILL` values apply only to still requests.

`SessionRecreationDecision` compares active and requested plans. Backend, binder, endpoint, route, stream, session-parameter, or timestamp-domain changes require recreation. Repeating and still-request changes do not.

## Still bursts and modifiers

`CaptureRequestPlanner` creates an ordered `StillBurstPlan` bound to one session generation. Frames use contiguous indices and unique request IDs. Cancellation is checked before planning and between modifier applications.

`BackendRequestModifier` is the only portable extension point for backend-specific request changes. Every returned list is revalidated. The planner rejects:

- non-`STILL` parameters;
- duplicate keys;
- blank modifier IDs;
- preview/video templates for still bursts;
- vendor keys outside `CAMERA2_VENDOR_ADAPTER`;
- bursts above 64 frames.

Android binders map the validated portable parameters to framework key objects after planning.

## Transient failure recovery

`SessionRecoveryPolicy` maps stable failure categories to bounded actions:

- request timeout or capture failure: retry, then recreate the session, then fail;
- session configuration failure: bounded session recreation;
- foreground disconnect: bounded camera reopen;
- camera-in-use: bounded wait with capped exponential backoff;
- permission, unsupported configuration, and fatal device failures: fail immediately;
- user cancellation: stop without retry.

The policy does not loop indefinitely and never retries a permanent failure.

## Timestamp correlation

`ImageTimestamp` carries only request identity, frame number, timestamp, and clock domain. `TimestampCorrelator` pairs it with normalized `FrameMetadata` only when:

- frame numbers match;
- clock domains match and are known;
- absolute timestamp delta is within the declared tolerance.

A mismatch fails closed before the frame enters scoring, alignment, or rendering.

## Evidence boundary

The portable contracts, validation rules, recovery decisions, cancellation behavior, and timestamp correlation are implemented and unit tested. Android CameraX/Camera2 binder implementations, physical stream negotiation, real device retry thresholds, and measured image/result timestamp tolerances remain to be verified on Galaga hardware.
