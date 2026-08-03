# CMF Phone 2 Pro Camera Platform Project

This repository documents and validates the complete camera platform of the CMF Phone 2 Pro (`A001`, `Galaga`) and turns that knowledge into the engineering specification for an on-device replacement camera application.

The central reverse-engineering question is how Nothing Camera routes Expert mode to the ultrawide, main and telephoto sensors, which firmware interfaces it invokes, and where the reproducibility or privilege boundary lies.

## Current status

The research backlog covers the public Android API, Nothing Camera APK, dynamic instrumentation, CameraService/Binder, MediaTek provider/HAL/native libraries, firmware configuration, kernel drivers, permissions, SELinux, vendor metadata, computational photography and the replacement application.

Work is active. The evidence repository, schemas, source index, build matrix, acquisition tools, static-analysis pipeline, controlled Expert trace runner, Camera2 observers and route classifier are in place.

## Confirmed device findings

- Device: Nothing/CMF Phone 2 Pro, model `A001`, codename `Galaga`, MediaTek `MT6878`.
- Baseline: Android 16 / SDK 36 / June 2026 security patch.
- Public Camera2 IDs: rear `0`, front `1`.
- CameraService recognizes IDs `2`, `3`, `4` and `5` as **system-only camera devices** for an ordinary application.
- Rear public ID `0` is Camera2 `LEVEL_3` with RAW, burst, private/YUV reprocessing, OIS and manual sensor/post-processing controls.
- Public zoom remains on the main 5.56 mm sensor and crops continuously; public 2× is not the stock 50 mm-equivalent optical route.
- Stock Expert mode produces three distinct optical outputs:
  - 0.6× — 1.64 mm physical / 15 mm equivalent / 3264 × 2448.
  - 1× — 5.56 mm physical / 24 mm equivalent / 4080 × 3072.
  - 2× — 7.1 mm physical / 50 mm equivalent / 4096 × 3072.
- The exported widget focal route entered the stock app but remained on the 24 mm output in the audited run. This is a launch-state failure, not evidence that the internal optical route is impossible.
- The target publishes 162 unique MediaTek/Nothing vendor keys across MFNR/AIS, HDR, 3A, ZSL, ISP tuning, in-sensor zoom, seamless scenarios, CameraFlex/multicam, stabilization and custom tuning families.

## Leading physical-sensor map

Target geometry and official Galaga/16b drivers strongly support these base-silicon candidates:

| Route | Leading sensor | Geometry match |
|---|---|---|
| rear main | Samsung `s5kgn9sp` | 8160 × 6144 → 4080 × 3072 |
| rear ultrawide | GalaxyCore `gc08a8` | 3264 × 2448 |
| rear telephoto | OmniVision `ov50d40` | 8192 × 6144 → 4096 × 3072 |
| front | GalaxyCore `gc16b3c` | 2320 × 1744 |

These are strong C3 correlations. Exact module-supplier variants and runtime binding still require DTBO, EEPROM, kernel-log or HAL evidence.

## Official source baseline

Nothing's official MT6878 source family has been resolved:

- `NothingOSS/android_kernel_6.1_nothing_mt6878`
- `NothingOSS/android_kernel_modules_nothing_mt6878`
- `NothingOSS/android_kernel_device_modules_6.1_nothing_mt6878`
- `NothingOSS/android_kernel_build_nothing_mt6878`

The first three expose `mt6878/Galaga/v` and `mt6878/Galaga/16b`. The Android 16 target is compared first with the `Galaga/16b` family; exact installed-build-to-commit correspondence remains open.

## Tools

### Read-only device acquisition

```bash
chmod +x tools/device/collect-camera-platform.sh
tools/device/collect-camera-platform.sh --pull-apks --pull-readable-config
```

Collects build/package/permission/app-op state, camera services and dumps, VINTF data, processes, libraries, modules, kernel identifiers and optional stock-camera APKs into a hashed local bundle.

### APK static analysis

```bash
chmod +x tools/apk/analyze-nothing-camera.sh
tools/apk/analyze-nothing-camera.sh /path/to/nothing-camera-apks
```

Runs available manifest, certificate, JADX, apktool, native-symbol/string and routing-keyword analysis with a versioned output manifest.

