# Official Nothing Camera APK audit — CMF Phone 2 Pro / Galaga

Date: 2026-08-03

## Artifact identity

- Supplied APK SHA-256: `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`.
- Manifest package: `com.nothing.camera`.
- Manifest version: `16.1.01.93.20`.
- This matches the official-camera version recorded by the on-device Expert-mode audit, so the static APK configuration and observed captures describe the same installed camera build.

## Decisive camera-ID mapping

The device-specific class `com.nothing.common.utils.config.zoom.ProductGalagaZoomConfigBuilder` directly maps Expert/manual zoom regions to camera IDs in `addManualZoomConfig()` at DEX code offset `0x26c120`:

| Expert zoom region | Camera ID | Interpretation |
|---|---:|---|
| `[0.6,1)` | `2` | rear ultrawide |
| `[1,2)` | `0` | rear main |
| `[2,10]` | `3` | rear telephoto |

The same method defines the visible zoom indicators as `0.6`, `1.0`, and `2.0`.

This mapping independently matches the official Expert-mode EXIF audit:

- 0.6×: 1.64 mm / 15 mm-equivalent / f/2.2.
- 1×: 5.56 mm / 24 mm-equivalent / f/1.87.
- 2×: 7.10 mm / 50 mm-equivalent / f/1.85.
- All three report EXIF digital zoom ratio zero.

Therefore the internal rear-camera mapping for this firmware is confirmed as:

- `0` — main rear physical camera; publicly exposed.
- `2` — ultrawide rear physical camera; system-only.
- `3` — telephoto rear physical camera; system-only.

## Logical and special camera IDs

`ProductGalagaZoomConfigBuilder.addPhotoZoomConfig()` at DEX code offset `0x26c254` contains two routing forms.

When SAT is disabled, it routes directly:

- 0.6× to ID `2`.
- 1× to ID `0`.
- 2×–20× to ID `3`.

For Galaga, `ConfigMapGalaga` sets `FEATURE_CAMERA_DEFAULT_SUPPORT_SAT=true`. The enabled branch maps the complete `[0.6,20]` range to camera ID `4`, with 0.6×, 1× and 2× indicators. ID `4` is therefore the stock application's SAT/logical triple-rear endpoint used for seamless normal-photo zoom.

`ProductGalagaZoomConfigBuilder.addBokehZoomConfig()` at DEX code offset `0x26c084` maps `[1,4]` to camera ID `5`. ID `5` is therefore the portrait/bokeh logical rear endpoint.

Confirmed internal topology:

| ID | Role | Third-party visibility |
|---:|---|---|
| `0` | main rear physical camera | public |
| `1` | front camera | public |
| `2` | ultrawide rear physical camera | system-only |
| `3` | telephoto rear physical camera | system-only |
| `4` | SAT/logical triple-rear camera | system-only |
| `5` | portrait/bokeh logical rear camera | system-only |

## Galaga zoom and focal configuration

`ConfigMapGalaga` enables:

- default photo SAT;
- video SAT;
- wide-lens support;
- MediaTek SAT capture cropping;
- maximum photo zoom of 20×.

The Galaga focal-display configuration defines:

- 0.6× → 15 mm equivalent.
- 1× → 24 mm equivalent.
- 2× → 50 mm equivalent.
- 3× → 70 mm equivalent.
- 4× → 100 mm equivalent.
- 5× → 120 mm equivalent.
- 6× → 140 mm equivalent.
- 10× → 240 mm equivalent.

Only 0.6×, 1× and 2× are separate optical anchor points. Higher labels are digital zoom on the selected route.

## Vendor routing metadata

`com.nothing.common.setting.SettingCharacteristics.<clinit>()`, DEX code offset `0x21eb00`, constructs the following relevant vendor keys:

- `com.mediatek.multicamfeature.multiCamMasterId` — capture-result master physical ID.
- `com.nothing.camera.sat.capture.masterId` — capture-request master physical ID.
- `com.nothing.camera.sat.capture.crop` — SAT capture crop request/result.
- `com.nothing.camera.SatZoom.enable` — SAT zoom enable request.
- `com.nothing.camera.SatFallback.halStatus` — HAL fallback result.
- `com.nothing.camera.SatFallback.appStatus` — application fallback request.
- `com.nothing.camera.sat.canCapture` — SAT capture-ready result.
- `com.mediatek.multicamfeature.multiCamFeatureMode` — multi-camera feature-mode request.
- `com.nothing.camera.sat.touch.ratio` — SAT touch-zoom request.
- `com.nothing.camera.teleFixZoom.ratio` — telephoto fixed-zoom request.
- `com.nothing.camera.master.camera.id` — explicit master-camera request.
- `com.nothing.camera.slaver.camera.id` — explicit secondary-camera request; the `slaver` spelling is present in the OEM APK.

