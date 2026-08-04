# Expert-route Perfetto and clock-normalization workflow

**Issue:** CAM-040 / #37  
**Target:** CMF Phone 2 Pro (`Galaga`)  
**Trace clock:** `BUILTIN_CLOCK_BOOTTIME`

The existing Expert-route runner captures one controlled stock-camera scenario with Frida, CameraService logcat and before/after service state. The synchronized wrapper adds the lower-layer evidence required to correlate that run with Perfetto scheduler, camera/HAL and Binder events.

## One-command run

Use the wrapper instead of invoking `run-expert-route-trace.sh` directly:

```sh
tools/device/run-expert-route-perfetto.sh --route 06x --mode camera2
```

The wrapper forwards the existing runner options, including `--serial`, `--output`, package selection and timing controls. Only one synchronized wrapper may use an output root at a time.

For the complete matrix:

```sh
tools/device/run-expert-route-perfetto.sh --route 06x --mode camera2
tools/device/run-expert-route-perfetto.sh --route 1x  --mode camera2
tools/device/run-expert-route-perfetto.sh --route 2x  --mode camera2
tools/device/run-expert-route-perfetto.sh --route 06x --mode key-types
tools/device/run-expert-route-perfetto.sh --route 1x  --mode key-types
tools/device/run-expert-route-perfetto.sh --route 2x  --mode key-types
```

## Perfetto lifecycle

The wrapper starts the on-device Perfetto client in detached mode using `tools/device/perfetto/expert-routing.pbtx`. The configuration:

- has a hard ten-minute duration limit;
- writes periodically to the device trace file;
- uses a 64 MiB ring buffer;
- records camera, HAL and Binder atrace categories;
- records Binder transaction, scheduling and process-lifecycle ftrace events;
- records process statistics;
- declares BOOTTIME as the primary trace clock and emits clock snapshots every second.

The session is explicitly stopped and pulled after the interactive runner finishes. An EXIT trap also stops it on wrapper failure, while the hard duration prevents an indefinite leaked session after host loss.

## Clock correlation

`capture-adb-clock-sample.py` records four bounded samples around the Perfetto and interactive-run lifecycle. Each sample contains:

- host send, receive and midpoint epoch nanoseconds;
- ADB round-trip duration;
- device `/proc/uptime` converted to BOOTTIME nanoseconds;
- device realtime nanoseconds, or second precision when `%N` is unavailable;
- realtime precision.

`normalize-trace-clocks.py` uses the median BOOTTIME↔host-epoch offset and records an uncertainty bound from transport delay, clock precision and observed offset spread. Epoch-formatted CameraService logcat is converted to BOOTTIME JSONL, allowing direct comparison with Perfetto trace-processor timestamps.

## Added bundle artifacts

A successful run adds:

- `expert-routing.perfetto-trace` — raw Perfetto trace;
- `perfetto-status.json` — session/config/lifecycle record;
- `clock-samples.jsonl` — raw host/device correlation samples;
- `clock-normalization.json` — BOOTTIME↔epoch mapping and uncertainty;
- `camera-service.boottime.jsonl` — normalized logcat events when logcat exists;
- refreshed `SHA256SUMS` covering the entire bundle.

Raw traces may contain process names, system state and package metadata. Keep bundles local and review them before sharing. The workflow does not capture or upload image pixels.

## Validation boundary

The tools and synthetic tests verify orchestration, clock arithmetic and logcat conversion. They do not prove that every requested ftrace event is enabled on a specific production build or that a stock-camera route activates an optical sensor. A real six-run device matrix and output association remain required before closing CAM-040.

## Tests

```sh
python3 -m unittest tests/test_trace_clock_normalization.py -v
python3 -m py_compile \
  tools/trace/capture-adb-clock-sample.py \
  tools/trace/normalize-trace-clocks.py
bash -n tools/device/run-expert-route-perfetto.sh
```
