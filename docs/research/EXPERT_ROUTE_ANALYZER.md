# Expert Route Bundle Analyzer

Status: implemented for CAM-024, CAM-040, CAM-042, CAM-045, CAM-060 and CAM-061.

`tools/trace/analyze-expert-routing-bundles.py` consumes the timestamped evidence directories produced by `tools/device/run-expert-route-trace.sh` and generates one conservative architecture decision.

## Inputs

The analyzer selects the newest bundle for each of these six slots:

| Route | Camera2 trace | Key/type trace |
|---|---|---|
| `06x` | required | required for full type coverage |
| `1x` | required | required for full type coverage |
| `2x` | required | required for full type coverage |

A Camera2 route is accepted only when `output-association-template.json` contains non-image metadata matching the established stock optical signature:

| Route | Physical focal length | Equivalent | Dimensions |
|---|---:|---:|---:|
| `06x` | 1.64 mm | 15 mm | 3264 × 2448 |
| `1x` | 5.56 mm | 24 mm | 4080 × 3072 |
| `2x` | 7.1 mm | 50 mm | 4096 × 3072 |

The analyzer does not read the photograph and does not accept the requested UI route as proof of the active lens.

## Run

```bash
python3 tools/trace/analyze-expert-routing-bundles.py \
  --root traces/expert-routing \
  --json traces/expert-routing/architecture.json \
  --markdown traces/expert-routing/architecture.md
```

Use `--strict` in a controlled research pipeline. It exits with status 2 when the six-run matrix is incomplete or the result still requires a lower-layer trace.

## Generated evidence

The JSON report includes:

- selected bundle path for every route and trace mode;
- optical-association checks and mismatches;
- Camera2 IDs opened by each verified route;
- physical output IDs when observed;
- route-specific MediaTek/Nothing key values;
- stock vendor-key Java/native type recovery coverage;
- `SYSTEM_CAMERA`, system-partition, privileged-package and camera app-op indicators;
- architecture classification, confidence and exact next action.

The Markdown report is a review-oriented summary of the same data.

## Classifications

### `direct-system-camera-route`

Verified routes open different Camera2 endpoints. The exact `2 / 0 / 3` sequence receives the highest confidence. The next step is to recover authorization and characteristics for the non-public IDs and test a minimal authorized direct-open implementation.

### `system-logical-sat-route`

All verified routes open system-only candidate ID `4`. The next step is to recover its logical/hidden-physical metadata and isolate the session or request state selecting each physical sensor.

### `public-id-vendor-sat-route`

All verified routes open public ID `0`, but physical IDs or routing-related vendor values differ. The next step is to reproduce the earliest route-specific session configuration using the exact target key type and working stock value.

### `lower-layer-route-unresolved`

All verified routes open public ID `0`, and the Java Camera2 observer finds no routing difference. The next step is JNI, Binder, CameraService/provider and HAL tracing around `configureStreams` and request submission.

### `incomplete`

At least one optical route lacks a verified association or an observed Camera2 open event. No implementation conclusion is emitted.

## Causality rule

A route-specific metadata value is a discriminator candidate, not proof that the value causes sensor selection. Causality requires a controlled reproducer that preserves the stock session setup while changing or removing only that candidate, followed by optical output verification.

## Automated tests

`tests/test_analyze_expert_routing_bundles.py` covers:

- exact direct system-camera routing;
- public ID `0` plus route-dependent vendor metadata;
- rejection of incomplete three-route evidence.

The repository validation workflow compiles the analyzer and runs the tests on every push and pull request.
