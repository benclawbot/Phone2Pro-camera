# CMF Phone 2 Pro capability audit — 2026-08-02

This document records the first on-device report produced by the diagnostics APK on a Nothing A001 / Galaga device running Android 16. Device fingerprints and other unnecessary build identifiers are intentionally omitted.

## Confirmed device baseline

- SoC platform reported by Android: MediaTek MT6878.
- Approximately 7.23 GiB of physical memory was visible to Android.
- Application memory class: 256 MiB; large-memory class: 512 MiB.
- The report was generated while Android thermal status was `3`; this must not be treated as an idle thermal baseline.

## Manufacturer-confirmed camera hardware

Nothing's official CMF Phone 2 Pro specification confirms three functional rear camera modules:

- 50 MP main camera, 1/1.57-inch sensor, 24 mm-equivalent field of view, PDAF.
- 50 MP telephoto camera, 1/2.88-inch sensor, 50 mm-equivalent field of view, 2× optical zoom and up to 20× digital zoom.
- 8 MP ultrawide camera, 1/4-inch sensor, 15 mm-equivalent field of view and 119.5-degree field of view.

The stock Nothing camera presents 0.6×, 1× and 2× capture modes. The physical lenses are therefore real and operational. The diagnostics result below describes only what a normal third-party application can see through the public Android Camera2 interface; it does not mean that only one rear lens exists or works.

Manufacturer source: https://nothing.tech/pages/cmf-phone-2-pro

## Public Camera2 topology

Android exposes only two public Camera2 IDs to this third-party diagnostics application:

- `0`: rear camera endpoint
- `1`: front camera endpoint

Neither endpoint advertises `LOGICAL_MULTI_CAMERA`, and both return an empty set of physical camera IDs. The only advertised concurrent pair is rear plus front (`0` + `1`).

Consequences:

- The app cannot explicitly select the rear ultrawide or 2× telephoto through standard public Camera2 physical-camera APIs.
- Standard dual-rear-camera fusion is not currently guaranteed or addressable.
- The OEM camera can use privileged vendor interfaces, vendor tags, or internal HAL routing that a normal third-party app cannot assume.
- A runtime zoom test is still required to determine whether rear endpoint `0` silently changes physical sensors at some zoom ratios despite not exposing a standards-compliant logical camera.

This is an API-visibility limitation, not evidence that the other rear cameras are inactive.

## Rear camera endpoint (`0`)

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

These capabilities are sufficient to prototype a serious computational pipeline with manual exposure control, multi-frame YUV capture, reprocessing, RAW experiments, and on-device fusion through the public rear endpoint.

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

The static characteristics resemble the main camera path and expose only one focal length. They do not identify the telephoto or ultrawide as independently selectable devices.

### Important restriction

The advertised 50 MP sensor mode is not exposed through the public standard camera characteristics. The endpoint does not advertise `ULTRA_HIGH_RESOLUTION_SENSOR` or remosaic capability, and the largest public RAW/YUV/JPEG frame is about 12.5 MP. Version 1 must therefore assume a binned 12.5 MP source unless a later vendor-key or runtime test proves another path.

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

The production app can begin with a single-public-rear-endpoint architecture:

1. Public Camera2 rear endpoint `0`.
2. 12.5 MP YUV burst capture as the primary computational input.
3. Optional RAW experiments at 4080 × 3072.
4. Gyroscope-assisted frame scoring and alignment.
5. Natural JPEG rendering and MediaStore output.
6. Quick, Auto, and Max Detail modes implemented without assuming explicit rear-lens selection.

The first zoom prototype should be framed as multi-frame super-resolution through the public rear endpoint. Explicit main/telephoto fusion remains blocked unless a later runtime/vendor-key audit exposes a reliable way to address or identify the rear modules.

## Required dynamic audit before finalizing zoom

The static report cannot establish capture throughput or whether zoom ratios trigger hidden OEM sensor switching. The next one-button diagnostics workflow should therefore:

- Enumerate all standard and vendor characteristic/request/result key names.
- Record stream minimum-frame and stall durations.
- Capture controlled 1×, 2× and 4× samples from rear endpoint `0`.
- Record per-frame focal length, crop region, zoom ratio, exposure, ISO, timestamp, rolling-shutter skew, stabilization state and any active-camera vendor metadata.
- Compare field of view and image geometry to detect silent physical-lens switching.
- Benchmark sustained 8- and 15-frame YUV bursts at practical resolutions.
- Measure dropped frames, inter-frame spacing, memory peak, and thermal changes.
- Test OIS control behavior.
- Save a single report plus clearly named local sample frames for comparison.

The public zoom range starts at 1×, so the static report provides no standard route to the 0.6× ultrawide. The dynamic test can investigate telephoto routing at 2× and above, while ultrawide access may require vendor-specific discovery.

This dynamic result is the remaining gate for choosing the exact Max Detail zoom algorithm and performance budget.
