# CMF Phone 2 Pro daylight lens-routing audit — 2026-08-03

Status: preliminary image-only analysis. The daylight JSON report is still required before this audit is final.

## Supplied image set

The received daylight samples cover 1.8×, 1.9×, 2.0×, 2.1×, 2.2×, 2.5×, 3.0×, 4.0×, 10.0× and 20.0×. The 0.6×, 1.0× and 1.5× samples and the corresponding JSON report were not present in this upload.

All received JPEGs are 1536 × 1152.

## Image-registration result

Feature-based registration between adjacent samples found a single global scaling transform with very high consistency and almost no residual parallax through the 1.8×–4× sequence.

Estimated image-scale changes versus requested ratios:

- 1.8× → 1.9×: estimated 1.0607×; requested ratio 1.0556×.
- 1.9× → 2.0×: estimated 1.0522×; requested ratio 1.0526×.
- 2.0× → 2.1×: estimated 1.0512×; requested ratio 1.0500×.
- 2.1× → 2.2×: estimated 1.0473×; requested ratio 1.0476×.
- 2.2× → 2.5×: estimated 1.1395×; requested ratio 1.1364×.
- 2.5× → 3.0×: estimated 1.1999×; requested ratio 1.2000×.
- 3.0× → 4.0×: estimated 1.3328×; requested ratio 1.3333×.

The median geometric registration error for those adjacent pairs was approximately 0.23–0.47 pixels with roughly 1,700–2,650 inlier features per comparison. That is consistent with digital cropping/scaling from one optical viewpoint and is not consistent with a switch to a physically displaced telephoto module around 2×.

The scene contains foreground leaves and branches plus distant buildings and road detail, so a real switch to another rear module should normally introduce measurable depth-dependent parallax. None was detected across 1.8×, 1.9×, 2.0×, 2.1× or 2.2×.

## 10× and 20× behaviour

The 10× and 20× samples have effectively the same field of view. Registration estimated a scale of approximately 0.9995× rather than the requested 2× change, with high image correlation. This confirms the public image route remains capped at approximately 10× while the standard zoom value can still echo 20×.

## Preliminary conclusion

The public rear endpoint does not switch to the dedicated telephoto camera in daylight around 2× for this test path. The received 1.8×–10× sequence behaves as digital crops from the same main-camera image stream, and 20× is clamped to the same effective field of view as 10×.

This image evidence agrees with the previous night report, where MediaTek crop metadata described exact centered crops and the focal length stayed at 5.56 mm.

## Remaining evidence required

The daylight JSON report is required to confirm:

- exact MediaTek effective crop values for every requested zoom;
- whether any active physical ID, focal length, in-sensor zoom or remosaic result changes;
- system-only camera open-probe outcomes for IDs 2–5;
- 1× and 2× eight-frame burst throughput and frame spacing;
- thermal status before and after the run.

After the JSON is reviewed, the next investigation should move to ADB camera-service inspection and Nothing Camera APK/vendor-interface analysis rather than further public Camera2 zoom probing.