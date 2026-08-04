# Merge, super-resolution and image-rendering pipeline

Status: executable interface specification for CAM-105.

This document defines modular contracts and conservative quality rules. It does not claim that the production application currently executes the multi-frame pipeline.

## Evidence classification

- **VERIFIED:** The types, validation rules, metadata behavior, stage order and fallback policy described here are implemented and unit tested.
- **HYPOTHESIS:** Algorithm implementations, thresholds, compute budgets and image-quality improvements remain design choices until benchmarked on Galaga hardware.
- **UNKNOWN:** The best Galaga-specific color matrices, denoise models, super-resolution kernels, tone curves and JPEG tuning remain unknown.

## Canonical order

```text
Input normalization
→ Demosaic
→ Alignment
→ Robust merge
→ Super resolution
→ Denoise
→ Color transform
→ Tone mapping
→ Natural sharpening
→ JPEG encoding
```

A `RenderPipelinePlan` requires strictly increasing stage order, compatible adjacent encodings and a final `ENCODING` stage. Robust merge requires an earlier alignment stage.

Optional product-mode plans may omit merge or super-resolution, but they may not reorder the remaining stages or hide an encoding mismatch.

## Color and precision

`ImageEncoding` separates:

- color space and primaries;
- transfer function;
- bit depth;
- integer versus floating-point representation.

Supported spaces currently include sensor-native linear, CIE XYZ D50, linear sRGB, linear Display P3, nonlinear sRGB and nonlinear Display P3.

Alignment, merge, super-resolution, denoise and color transformation require linear input at 12-bit precision or higher. Tone mapping is the explicit transition from scene-linear data to nonlinear display output. Sharpening and encoding preserve the declared display encoding.

The canonical JPEG plan uses:

```text
Sensor-native linear 16-bit
→ linear sRGB 16-bit
→ nonlinear sRGB 8-bit
→ JPEG
```

This is an interface default, not a claim that 16-bit intermediate buffers are already active in the application.

## Metadata propagation

`RenderMetadata` is immutable and strongly typed. Existing metadata cannot be dropped by a `RenderStageSpec`; stages may only preserve values and add derived values.

Standard propagation keys currently include:

- reference frame ID;
- source frame count;
- lens route ID;
- sensor timestamp.

Additional color transforms, crop, orientation, exposure, white-balance, calibration and provenance keys can be added without weakening existing type checks.

## Replaceable stages

Every `RenderStageProcessor`, `ArtifactDetector` and `ImageEncoder` exposes an `AlgorithmDescriptor` with a stable ID and version. This allows independent implementation, benchmark comparison and rollback.

A rendering stage returns:

- a new owned `RenderImage`;
- an `ArtifactReport` for the completed stage.

`ImageEncoder` is isolated from image processing and receives explicit JPEG quality, output gamut and metadata-privacy options.

## Artefact detection

The shared taxonomy covers:

- misalignment;
- ghosting;
- halos;
- ringing;
- highlight clipping;
- color shift;
- noise amplification;
- synthetic texture.

Each finding records normalized severity, evidence and an optional local mask. Local masks allow unreliable regions to be rejected without discarding stable parts of the frame.

## Conservative fallback ladder

The pipeline always sacrifices synthesized detail before natural scene structure:

1. Severe misalignment, ghosting or color instability: use the reference frame only.
2. Moderate local motion failure: mask unreliable regions.
3. Synthetic texture: disable super-resolution.
4. Halos or ringing: disable sharpening.
5. Noise amplification: reduce denoise strength rather than erase texture.
6. Highlight clipping: reapply highlight protection.
7. No material artefact: keep the result.

`KEEP_RESULT` cannot be combined with a fallback. `USE_REFERENCE_FRAME_ONLY` supersedes all other actions.

## Mandatory quality goals

Every mode inherits these goals:

- preserve natural color;
- preserve highlight detail;
- preserve local motion;
- avoid ghosting;
- avoid halos and ringing;
- avoid synthetic texture;
- retain real sensor texture;
- prefer the reference frame over unstable detail.

The current severity threshold is a testable design policy, not a device-validated image-quality metric.

## JPEG boundary

`JpegEncodingOptions` requires:

- quality from 1 through 100;
- nonlinear sRGB or Display P3 output;
- explicit location-metadata inclusion;
- explicit diagnostic-metadata inclusion.

Encoded bytes and metadata are immutable. Storage, pending MediaStore assets, EXIF/XMP mapping and crash recovery remain the responsibility of CAM-107.

## Current implementation boundary

The production application still captures a CameraX JPEG through the verified single-frame public route. These rendering interfaces are ready for independent implementations, but no merge, super-resolution, denoise or custom JPEG stage may be presented as active until integrated and verified on-device.
