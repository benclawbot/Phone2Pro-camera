# Baseline Capability Map

Status: initial working baseline. This document records what the current diagnostic artifact directly supports and separates that from hypotheses requiring deeper reverse engineering.

## Device and build

- Manufacturer/brand: Nothing.
- Model: `A001`.
- Device/board: `Galaga`.
- Product: `GalagaEEA`.
- SoC: MediaTek `MT6878`.
- Captured diagnostic build: Android 16, SDK 36, security patch 2026-06-01.
- Nothing Camera package: `com.nothing.camera`, observed version `16.1.01.93.20`.

## Public camera enumeration

| Public ID | Facing | Independently openable | Hardware level | Physical IDs exposed |
|---|---:|---:|---|---|
| `0` | rear | yes | `LEVEL_3` | none |
| `1` | front | yes | `LEVEL_3` | none |

The absence of public physical IDs is a property of these published CameraCharacteristics. It does not identify how Nothing Camera's internal Expert route reaches the auxiliary sensors.

## Rear public camera `0`

### Optics and sensor metadata

- Advertised focal length: 5.56 mm.
- Advertised aperture: f/1.879.
- Pixel array: 4080 × 3072.
- Active array: 4080 × 3072.
- Physical sensor size: 8.16 × 6.14 mm.
- Minimum focus distance: 10 dioptres.
- Optical stabilization modes: off/on.
- Zoom ratio range: 1.0–10.0.
- Exposure-time range: 100 μs to 32 s.
- Sensitivity range: ISO 100–16000; maximum analog sensitivity 1600.

### Major capabilities

- Backward compatible.
- Manual sensor.
- Manual post-processing.
- Read sensor settings.
- RAW.
- Burst capture.
- Private reprocessing.
- YUV reprocessing.
- Constrained high-speed video.
- Stream use cases.
- Colour-space profiles.
- Camera Extensions: Night.

### Maximum observed outputs

- One RAW output.
- Three processed outputs.
- One stalling output.
- Full-resolution RAW: 4080 × 3072.
- Full-resolution YUV/JPEG paths are advertised, subject to stream-combination validation.

## Vendor-feature surface

The public metadata inventory exposes request, result, characteristic or session keys for the following subsystem families:

- Face/scene analysis and third-party face metadata.
- 3D noise reduction.
- HDR, VHDR, multi-stream HDR and frame-sync controls.
- MFNR/MFB and AIS.
- Continuous-shot capture.
- MediaTek 3A controls and detailed AE/AWB/AF results.
- EIS and preview EIS.
- High-frame-rate video and HDR10+ support.
- ZSL, postview and early-capture notifications.
- ISP metadata and tuning requests.
- RAW processing, packed RAW, RAW10 conversion and remosaic controls.
- Background pre-release and ImageReader integration.
- Flash calibration/customization.
- Slow-motion video.
- AOV service pipeline.
- CameraFlex flexible capabilities.
- Video AI noise reduction.
- Camera-preview compression.
- In-sensor zoom status and enable hints.
- Seamless sensor scenarios, forced sensor mode and cell crop/full-sensor configuration.
- Nothing Super EIS, SOIS gains and custom tuning hints.

Exposure of a key name is not proof that arbitrary values are accepted from an ordinary app. Every key requires call-site tracing and controlled write testing.

## Current routing evidence

### Internal stock-camera behaviour

Prior controlled Expert-mode captures support three distinct optical routes:

| Expert button | Expected internal route | Physical focal length | 35 mm equivalent |
|---|---:|---:|---:|
| 0.6× | ultrawide / ID 2 | 1.64 mm | 15 mm |
| 1× | main / ID 0 | 5.56 mm | 24 mm |
| 2× | telephoto / ID 3 | 7.1 mm | 50 mm |

The exact internal call chain remains the primary reverse-engineering target.

### External widget focal-launch audit

Nothing Camera's widget contract accepted focal strings such as `15mm`, `24mm` and `50mm`, and the decompiled parser was understood to normalize rear IDs to SAT ID 4 before applying manual-mode focal selection. However, the audited external captures remained 5.56 mm / 24 mm-equivalent. This establishes that the tested external entry route did not reproduce the internal Expert lens state on the observed build.

It does **not** establish that the internal routing mechanism is unavailable to a replacement app. Remaining candidates include:

- additional in-process state established before the parser runs;
- non-exported controller calls;
- session parameters or proprietary request initialization;
- vendor Camera2 keys with specific ordering or dependencies;
- a hidden logical/system camera opened under privileged identity;
- Binder or native service interaction;
- package-signature, UID or SELinux gating.

## Highest-priority unknowns

1. Exact 0.6×/1×/2× UI-to-HAL call chain in Expert mode.
2. Camera/session identity actually opened by the stock app for each route.
3. Session parameters established before capture requests.
4. Vendor tags that change sensor scenario, active sensor or SAT policy.
5. JNI/native methods involved in route selection.
6. Framework, CameraService, provider or HAL checks on package identity.
7. Whether a normal app can reproduce the route with the correct complete configuration.
8. If not, the exact enforcing boundary and best supported fallback architecture.
