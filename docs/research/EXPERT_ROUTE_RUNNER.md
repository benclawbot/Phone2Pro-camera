# Expert Route Trace Runner

Status: ready for authorized device execution under CAM-024, CAM-040, CAM-042 and CAM-045.

`tools/device/run-expert-route-trace.sh` turns one controlled stock-camera run into a timestamped, hashed local evidence bundle. It coordinates ADB preflight, package and app-op snapshots, camera-service logging, one Frida observer, before/after CameraService dumps and a non-image output-association record.

The runner does not alter permissions, Camera2 requests, SELinux policy or application files. It does not copy or upload the photograph.

## Prerequisites

- Linux or macOS host with Bash.
- `adb` connected to an authorized CMF Phone 2 Pro.
- Frida client plus an approved compatible device-side instrumentation setup.
- Repository checkout containing the observer scripts.

Verify:

```bash
adb get-state
frida --version
adb shell pm path com.nothing.camera
```

## Six-run matrix

Collect each optical route twice: once for high-level Camera2 routing and once for exact vendor-key type/value recovery.

```bash
chmod +x tools/device/run-expert-route-trace.sh

# Camera ID, physical output, session and request routing
for route in 06x 1x 2x; do
  tools/device/run-expert-route-trace.sh \
    --route "$route" \
    --mode camera2
done

# Vendor key Java/native types and stock values
for route in 06x 1x 2x; do
  tools/device/run-expert-route-trace.sh \
    --route "$route" \
    --mode key-types
done
```

Each invocation is interactive. Complete only the assigned stock Expert route, take one photograph, exit Nothing Camera, then stop the Frida console. Ctrl-D is preferred; Ctrl-C is handled and recorded.

Do not cycle through the other lens buttons during a run. Each invocation force-stops the stock package first so state does not carry between routes.

## Per-run bundle

A bundle is created below `traces/expert-routing/` using this naming scheme:

```text
YYYYMMDDTHHMMSSZ-ROUTE-MODE/
```

It contains, as available:

```text
run-metadata.json
run-status.txt
frida.log
camera-service.log
media-camera-before.txt
media-camera-after.txt
package-dumpsys-before.txt
package-dumpsys-after.txt
package-paths.txt
appops-before.txt
appops-after.txt
getprop.txt
output-association-template.json
SHA256SUMS
```

The `traces/` directory and raw camera/firmware formats are ignored by Git. Keep these bundles in controlled local evidence storage.

## Associate the stock output

Fill `output-association-template.json` using only non-image MediaStore/EXIF values:

- filename or MediaStore ID;
- capture timestamp;
- dimensions;
- physical focal length;
- 35 mm-equivalent focal length;
- aperture;
- digital zoom ratio when present.

Expected signatures:

| Route | Physical focal length | Equivalent | Dimensions |
|---|---:|---:|---:|
| `06x` | 1.64 mm | 15 mm | 3264 × 2448 |
| `1x` | 5.56 mm | 24 mm | 4080 × 3072 |
| `2x` | 7.1 mm | 50 mm | 4096 × 3072 |

A trace is not accepted as evidence for a route when the associated output does not match that optical signature.

## Compare the three Camera2 traces

Identify the three `camera2` bundle paths and run:

```bash
python3 tools/trace/compare-routing-traces.py \
  --trace 06x=traces/expert-routing/<06x-camera2>/frida.log \
  --trace 1x=traces/expert-routing/<1x-camera2>/frida.log \
  --trace 2x=traces/expert-routing/<2x-camera2>/frida.log \
  --json traces/expert-routing/camera2-diff.json \
  --markdown traces/expert-routing/camera2-diff.md
```

The report separates:

- camera IDs opened by each route;
- physical output IDs;
- session-creation methods;
- route-specific session values;
- route-specific repeating or still-request values;
- events shared with different occurrence counts.

A difference is a discriminator candidate. It becomes causal only after a controlled reproducer removes or changes that one configuration while preserving the rest of the stock setup.

## Architecture decision

The initial report should resolve one of four branches:

| Observation | Next layer |
|---|---|
| Different IDs, such as `2 / 0 / 3` | system-camera permissions, characteristics and direct open route |
| One system logical ID, such as `4` | hidden physical IDs and logical/SAT session state |
| Always ID `0`, route-specific session/request metadata | MediaTek vendor/SAT reproducer |
| No Java Camera2 difference | JNI, Binder, provider/HAL and native feature-pipeline tracing |

## Sharing rule

Before sharing a bundle:

1. Keep the photograph outside the bundle.
2. Review package dumps and logs for unrelated personal information.
3. Preserve hashes and build metadata.
4. Share only the minimum files required for the route analysis.
5. Do not commit raw traces or proprietary binaries to the public repository.
