# CMF Phone 2 Pro capability audit — 2026-08-02

This document records the first on-device report produced by the diagnostics APK on a Nothing A001 / Galaga device running Android 16. Device fingerprints and other unnecessary build identifiers are intentionally omitted.

## Confirmed device baseline

- SoC platform reported by Android: MediaTek MT6878.
- Approximately 7.23 GiB of physical memory was visible to Android.
- Application memory class: 256 MiB; large-memory class: 512 MiB.
- The report was generated while Android thermal status was `3`; this must not be treated as an idle thermal baseline.

## Public Camera2 topology

Android exposes only two public Camera2 IDs:

- `0`: rear camera
- `1`: front camera

Neither camera advertises `LOGICAL_MULTI_CAMERA`, and both return an empty set of physical camera IDs. The only advertised concurrent pair is rear plus front (`0` + `1`).

Consequences:

- The app cannot explicitly address the rear ultrawide or 2× telephoto through standard public Camera2 physical-camera APIs.
- Standard dual-rear-camera fusion is not currently available.
- The OEM camera may use privileged/vendor interfaces that a normal third-party app cannot assume.
- A runtime zoom test is still required to determine whether the single rear ID internally changes sensors at some zoom ratios despite not exposing a standards-compliant logical camera.

## Rear camera (`0`)

### Strong capabilities

- Hardware level: `LEVEL_3`.
- Manual sensor and manual post-processing.
- RAW output.
- Burst capture.
- PRIVATE and YUV reprocessing.
- Read-sensor-settings support.
- Constrained high-speed video.
- Stream-use-case and color-space-profile support.
- One RAW, three processed, and one stalling output stream.
- Camera extension exposed: `NIGHT`.

These capabilities are sufficient to prototype a serious single-camera computational pipeline with manual exposure control, multi-frame YUV capture, reprocessing, RAW experiments, and on-device fusion.

### Exposed imaging geometry

- Active/pixel array: 4080 × 3072 (about 12.5 MP).
- Maximum RAW output: 4080 × 3072.
- Maximum normal JPEG/YUV output: 4080 × 3072.
- Public focal length: approximately 5.56 mm.
- Public aperture: approximately f/1.879.
- Sensor physical size: approximately 8.16 × 6.14 mm.
- Focus distance control is exposed.
- Exposure range: 0.1 ms to 32 s.
- ISO range: 100–16000; reported maximum analog sensitivity: ISO 1600.
- Zoom-ratio range: 1×–10×.
- Optical stabilization modes report both OFF and ON.
- Video stabilization control reports OFF only.

### Important restriction

The advertised 50 MP sensor mode is not exposed through the public standard camera characteristics. The camera does not advertise `ULTRA_HIGH_RESOLUTION_SENSOR` or remosaic capability, and the largest public RAW/YUV/JPEG frame is about 12.5 MP. Version 1 must therefore assume a binned 12.5 MP source unless a later vendor-key or runtime test proves another path.

## Front camera (`1`)

- Hardware level: `LEVEL_3`.
- Manual sensor/post-processing, RAW, burst, PRIVATE/YUV reprocessing, stream-use-case, and color-space-profile support.
- Active/pixel array: 2320 × 1744 (about 4.0 MP).
- Maximum RAW/YUV: 2320 × 1744.
- Maximum JPEG listed: 1920 × 1440.
- Fixed focus (`minimumFocusDistance = 0`).
- No optical stabilization.
- Camera extension exposed: `NIGHT`.

The public path appears to expose a binned front-camera output rather than the nominal full sensor resolution.

## Sensors and acceleration

- Accelerometer and gyroscope are available with a reported minimum delay of 5000 microseconds (up to 200 Hz request rate).
- Uncalibrated gyro and accelerometer streams are also available.
- Rotation-vector and game-rotation-vector sensors are available.
- Hardware codecs include AVC/H.264, HEVC/H.265, and HEIF encode/decode support.

The inertial sensors are suitable for capture-motion scoring, frame alignment hints, horizon detection, and stabilization experiments. Actual timestamp alignment between Camera2 and sensors still needs measurement.

## Architecture decision from the static audit

The production app can begin with a single-rear-camera architecture:

1. Public Camera2 rear ID `0`.
2. 12.5 MP YUV burst capture as the primary computational input.
3. Optional RAW experiments at 4080 × 3072.
4. Gyroscope-assisted frame scoring and alignment.
5. Natural JPEG rendering and MediaStore output.
6. Quick, Auto, and Max Detail modes implemented without depending on rear-lens fusion.

The flagship zoom pipeline should initially be framed as **single-camera multi-frame super-resolution**. Explicit main/telephoto fusion remains blocked unless a later runtime/vendor-key audit exposes a reliable rear-lens path.

## Required dynamic audit before finalizing zoom

The static report cannot establish capture throughput or whether zoom ratios trigger hidden OEM sensor switching. The next one-button diagnostics workflow should therefore:

- Enumerate all standard and vendor characteristic/request/result key names.
- Record stream minimum-frame and stall durations.
- Capture controlled 1×, 2×, and 4× samples from rear ID `0`.
- Record per-frame focal length, crop region, zoom ratio, exposure, ISO, timestamp, rolling-shutter skew, and stabilization state.
- Benchmark sustained 8- and 15-frame YUV bursts at practical resolutions.
- Measure dropped frames, inter-frame spacing, memory peak, and thermal changes.
- Test OIS control behavior.
- Save a single report plus clearly named local sample frames for comparison.

This dynamic result is the remaining gate for choosing the exact Max Detail zoom algorithm and performance budget.
