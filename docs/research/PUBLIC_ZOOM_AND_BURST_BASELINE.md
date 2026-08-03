# Public Zoom and Burst Baseline

Source artifact: `phone2pro-daylight-lens-routing-20260803_092933_170.json`.

Build: `Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys`.

## Test configuration

- Public rear camera ID: `0`.
- Active array: 4080 × 3072.
- JPEG capture size: 2560 × 1920.
- Advertised zoom-ratio range: 1.0–10.0.
- Tested requested zoom ratios: 0.6, 1.0, 1.5, 1.8, 1.9, 2.0, 2.1, 2.2, 2.5, 3.0, 4.0, 10.0 and 20.0.

## Result

Every capture remained on the public main-camera focal length of 5.56 mm. No standard active physical camera ID was reported. The MediaTek effective crop changed continuously with zoom, and the Nothing result `com.nothing.camera.insensorzoom.enable` remained `0`.

| Requested | Result echo | Effective crop size | Derived effective zoom | Result |
|---:|---:|---:|---:|---|
| 0.6× | 0.6× | 4080 × 3072 | 1.0× | clamped to full main sensor |
| 1.0× | 1.0× | 4080 × 3072 | 1.0× | main sensor |
| 1.5× | 1.5× | 2720 × 2048 | 1.5× | digital crop |
| 1.8× | 1.8× | 2267 × 1707 | ~1.80× | digital crop |
| 1.9× | 1.9× | 2147 × 1617 | ~1.90× | digital crop |
| 2.0× | 2.0× | 2040 × 1536 | 2.0× | digital crop |
| 2.1× | 2.1× | 1943 × 1463 | ~2.10× | digital crop |
| 2.2× | 2.2× | 1855 × 1396 | ~2.20× | digital crop |
| 2.5× | 2.5× | 1632 × 1229 | 2.5× | digital crop |
| 3.0× | 3.0× | 1360 × 1024 | 3.0× | digital crop |
| 4.0× | 4.0× | 1020 × 768 | 4.0× | digital crop |
| 10.0× | 10.0× | 408 × 307 | 10.0× | digital crop |
| 20.0× | 20.0× | 408 × 307 | 10.0× | request echoed but effective crop clamped |

## Interpretation

- `CONTROL_ZOOM_RATIO` below the advertised minimum can be accepted and echoed while still being clamped in the image path.
- Public 2× is not the stock 50 mm-equivalent telephoto route. It is a 2× crop of the 5.56 mm main sensor.
- The public ID `0` route showed no sensor switch around the stock telephoto threshold.
- An accepted request value is not sufficient evidence of an effective configuration.
- The MediaTek crop result is more informative than the standard scaler crop result in this test: standard `android.scaler.cropRegion` remained the full active array while `com.mediatek.control.capture.scalerCropRegion` represented the effective crop.

## Burst baseline

Eight JPEG captures were submitted at 1× and 2×.

| Requested route | Results | Images | Mean sensor interval | Estimated sensor rate | Wall time |
|---|---:|---:|---:|---:|---:|
| 1× | 8/8 | 8/8 | 33.367 ms | 29.97 fps | 479 ms |
| 2× public crop | 8/8 | 8/8 | 33.383 ms | 29.96 fps | 427 ms |

The sensor timestamps show a stable approximately 30 fps cadence for the tested 2560 × 1920 JPEG burst configuration. Wall time includes capture and image delivery overhead, so it is longer than seven inter-frame intervals.

## Product consequences

- `Quick` can initially target a short 3–5-frame burst within this proven 30 fps envelope.
- `Auto` can target 6–8 frames when scene motion and memory allow.
- `Max Detail` should not assume that public 2× provides optical telephoto data; it must describe that route as a crop until a system/vendor backend is available.
- The capture engine must compare requested values with result metadata and effective geometry, not merely treat a successful `CaptureRequest.set()` as feature support.

## Required follow-up

1. Repeat in YUV and RAW to measure throughput without JPEG encoding.
2. Test full-resolution and maximum-quality stream combinations.
3. Record memory pressure, dropped buffers and thermal state over sustained bursts.
4. Decode the MediaTek crop tuple semantics formally.
5. Probe in-sensor zoom only after valid session values are recovered from stock-app traces or MediaTek source.
