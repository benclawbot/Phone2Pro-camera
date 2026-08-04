# Quick, Auto and Max Detail capture policy

Status: executable product-mode contract for CAM-103.

The source of truth is `CaptureModePolicy`. This document describes the same deterministic rules; Android unit tests exercise every combination of motion, light, thermal and memory state.

## Evidence classification

### VERIFIED

The current application still uses CameraX single-frame capture for all three controls and reports that implementation state to the user.

### HYPOTHESIS

Frame counts, stage selection and latency budgets below are production design targets for the future burst pipeline. They are not measured MT6878 performance claims. They must remain `HYPOTHESIS` until device benchmarks verify them.

### UNKNOWN

Exact scene thresholds, exposure values, memory consumption, thermal trip points and image-quality breakpoints remain unknown until the corresponding acquisition and imaging stages run on Galaga hardware.

## Deterministic mode bounds

| Mode | Minimum frames | Maximum frames | Shutter target | Processing target | Nominal purpose |
|---|---:|---:|---:|---:|---|
| Quick | 1 | 1 | 350 ms | 1.5 s | Shortest predictable shutter path. |
| Auto | 1 | 6 | 500 ms | 5 s | Adaptive balance of motion, dynamic range, detail and latency. |
| Max Detail | 1 | 12 | 800 ms | 12 s | Aligned detail capture with conservative super-resolution when reliable. |

The latency targets are explicitly marked `HYPOTHESIS` in code.

## Nominal work

### Quick

- One automatic-exposure frame.
- No alignment, HDR merge or super-resolution.
- Natural color, highlight protection, conservative sharpening and texture restraint remain required.
- Low light does not silently turn Quick into a long burst; the mode continues to prioritize response.

### Auto

Nominal frame count by scene light:

| Light | Frames |
|---|---:|
| Bright | 3 |
| Normal | 4 |
| Low | 6 |

Multi-frame Auto uses frame scoring, motion estimation and alignment. HDR merge is enabled only with at least three frames and no high-motion condition. Auto never enables super-resolution.

### Max Detail

Nominal frame count by scene light:

| Light | Frames |
|---|---:|
| Bright | 8 |
| Normal | 10 |
| Low | 12 |

With nominal resources and manageable motion, Max Detail adds super-resolution to frame scoring, motion estimation, alignment, HDR merge, denoise, sharpening, color rendering, tone mapping and JPEG encoding.

## Exposure strategy

| Condition | Selected strategy |
|---|---|
| Quick or critical-resource fallback | `SINGLE_AUTO` |
| High motion | `SHORT_EXPOSURE_BURST` |
| Low light without high motion | `LOW_LIGHT_BRACKET` |
| Auto in normal/bright light | `BALANCED_BRACKET` |
| Max Detail in normal/bright light | `DETAIL_BURST` |

No concrete shutter time, ISO or EV spacing is asserted yet. Those values require capture-engine and sensor evidence.

## Degradation ladder

### Motion

- Moderate motion caps Auto at three frames and Max Detail at six frames.
- High motion caps both multi-frame modes at two frames.
- High-motion Max Detail becomes an Auto-compatible plan and disables HDR merge and super-resolution.
- Deghosting is preferred over synthetic detail in every mode.

### Thermal

- Warm caps Auto at four frames and Max Detail at eight frames.
- Hot caps Auto at two frames and converts Max Detail to a three-frame Auto-compatible plan.
- Critical thermal state falls back to one-frame Quick.

### Memory

- Constrained memory caps Auto at three frames and converts Max Detail to a four-frame Auto-compatible plan without super-resolution.
- Critical memory pressure falls back to one-frame Quick.

### Low light

- Quick remains one frame and explicitly prioritizes shutter response over low-light detail.
- Auto increases work to at most six aligned bracketed frames.
- Max Detail increases work to at most twelve frames only when motion and resources permit it.

## Natural rendering contract

Every plan retains these constraints:

```text
PRESERVE_NATURAL_COLOR
PROTECT_HIGHLIGHTS
PREFER_DEGHOSTING_OVER_DETAIL
CONSERVATIVE_SHARPENING
AVOID_SYNTHETIC_TEXTURE
```

A degradation may reduce frames or stages, but it may not remove these product-quality constraints.

## User-facing predictability

Each `CapturePlan` contains:

- requested and effective mode;
- exact frame count;
- exposure strategy;
- selected processing stages;
- active degradation reasons;
- latency targets and confidence;
- a user-readable summary.

When Max Detail cannot safely run super-resolution, the effective mode and reason are explicit rather than silently returning an apparently full-quality result.

## Current implementation boundary

`CaptureProfile.implementationStatus()` remains the UI source for what the application currently executes:

- Quick: single-frame low-latency CameraX baseline.
- Auto: single-frame quality baseline.
- Max Detail: single-frame quality baseline.

`CaptureProfile.plan(environment)` defines the future acquisition and processing contract. The application must not present the multi-frame plan as active until the capture engine implements and verifies it.
