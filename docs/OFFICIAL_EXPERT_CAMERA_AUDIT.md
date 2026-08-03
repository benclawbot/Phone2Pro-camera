# Official camera Expert-mode lens audit

This profile exists to observe the stock Nothing camera's lens-routing behaviour without pretending that a third-party app can read the stock application's private Camera2 `CaptureResult`.

## User workflow

1. Start **Official camera Expert 0.6x / 1x / 2x audit**.
2. Grant Camera and full Photos and videos access.
3. The diagnostics app resolves and opens the device's default full still-camera activity.
4. In the official camera, switch to Expert mode.
5. Keep the phone in the same position and take exactly one photo at 0.6x, one at 1x, and one at 2x, in that order.
6. Return to the diagnostics app.

## Association rule

The first three new non-RAW still images created after the camera launch are ordered by capture time and associated with:

1. 0.6x
2. 1x
3. 2x

Taking extra photos during the sequence makes the association ambiguous and requires rerunning the profile.

## Recorded evidence

For each associated stock-camera image, the report records:

- expected Expert-mode lens button;
- original MediaStore URI and metadata;
- official camera package and activity component;
- capture and return timestamps;
- public camera availability transitions while the official app is active;
- SHA-256 hash;
- EXIF make, model, software, lens model and lens specification;
- physical and 35 mm-equivalent focal lengths;
- EXIF digital zoom ratio;
- aperture, exposure, ISO and dimensions;
- a byte-for-byte diagnostic copy named for 0.6x, 1x or 2x.

Copies are stored under `Pictures/Phone2Pro Diagnostics/Official Expert Camera Audit`. The JSON report is stored under `Downloads/Phone2Pro Diagnostics`.

## Diagnostic boundary

Android isolates one application's camera session from another application. A normal third-party diagnostics app cannot intercept the official camera's private request/result metadata, vendor tags, or internal physical-camera ID while the stock app owns the camera.

This profile therefore uses externally observable evidence: the exact official output files, EXIF, image geometry, package/component identity, timing and public camera availability events. Distinct focal-length or lens-model metadata strongly supports physical switching; image registration is used as the final check when OEM EXIF is incomplete or normalized.
