# CMF Phone 2 Pro dynamic camera audit — night run 2026-08-02

This document records the second-stage diagnostics run from a Nothing A001 / Galaga device running Android 16. The run used the normal third-party application sandbox and public Camera2 access. It did not use root, ADB privileges, the stock Nothing camera process, or firmware modification.

## Executive result

The night run found strong evidence that the phone's additional camera devices exist behind system-only Camera2 IDs, but a normal third-party app cannot inspect or open them directly.

Through public rear endpoint `0`, the HAL accepts zoom-ratio requests outside its advertised `1.0–10.0` range. However, the returned JPEG geometry and MediaTek crop metadata show that:

- A requested `0.6×` is effectively the same full main-camera view as `1×`; it does not route to the ultrawide.
- `2×`, `4×`, and `10×` are center crops of the same 4080 × 3072 main-camera stream during this low-light run.
- A requested `20×` is effectively clamped to the same underlying `10×` crop, even though the standard `android.control.zoomRatio` result echoes `20`.
- No sample enabled the exposed Nothing in-sensor-zoom or remosaic status flags.
- The lens focal length stayed at 5.56 mm and aperture at f/1.879 for all samples.

This establishes that standard result metadata alone cannot be trusted to prove actual zoom geometry when the requested ratio is outside the advertised range. MediaTek's vendor crop result and image-to-image geometry are the reliable evidence in this run.

## Hidden/system-only camera devices

The diagnostics app probed numeric camera IDs `0` through `31`.

- Public IDs remained `0` (rear) and `1` (front).
- IDs `2`, `3`, `4`, and `5` returned `CameraAccessException` messages explicitly identifying them as `system only device` entries.
- No unlisted ID was accessible to the ordinary application.
- IDs `6` through `31` were rejected as nonexistent/invalid candidates.

The four system-only entries are important evidence that additional Camera2/HAL devices exist beyond the two public endpoints. The report does not reveal which ID maps to the ultrawide, telephoto, front physical sensor, auxiliary stream, or another internal camera role. Mapping them requires privileged camera-service information, stock-camera analysis, or a vendor routing interface.

## Vendor interface inventory

The rear endpoint exposes a substantial MediaTek and Nothing vendor-tag surface, including names associated with:

- Multi-camera feature sensor configuration.
- In-sensor zoom status and hints.
- Seamless sensor scenarios and forced sensor modes.
- Cell-crop and full-sensor ID configuration.
- Physical-ID-specific temporal noise reduction.
- Remosaic and seamless remosaic.
- Multi-frame noise reduction and AIS modes.
- HDR, 3D noise reduction, ZSL, high-quality YUV, RAW processing, ISP tuning, gyro data, and custom Nothing tuning.

Notable request-key names include:

- `com.mediatek.insensorzoomfeature.insensorzoomPhysicalIdsStatus`
- `com.mediatek.insensorzoomfeature.insensorzoomEnableHints`
- `com.mediatek.seamlessfeature.sensorScenario`
- `com.mediatek.seamlessfeature.forceSensorMode`
- `com.mediatek.seamlessfeature.configCellCropSensorIds`
- `com.mediatek.seamlessfeature.configCellFullSensorIds`
- `com.mediatek.seamlessfeature.configSensorScenarios`
- `com.mediatek.streamingfeature.tnrOffByPhysicalIds`
- `com.nothing.camera.hint.for.custom.tuning`

The available characteristic `com.mediatek.multicamfeature.availableMultiCamFeatureSensorManualUpdated` also returns a list of encoded integer values. Their semantics are not self-describing and must not be guessed.

The presence of these keys demonstrates that the MediaTek/Nothing HAL contains sensor-routing and multi-camera mechanisms. It does not prove that arbitrary values are safe or usable by an unprivileged app. Vendor tags require correct data types, valid enumerations, compatible session setup, and possibly signature-level permissions.

## Zoom samples

All samples were captured from public rear camera ID `0` at 1536 × 1152 JPEG output.