### Controlled Expert route collection

```bash
chmod +x tools/device/run-expert-route-trace.sh

for route in 06x 1x 2x; do
  tools/device/run-expert-route-trace.sh --route "$route" --mode camera2
done

for route in 06x 1x 2x; do
  tools/device/run-expert-route-trace.sh --route "$route" --mode key-types
done
```

Each invocation starts from a fresh Nothing Camera process and creates a timestamped, hashed local bundle containing Camera2 observations, package/permission evidence, camera-service logs and an empty non-image EXIF association record. The runner does not alter requests, permissions, SELinux policy or application files.

### Camera2 routing observer

```bash
frida -U -f com.nothing.camera \
  -l tools/frida/trace-camera2-routing.js \
  -o traces/nothing-camera-frida.log
```

Observes camera opens, session parameters, physical output selection, request metadata and request submission. It does not alter requests or bypass Android permissions.

### Vendor-key type observer

```bash
frida -U -f com.nothing.camera \
  -l tools/frida/dump-camera-key-types.js \
  -o traces/nothing-camera-key-types.log
```

Attempts to recover the installed framework key object's Java generic type, native metadata type, vendor ID, tag and the exact values used by the stock app. Unknown or inaccessible fields remain explicit.

### Expert route classifier

After filling each bundle's `output-association-template.json` from EXIF/MediaStore metadata:

```bash
python3 tools/trace/analyze-expert-routing-bundles.py \
  --root traces/expert-routing \
  --json traces/expert-routing/architecture.json \
  --markdown traces/expert-routing/architecture.md
```

The analyzer refuses to classify a route without the correct optical focal length, 35 mm equivalent and output geometry. It distinguishes:

- direct system-camera endpoints;
- a system logical/SAT endpoint;
- public ID `0` plus route-specific vendor metadata;
- a lower Java Camera2 boundary requiring JNI/Binder/provider/HAL tracing;
- incomplete or mismatched evidence.

## Immediate discriminator

The next decisive evidence is the stock package grant state and three fresh-process 0.6×/1×/2× traces:

- direct opens of IDs `2`, `3` or `4` establish a system-camera route;
- repeated opening of ID `0` with different vendor/session metadata establishes a public-ID SAT/vendor route;
- no Camera2 difference moves the investigation to JNI, native services and provider/HAL configuration.

The Android system-camera baseline matters because IDs `2`–`5` are filtered and rejected at CameraService for an ordinary caller. A numerical ID alone does not provide access. If the stock app opens those endpoints directly, a production ordinary APK and a privileged/system deployment must be treated as separate backends.

See:

- `docs/EXECUTION_PLAN.md`
- `docs/EVIDENCE_MODEL.md`
- `docs/research/SYSTEM_CAMERA_BOUNDARY.md`
- `docs/research/PHYSICAL_SENSOR_MAP.md`
- `docs/research/EXPERT_ROUTE_DISCRIMINATOR.md`
- `docs/research/EXPERT_ROUTE_RUNNER.md`
- `docs/research/EXPERT_ROUTE_ANALYZER.md`
- `data/capabilities/baseline.json`
- `data/vendor-tags/inventory.json`
- `data/vendor-tags/routing-priority.yaml`
- `data/hardware/sensor-map.yaml`

## Evidence rules

Every material claim records source and confidence. Negative tests are scoped to the exact mechanism tested. A failed intent, request or direct ID open does not become a platform-wide impossibility claim without tracing the enforcing layer.

Raw APKs, firmware, personal captures and proprietary binaries remain in controlled local evidence storage. The public repository contains hashes, normalized facts, independently written analysis and legally redistributable source references.

A route-specific vendor value is a discriminator candidate, not causal proof. It becomes production-usable only after exact target types and working stock values are captured and a controlled positive/negative reproducer demonstrates the effect safely.

## Product constraints

- CameraX with Camera2 interoperability where appropriate.
- Fully on-device processing; no cloud image processing.
- Natural colour and texture rather than an oversharpened synthetic rendering.
- Modular capture and processing stages.
- `Quick`, `Auto` and `Max Detail` capture modes.
- RAW capture and processing as a later milestone.
