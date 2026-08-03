# CMF Phone 2 Pro official Expert-mode lens-routing result — 2026-08-03

## Result

The official Nothing camera used three distinct optical routes for the Expert-mode sequence 0.6×, 1× and 2×.

The diagnostics app associated exactly three new JPEGs, in the instructed order, with no unassociated or auxiliary assets. The official camera package was `com.nothing.camera`, component `com.nothing.camera.activity.VoiceCameraActivity`, version `16.1.01.93.20`.

## Per-lens evidence

| Expert button | Physical focal length | 35 mm equivalent | Aperture | Digital zoom EXIF | Output dimensions |
|---|---:|---:|---:|---:|---:|
| 0.6× | 1.64 mm | 15 mm | f/2.2 | 0.0 | 2448 × 3264 |
| 1× | 5.56 mm | 24 mm | f/1.87 | 0.0 | 3072 × 4080 |
| 2× | 7.10 mm | 50 mm | f/1.85 | 0.0 | 3072 × 4096 |

These focal lengths, equivalent focal lengths, apertures and zero digital-zoom values are not compatible with one camera being digitally cropped for all three settings. They match separate ultrawide, main and telephoto modules.

The 2× result is especially decisive: it records a 7.10 mm physical focal length and 50 mm-equivalent field of view with EXIF digital zoom 0.0, whereas the main route records 5.56 mm and 24 mm equivalent.

## Camera-availability timing

The public rear camera ID `0` changed availability while the stock app was running:

- ID `0` became available before the 0.6× photo was taken.
- ID `0` became unavailable before the 1× photo and remained unavailable during that capture.
- ID `0` became available again before the 2× photo.

This timing strongly suggests:

- 1× uses the public rear camera endpoint `0`.
- 0.6× uses a separate system-only rear camera device.
- 2× uses another separate system-only rear camera device.

The availability callback did not reveal which internal numeric IDs correspond to ultrawide and telephoto, so IDs `2–5` remain unmapped.

## Corrected architecture conclusion

The earlier public Camera2 tests did not activate the telephoto or ultrawide because those tests stayed on public endpoint `0`. This does not mean the hardware or stock-camera routing is unavailable internally.

For an ordinary third-party application:

- Public Camera2 access currently exposes the main camera only.
- The stock Nothing camera can access separate ultrawide and telephoto system-only devices.
- Reproducing stock-camera lens access requires discovering a privileged/vendor route or obtaining access unavailable to an ordinary app.

The production app should therefore keep a fully functional public-main-camera architecture as the guaranteed baseline, while reverse-engineering the stock camera/HAL route as an optional investigation. It must not assume the hidden routes can be shipped to normal users until a non-privileged invocation is proven.

## Next reverse-engineering target

The next useful investigation is not another public zoom test. It is an ADB-assisted stock-camera and camera-service audit to map system-only IDs `2–5` and identify the routing mechanism:

1. Capture `dumpsys media.camera` and camera-service state while Expert mode is idle at 0.6×, 1× and 2×.
2. Capture logcat around each lens switch and shutter event.
3. Inspect the installed Nothing Camera APK for camera-ID constants, vendor tag names, sensor-scenario values and privileged permissions.
4. Compare MediaTek seamless/multicam request keys against values emitted or referenced by the stock app.

This stage may identify exact internal IDs and vendor controls, but shipping access remains contingent on Android permissions and HAL policy.