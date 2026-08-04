# Burst, motion, scoring and alignment contracts

Status: executable interface specification for CAM-104.

These contracts define the boundary between camera acquisition and replaceable computational-photography algorithms. They do not claim that a multi-frame implementation is active in the production application.

## Evidence classification

- **VERIFIED:** The interface invariants and unit-tested behavior described here are implemented in the repository.
- **HYPOTHESIS:** Algorithm choices, score weights, pyramid depth, displacement limits and performance targets remain implementation choices until benchmarked on Galaga hardware.
- **UNKNOWN:** The exact Galaga gyroscope-to-camera clock relationship, OIS sample availability and calibration uncertainty remain unknown until measured.

## Timestamp contract

Every frame and motion sample declares a `TimestampDomain`:

- `CAMERA_SENSOR`
- `ELAPSED_REALTIME`
- `UPTIME`
- `WALL_CLOCK`
- `UNKNOWN`

`UNKNOWN` is rejected for frames and motion samples used by the pipeline. A `BurstSequence` requires one frame clock and one motion clock. When those clocks differ, construction fails unless a matching `ClockCalibration` is supplied.

`ClockCalibration` uses an affine mapping:

```text
target = targetAnchor + (source - sourceAnchor) * scale
```

The calibration also records uncertainty, evidence confidence and a provenance note. Wall-clock time may be retained for reporting but must not be used directly for frame alignment.

## Acquisition boundary

`FrameBuffer` is a framework-independent, read-only image owner. CameraX, Camera2, NDK and future native acquisition layers can adapt their buffers without exposing framework types to algorithms.

`BurstFrame` joins a buffer with `FrameMetadata`, including:

- frame number;
- sensor timestamp and domain;
- exposure time;
- sensitivity;
- frame duration;
- rolling-shutter skew;
- focal length.

`BurstSequence` joins ordered frames, motion samples and the optional motion-to-frame calibration.

## Motion inputs

`MotionSample` supports:

- gyroscope angular velocity;
- OIS lens position;
- explicitly unknown vendor motion signals.

Unknown vendor semantics remain labeled rather than being interpreted as gyroscope or OIS data.

## Scoring and reference selection

`FrameScorer` returns a transparent `FrameScore` with normalized components for:

- sharpness;
- motion stability;
- exposure quality;
- highlight retention;
- noise quality;
- total score.

`ReferenceSelector` is separate from the scorer, so selection policies can be benchmarked or changed without replacing quality measurement. Every implementation exposes an `AlgorithmDescriptor` containing a stable ID and version.

## Multi-scale alignment

`FrameAligner` accepts a reference frame, candidate frame, calibrated burst and `AlignmentRequest`. The request states:

- pyramid level count;
- maximum displacement;
- whether a motion prior may be used;
- minimum confidence.

`AlignmentResult` contains:

- a global 3×3 transform;
- a dense local `MotionField`;
- an alignment-confidence mask;
- a validity mask;
- pyramid levels used;
- residual error.

The local motion, confidence and validity grids must have identical dimensions. This supports deghosting, local rejection and conservative merge fallbacks instead of treating one global transform as universally valid.

## Replaceability and benchmarks

`FrameScorer`, `ReferenceSelector` and `FrameAligner` are independent interfaces. Each implementation is identified by `AlgorithmDescriptor` and can be measured through `AlgorithmBenchmark` using consistent work-unit accounting.

A benchmark result records implementation ID/version, work units, duration and time per work unit. Quality metrics and device resource measurements will be added by later benchmark issues; this contract intentionally does not invent Galaga performance.

## Required implementation behavior

- Reject unknown or inconsistent timestamp domains.
- Require explicit calibration before joining different frame and motion clocks.
- Preserve calibration uncertainty and evidence confidence.
- Keep buffers read-only and ownership explicit.
- Preserve local motion, confidence and validity masks.
- Keep scoring, selection and alignment independently replaceable.
- Never convert an unknown vendor motion signal into a standard sensor interpretation without evidence.

## Current implementation boundary

The production camera remains on the verified CameraX single-frame path. These contracts are ready for burst acquisition, scoring and alignment implementations, but none of those future stages may be displayed as active until image acquisition, timestamp correlation and output quality are verified on the device.