| Requested | Reported zoom | Public focal length | MediaTek effective crop | In-sensor zoom | Interpretation in this run |
|---:|---:|---:|---|---:|---|
| 0.6× | 0.6× | 5.56 mm | `[0, 0, 4080, 3072]` | 0 | Same full main-camera geometry as 1×; no ultrawide route |
| 1× | 1× | 5.56 mm | `[0, 0, 4080, 3072]` | 0 | Full 4080 × 3072 main path |
| 2× | 2× | 5.56 mm | `[1020, 768, 2040, 1536]` | 0 | Exact centered 2× crop of main path |
| 4× | 4× | 5.56 mm | `[1530, 1152, 1020, 768]` | 0 | Exact centered 4× crop of main path |
| 10× | 10× | 5.56 mm | `[1836, 1382, 408, 307]` | 0 | Approximate centered 10× crop of main path |
| 20× | 20× | 5.56 mm | `[1836, 1382, 408, 307]` | 0 | Same underlying crop as 10×; request/result metadata exceeds actual crop |

The standard `android.scaler.cropRegion` result remained the full active array for every sample, while the MediaTek vendor crop value tracked the effective digital crop. This device therefore requires the vendor crop result, output geometry, or both when auditing zoom behavior.

Automated feature matching on the supplied samples found:

- `0.6×` to `1×` scene scale approximately `1.001`, confirming effectively identical field of view.
- `1×` to `2×` scene scale approximately `1.998`, confirming an ordinary 2× digital crop.
- `1×` to `4×` scene scale approximately `3.993`, confirming an ordinary 4× digital crop.
- `10×` to `20×` scene scale approximately `1.0005`, confirming effectively identical field of view.

The low-light run therefore found no evidence of telephoto or ultrawide activation through the public endpoint.

## Exposure and stabilization observations

Across the six zoom samples:

- OIS result remained enabled.
- Exposure time remained approximately 10 ms.
- ISO varied from about 1320 to 1964.
- Focal length and aperture never changed.
- `com.nothing.camera.remosaic.status` remained `0`.
- `com.nothing.camera.insensorzoom.enable` remained `0`.
- MediaTek 3D noise reduction remained enabled.

The unchanged lens properties and the exact center-crop sequence further support a single main-sensor path for this night test.

## Burst benchmark

The 1× eight-frame burst completed successfully:

- Requested frames: 8.
- Capture results received: 8.
- Images received: 8.
- Dropped frames: 0 observed.
- Wall-clock completion time: 553 ms.
- Sensor timestamp spacing: approximately 33.34 ms per frame.
- Effective sensor cadence: approximately 30 fps.
- First-to-last sensor timestamp span: approximately 233.57 ms.
- Thermal status stayed at `1` before and after the complete capture audit.

This is a useful baseline for Quick and Auto burst modes. It is not yet a maximum-throughput test because the current diagnostic output size is 1536 × 1152 and the benchmark used eight frames only.

## Architecture implications

1. The production app can reliably use public rear endpoint `0` for main-camera burst capture.
2. Public zoom requests below 1× and above 10× must not be interpreted literally; the HAL may echo them while clamping the underlying image route.
3. At night, 2× must currently be treated as a crop of the main sensor, not proof of telephoto access.
4. Zoom Detail version 1 still needs a strong single-camera multi-frame super-resolution path.
5. The four system-only IDs and vendor routing tags justify further investigation after the daylight run.
6. The app must avoid writing undocumented vendor-tag values until their types, enumerations, and session requirements are understood.

## Daylight decision gate

Run the existing `Daylight lens-routing audit` outdoors in good light, with the phone held still and a scene containing distant fine detail.

The daylight result will answer whether the HAL changes behavior when enough light is available:

- If 2× changes focal length, vendor crop behavior, image viewpoint, or image geometry, the telephoto may be routed automatically in good light.
- If 2× remains the same exact center crop, the public endpoint does not automatically expose the telephoto under tested conditions.
- A 0.6× result with the same geometry as 1× will confirm that the public endpoint cannot route to the ultrawide through `CONTROL_ZOOM_RATIO`.

If daylight still exposes only main-sensor crops, the next investigation should move outside the ordinary app sandbox: use ADB camera-service diagnostics and inspect the installed Nothing Camera package/vendor interfaces to map system-only IDs `2`–`5` and determine whether any supported third-party route exists.
