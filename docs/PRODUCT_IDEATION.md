# Product ideation baseline

This document records the decisions agreed before the CMF Phone 2 Pro capability audit. They are product goals, not claims that every feature is available through the phone's public camera APIs.

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

## Proposed capture pipeline

1. Maintain a short zero-shutter-lag frame buffer where supported.
2. Capture a motion-aware burst using short exposures.
3. Select a sharp reference frame.
4. Align frames using image motion and gyroscope timestamps.
5. Reject moving or unreliable regions to avoid ghosts.
6. Fuse recoverable detail at sub-pixel precision.
7. Select or fuse main and telephoto cameras only when the capability audit proves synchronization and output quality are sufficient.
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

1. Capability report and repeatable on-device benchmarks.
2. Minimal production camera preview and reliable JPEG capture.
3. Gallery thumbnail/default-viewer integration.
4. Single-camera burst fusion and motion-aware HDR.
5. Super-resolution zoom and automatic main-versus-telephoto selection.
6. Dual-camera fusion only if the HAL exposes usable synchronized streams.
7. Video stabilization and temporal processing.
8. RAW/DNG and advanced controls.
