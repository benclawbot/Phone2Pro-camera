# Product ideation baseline

This document records the decisions agreed before the CMF Phone 2 Pro capability audit and the architecture constraints discovered by the first on-device report.

## Product intent

Build a privacy-first camera app whose flagship advantage is authentic zoom detail. It should improve the whole capture pipeline—motion handling, low light, skin tones, video stability, and portraits—without inventing textures, text, or facial detail.

## Locked decisions

- Processing is fully on-device. No cloud mode, uploads, remote account, or server dependency.
- Zoom detail is the flagship capability.
- Zoom processing modes are `Quick`, `Auto`, and `Max Detail`.
- `Auto` is the default and enables heavier processing only when phone and subject stability make it useful.
- The default rendering profile is natural and realistic: restrained sharpening, conservative denoising, neutral color, smooth highlight roll-off, and no beauty treatment by default.
- Version 1 saves JPEG only.
- RAW/DNG is on the roadmap after the JPEG pipeline is stable.
- Temporary burst frames remain local and are discarded after the output JPEG is committed.
- Processing adapts to temperature, battery, memory pressure, and motion instead of blocking or overheating the device.

## Capability-audit constraints

The first on-device report establishes the following public Camera2 baseline:

- One public rear camera ID and one public front camera ID.
- No exposed logical multi-camera capability or physical rear camera IDs.
- Rear camera hardware level `LEVEL_3` with manual sensor/post-processing, RAW, burst capture, and YUV/PRIVATE reprocessing.
- Maximum public rear image size of 4080 × 3072 (about 12.5 MP).
- No public 50 MP maximum-resolution/remosaic path was advertised.
- Rear OIS control is reported as available; public video-stabilization control is not.
- Only the Night camera extension is exposed.

Therefore version 1 must not depend on direct ultrawide/telephoto access or dual-rear-camera fusion. The initial flagship zoom implementation is single-camera multi-frame super-resolution using rear camera ID `0`. A dynamic audit will test whether the OEM HAL silently changes sensors at some zoom ratios, but this is not assumed by the architecture.

## Proposed capture pipeline

1. Maintain a short zero-shutter-lag frame buffer where runtime tests prove it is reliable.
2. Capture a motion-aware YUV burst using short exposures from the public rear camera.
3. Select a sharp reference frame.
4. Align frames using image motion and gyroscope timestamps.
5. Reject moving or unreliable regions to avoid ghosts.
6. Fuse recoverable detail at sub-pixel precision.
7. Use the tested public zoom/crop path; do not assume a separately addressable telephoto camera.
8. Apply natural tone mapping, texture-preserving denoising, and restrained sharpening.
9. Encode one share-ready JPEG into Android MediaStore.

## Camera-screen UX baseline

The production camera screen should feel familiar without copying another application's proprietary assets:

- Full-screen preview.
- Compact top controls and expandable settings.
- Zoom selector near the preview edge.
- Mode strip around Photo, Video, Portrait, and later Pro/RAW modes.
- Large central shutter button.
- Front/rear camera switch on the right.
- Circular thumbnail of the latest successfully saved photo at the bottom left.
- Tapping that thumbnail opens the exact photo in the phone's default photo viewer.

The external default viewer supplies its normal actions—share, edit, add to album/favorites, delete, metadata, and overflow menus. Those viewer controls are not reimplemented inside the camera app.

## Roadmap after diagnostics

1. Complete dynamic zoom, burst-throughput, timestamp, and thermal benchmarks.
2. Minimal production camera preview and reliable JPEG capture from rear ID `0`.
3. Gallery thumbnail/default-viewer integration.
4. Single-camera burst fusion and motion-aware HDR.
5. Single-camera super-resolution zoom with Quick, Auto, and Max Detail modes.
6. Add alternate rear lenses only if a tested public/vendor path is stable and distributable.
7. Video stabilization and temporal processing.
8. RAW/DNG and advanced controls.