The stock app uses these keys in photo, video, manual, bokeh, night and super-resolution paths.

In `CameraManualMode.onShutterButtonClick()` at code offset `0x3c4b84`, the app obtains `CaptureHolder.getPhysicalId()` and writes it to `com.nothing.camera.sat.capture.masterId` before capture. This confirms that Expert mode carries the selected physical ID into the MediaTek capture request.

Normal photo mode uses `com.mediatek.multicamfeature.multiCamFeatureMode`, `com.nothing.camera.SatZoom.enable`, SAT crop metadata and the HAL-reported master ID around the system-only ID `4` route.

These private SAT tags were not exposed in the request-key inventory returned to the ordinary diagnostics application through public camera ID `0`.

## Privilege boundary

The official APK requests privileged permissions including:

- `android.permission.SYSTEM_CAMERA`;
- `android.permission.WRITE_SECURE_SETTINGS`;
- `android.permission.READ_GLOBAL_SETTINGS`;
- `android.permission.DUMP`;
- `android.permission.CONTROL_DEVICE_LIGHTS`;
- Nothing advanced-thermal and MediaTek APU permissions.

The APK is signed with Nothing's platform certificate:

- subject/issuer: `CN=platform, OU=nothing, O=nothing, L=ShenZhen, ST=GuangDong, C=zh`;
- SHA-256 certificate fingerprint: `2C:4E:1F:8E:B9:5D:96:F7:60:33:6F:03:B9:2B:C3:85:81:11:E9:87:C5:97:03:F9:87:3C:8D:C7:FA:A4:11:9D`.

This explains why the official app can open IDs `2`–`5` while a normally signed third-party APK receives a system-only-camera rejection. Recreating the numeric IDs or vendor-key names does not grant the missing camera-service permission.

## Exported stock-camera integration surface

The official manifest exports `CameraActivity` and `VoiceCameraActivity`. `LaunchIntentParser` recognizes launch extras including:

- `android.intent.extras.CAMERA_MAIN_MODE`;
- `android.intent.extras.CAMERA_PREFIX_MAIN_MODE`;
- `android.intent.extras.CAMERA_PREFIX_SUB_MODE`;
- `android.intent.extras.CAMERA_FACING`.

The internal mode-name map includes `manual`. This creates a testable integration path in which a normal application launches the privileged stock camera directly into Expert/manual mode and possibly supplies a target camera ID. It does not give the calling application access to the stock session's raw frames or private `CaptureResult`, so it cannot replace direct Camera2 ownership for the computational pipeline.

The exported `ExtensionsInterfaceProxyImplService` is an offline image-processing binder for parcelled images, capture results and hardware buffers. Static inspection found no camera-open or lens-routing operation in that service, so it is not a route around `SYSTEM_CAMERA`.

## Architecture decision

For an ordinary distributable application:

1. Direct Camera2 ownership remains limited to public rear ID `0` for the custom multi-frame pipeline.
2. Real ultrawide and telephoto capture cannot be implemented by simply opening IDs `2` or `3`; Android camera service enforces the system-only boundary.
3. A stock-camera handoff can potentially open Expert mode on IDs `2`, `0` or `3`, but processing remains inside the official app and the caller receives only the saved result.
4. Full direct access would require a privileged/system build signed with the OEM platform key, a firmware modification/root-level camera-service policy change, or official Nothing support exposing the logical/physical cameras publicly.

## Next validation

The next low-risk diagnostic should test the exported stock-camera launch contract:

- launch `CameraActivity` with main mode `manual`;
- request IDs `2`, `0` and `3` separately through the recognized facing/camera extra;
- record the initial Expert-mode lens and the resulting EXIF;
- determine whether this can provide a reliable stock-camera fallback for 0.6× and 2×.

A direct vendor-key probe against public ID `0` is lower priority because the relevant SAT keys are absent from the public request-key inventory and the actual SAT/logical endpoint is system-only ID `4`.