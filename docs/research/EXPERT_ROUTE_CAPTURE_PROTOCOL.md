# Controlled Expert Routing Trace Protocol

Status: ready for device execution under CAM-024, CAM-040, CAM-042, CAM-045 and CAM-047.

## Objective

Collect three comparable fresh-process traces that differ only in the stock Expert lens selected:

- `0.6x` — ultrawide, expected 15 mm equivalent;
- `1x` — main, expected 24 mm equivalent;
- `2x` — telephoto, expected 50 mm equivalent.

The experiment must determine whether the working stock route changes:

1. the Camera2 camera ID;
2. an output physical camera ID;
3. session parameters;
4. repeating-request metadata;
5. still-capture metadata;
6. no observable Camera2 state, implying a lower JNI/Binder/provider/HAL discriminator.

## Safety and scope

- Use only a device that the tester owns or is authorized to instrument.
- The scripts observe calls and metadata. They do not alter requests, permissions, package signatures or SELinux policy.
- Do not iterate unknown vendor values.
- Do not upload photographs or image buffers. The trace bundle contains metadata and control flow only.
- Stop if the camera service becomes unstable; reboot before collecting another baseline.

## Required tools

- ADB with USB debugging authorized.
- Frida client and a compatible Frida server or approved instrumentation environment.
- Repository tools:
  - `tools/frida/trace-camera2-routing.js`
  - `tools/frida/dump-camera-key-types.js`
  - `tools/trace/compare-routing-traces.py`

## Scene control

Use the same static scene for all three runs:

- bright, stable lighting;
- no moving subjects;
- at least one near object and one distant detailed object;
- no digital zoom gesture;
- flash disabled;
- identical orientation;
- phone fixed on a support where possible.

The scene is needed only to verify that the resulting file came from the intended optical route. No image data enters the trace logs.

## Preflight

Record:

```bash
adb shell getprop ro.build.fingerprint
adb shell dumpsys package com.nothing.camera | head -n 120
adb shell pidof com.nothing.camera || true
```

Create the output directory:

```bash
mkdir -p traces/expert-routing
```

Force-stop the stock camera before every run:

```bash
adb shell am force-stop com.nothing.camera
sleep 2
```

## Trace A: Camera2 route and requests

Run one trace per lens. Substitute `ROUTE` with `06x`, `1x` or `2x`:

```bash
ROUTE=06x
adb shell am force-stop com.nothing.camera
sleep 2

frida -U -f com.nothing.camera \
  -l tools/frida/trace-camera2-routing.js \
  -o "traces/expert-routing/${ROUTE}-camera2.log"
```

When the stock app appears:

1. Enter Expert mode.
2. Select only the assigned lens.
3. Wait three seconds for preview stabilization.
4. Take one photograph.
5. Wait three seconds.
6. Exit the camera.
7. Stop Frida.

Do not switch through other lenses during that process. Start a new stock-camera process for each route.

## Trace B: Exact key types and values

Repeat the three fresh-process runs with the type tracer:

```bash
ROUTE=06x
adb shell am force-stop com.nothing.camera
sleep 2

frida -U -f com.nothing.camera \
  -l tools/frida/dump-camera-key-types.js \
  -o "traces/expert-routing/${ROUTE}-key-types.log"
```

Use the same UI sequence as Trace A. The type trace is especially important for:

- `com.mediatek.configure.setting.*`;
- `com.mediatek.cameraflex.*`;
- `com.mediatek.insensorzoomfeature.*`;
- `com.mediatek.seamlessfeature.*`;
- `com.mediatek.multicamfeature.*`;
- `com.mediatek.streamingfeature.pipDevices`;
- `com.nothing.camera.*` and `nothing.camera.*`.

## Optional synchronized CameraService log

In a second terminal, collect a bounded log for each run:

```bash
ROUTE=06x
adb logcat -c
adb logcat -v epoch \
  CameraService:* CameraProviderManager:* cameraserver:* CamX:* mtkcam:* MtkCam:* *:S \
  > "traces/expert-routing/${ROUTE}-camera-service.log"
```

Tag availability varies by firmware. An empty vendor tag is not a negative result.

Also collect before and after snapshots:

```bash
adb shell dumpsys media.camera \
  > "traces/expert-routing/${ROUTE}-dumpsys-after.txt"
```

## Output-file association

For each stock capture, record only the non-image metadata needed to prove route identity:

- filename or MediaStore ID;
- creation timestamp;
- pixel dimensions;
- EXIF physical focal length;
- EXIF 35 mm-equivalent focal length;
- aperture;
- digital zoom ratio if present.

Expected optical signatures from the established stock audit:

| Route | Physical focal length | 35 mm equivalent | Landscape dimensions |
|---|---:|---:|---:|
| 0.6x | 1.64 mm | 15 mm | 3264 × 2448 |
| 1x | 5.56 mm | 24 mm | 4080 × 3072 |
| 2x | 7.1 mm | 50 mm | 4096 × 3072 |

## Differential analysis

Run:

```bash
python3 tools/trace/compare-routing-traces.py \
  --trace 06x=traces/expert-routing/06x-camera2.log \
  --trace 1x=traces/expert-routing/1x-camera2.log \
  --trace 2x=traces/expert-routing/2x-camera2.log \
  --json traces/expert-routing/camera2-diff.json \
  --markdown traces/expert-routing/camera2-diff.md
```

Repeat for the key-type logs if they contain routed `send()` events suitable for comparison.

## Interpretation order

### Outcome 1: different Camera2 IDs

Examples:

```text
0.6x -> 2
1x   -> 0
2x   -> 3
```

Interpretation: direct system-camera routing is strongly supported. Next work is package privilege, system-camera characteristics and a minimal authorized open reproducer.

### Outcome 2: one system logical ID

Example:

```text
0.6x -> 4
1x   -> 4
2x   -> 4
```

with different physical output IDs or vendor state.

Interpretation: system logical/SAT routing is strongly supported. Next work is logical metadata, hidden physical IDs and session configuration.

### Outcome 3: always public ID 0, different session parameters

Interpretation: a vendor SAT route below the public logical-camera contract is supported. The first route-specific session key or opaque initialization payload becomes the reproducer candidate.

### Outcome 4: always ID 0, no session difference, repeating requests differ

Interpretation: lens selection may be a request-time sensor scenario or proprietary repeating control.

### Outcome 5: no observable Camera2 difference

Interpretation: the discriminator is likely below or beside the Java Camera2 surface. Continue with:

- JNI registration and native function hooks;
- Binder transactions and service identity;
- provider/HAL `configureStreams` metadata;
- MediaTek feature-pipeline state;
- framework/vendor wrapper classes missed by the generic hooks.

## Validity checks

A route trace is invalid and must be repeated when:

- the app was not force-stopped first;
- another lens was selected before the target lens;
- the output EXIF does not match the assigned optical route;
- the trace started after camera/session initialization;
- logs were truncated before still capture;
- the device entered a thermal or camera-service fault state;
- stock application settings differed between routes.

## Acceptance criteria

- Three fresh-process traces are collected under the same build and settings.
- Every trace is associated with a verified 15/24/50 mm-equivalent stock output.
- Exact opened IDs, physical IDs, session parameters and route-related request keys are diffed.
- Every differing candidate records its Java/native type before reproduction testing.
- If no Java-layer discriminator exists, the next lower observation layer is identified rather than declaring the route impossible.
