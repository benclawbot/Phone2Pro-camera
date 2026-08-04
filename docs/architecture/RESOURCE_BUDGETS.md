# Memory, latency, battery and thermal budgets

Status: executable resource targets for CAM-109.

These limits make capture behavior deterministic and benchmarkable. They are initial MT6878 design targets, not measured Galaga performance claims.

## Evidence classification

- **VERIFIED:** Budget fields, degradation behavior, compliance evaluation and unit tests are implemented.
- **HYPOTHESIS:** Numeric memory, latency, sustained-rate and cooldown targets remain hypotheses until physical benchmarks calibrate them.
- **UNKNOWN:** Actual per-format memory use, power draw, thermal rise and sustained throughput on the target build remain unknown.

## Baseline mode budgets

| Mode | Frames | In-flight buffers | Max frame bytes | Intermediate bytes | Queue | Shutter target | Processing target | Sustained rate | Cooldown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Quick | 1 | 3 | 32 MiB | 48 MiB | 4 | 350 ms | 1.5 s | 20/min | 0 ms |
| Auto | 6 | 8 | 32 MiB | 192 MiB | 3 | 500 ms | 5 s | 8/min | 1 s |
| Max Detail | 12 | 14 | 32 MiB | 384 MiB | 1 | 800 ms | 12 s | 3/min | 5 s |

Maximum working set is defined as:

```text
max frame bytes × in-flight buffers + intermediate bytes
```

The buffer ceiling must hold the complete planned burst. Queue depth is independent from frame buffers and represents captures awaiting or undergoing processing.

## Memory headroom

A budget may use at most 60% of currently available application memory. This reserves headroom for preview, CameraX/Camera2, the UI, encoder, MediaStore and system pressure.

If the requested mode does not fit:

```text
Max Detail → Auto → Quick → block capture
```

Capture is blocked only when the Quick working set cannot fit. The user summary reports insufficient memory instead of attempting an unstable allocation.

## Thermal ladder

- `NOMINAL`: requested mode and baseline rate.
- `WARM`: Max Detail becomes Auto; sustained rate is capped at 4/min and cooldown is at least 3 s.
- `HOT`: all modes become Quick; sustained rate is capped at 2/min and cooldown is at least 10 s.
- `CRITICAL`: Quick only, 1/min, at least 30 s cooldown.

The runtime may impose stricter Android thermal restrictions. These values are application policy ceilings, not a substitute for platform thermal APIs.

## Battery ladder

- `CHARGING` or `NORMAL`: no battery-specific reduction.
- `LOW`: Max Detail becomes Auto; sustained rate is capped at 4/min and cooldown is at least 5 s.
- `CRITICAL`: Quick only, 1/min, at least 30 s cooldown.

Thermal, battery and memory restrictions compose; the strictest effective mode/rate/cooldown wins.

## Testable measurements

`ResourcePerformanceSample` records:

- actual frame count;
- peak in-flight buffers;
- peak working-set bytes;
- queued captures;
- shutter latency;
- processing latency;
- captures observed in the previous minute.

`ResourceBudgetCompliance` reports independent violations for every dimension. A value equal to the target passes; a value above it fails.

This supports CI fixtures, device benchmark ingestion and future firmware comparisons without changing the budget contract.

## Relationship to capture policy

`CaptureModePolicy` selects scene-dependent work. `ResourceBudgetPolicy` constrains that work using device state. The final acquisition plan must satisfy both:

```text
frames = min(scene-plan frames, resource-budget frames)
queue/buffer/memory/latency = resource budget ceilings
```

No mode may allocate beyond the effective resource budget even when scene analysis requests more work.

## Current implementation boundary

The policy and evaluator are implemented, but the CameraX single-frame runtime does not yet report peak buffers, working set, battery draw or measured latency into these contracts. Physical benchmarks must replace hypothetical numeric targets with versioned verified values rather than silently changing them.
