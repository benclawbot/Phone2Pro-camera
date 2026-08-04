# CMF Phone 2 Pro community camera evidence

**Index version:** 2026.08.04-1  
**Target:** CMF Phone 2 Pro (`A001`, `Galaga`)  
**Observed build:** `2606151653`  
**Issue:** CAM-095 / #79

## Purpose

This document tracks community observations about Camera2 exposure, GCam behavior, stock lens switching, firmware regressions, focus, image processing and camera-app stability. It is a research intake system, not a capability specification.

A report can identify a useful experiment. It cannot establish implementation, privilege, vendor-tag semantics, physical sensor use or root cause without controlled evidence.

## Evidence grades

- `SECOND_HAND_LEAD`: notification or repeated claim without on-device testing.
- `SINGLE_REPORT`: one owner reports a behavior without independent reproduction.
- `MULTIPLE_INDEPENDENT_REPORTS`: distinct participants report materially similar behavior, still under uncontrolled conditions.
- `OFFICIAL_CONTEXT_PLUS_REPORT`: an official changelog establishes build context and a participant reports behavior on that release.

These grades rank test priority only. None is implementation proof.

## Source contexts

### `nothing-community-gcam-32911`

The May 2025 GCam thread identifies the device as Nothing A001. The original poster repeated a GCamator notification for a GCam 8.4 build but did not own or test the phone. A separate participant reported Camera2 API level 3 and only one rear camera in Camera2 API Probe, while explicitly stating that GCam was not tested. The build, probe version and complete export are unknown.

### `nothing-community-camera-feedback-79`

A December 2025 feedback page contains a detailed single-user stock-video matrix. The participant reported 0.6x/1x/2x switching at 1080p30, no telephoto selection at 1080p60, and fixed preselected 1x or 2x routes during 4K30 recording. The post uses UI behavior to infer sensors; it does not include synchronized focal-length or physical-camera metadata.

The same page also contains multiple reports about darker or artificial post-processing, front-camera HDR/texture changes, motion blur and slow-shutter behavior.

### `nothing-community-nos32-251103-camera`

The V3.2-251103-2121 discussion gives exact firmware context. Multiple participants report HDR, low-light, skin-tone, exposure and processing regressions. One contributor states that private media samples, logs and crash reports were supplied to support, but those artifacts are not public repository evidence.

The thread also reports main/tele color variance and a visible 1x-to-2x shift. These are corroborated observations, not proof of an optical-route implementation or common root cause.

### `nothing-community-nos41-260415-camera`

The official B4.1-260415-1710 changelog says overall camera stability improved. One participant reports that a prior video lens-switching glitch was fixed. Another reports focus oscillation beginning with OS 4.0 and persisting on this release, with lens-specific distant-focus behavior. The changelog does not identify either defect by name.

### `nothing-community-update-ruined-camera-38107`

A single post reports that processing artifacts returned after an unspecified recent update. An attached image increases reproducibility value but the exact build and before/after protocol remain absent.

### `nothing-community-camera-feedback-20`

This page includes separate single-user reports of warmer telephoto versus main-camera rendering and occasional device restart after extended stock-camera use. No camera version, logs, thermal state or reboot reason is supplied.

### `nothing-community-camera-feedback-39`

This page collects moving-subject blur, post-processing artifacts, selfie smoothing, camera lag and color changes. It is useful for test design but mixes scenes, builds, lighting and modes.

### `nothing-community-camera-feedback-146`

A February 2026 post compares front-camera preview and final output and reports strong smoothing after beauty options were disabled. Additional participants describe similar processing. The reports do not isolate HDR, face retouching, tone mapping or display color management.

## Indexed reports

### Public IDs and GCam

- `report-gcamator-v84-device-lead`: second-hand indication that one GCam 8.4 build was labelled compatible with A001. Compatibility remains undefined.
- `report-camera2-level3-one-rear-id`: one Camera2 API Probe participant reported level 3 and a single rear ID. This does not rule out hidden, logical, physical or system-only routes.

### Stock video routing

- `report-stock-video-1080p30-three-lens-switching`: UI-observed 0.6x/1x/2x handover at 1080p30.
- `report-stock-video-high-mode-route-limits`: UI-observed restrictions at 1080p60 and 4K30.
- `report-nos41-switching-glitch-improved`: official camera-stability context plus one positive report after B4.1-260415-1710.

### Firmware and processing

- `report-nos32-processing-regression-cluster`: multiple reports on exact build V3.2-251103-2121 covering HDR, exposure, skin tone, low light and processing latency.
- `report-nos32-main-tele-handover-glitch`: reports of 1x/2x shift and route-dependent rendering on the same build.
- `report-front-camera-postprocessing-cluster`: preview/final selfie processing differences reported by multiple participants.

### Focus and stability

- `report-os40-os41-focus-oscillation`: one device report of focus oscillation persisting through B4.1-260415-1710.
- `report-long-camera-session-reboot`: one report of shutdown/restart after prolonged camera use.

## Controlled tests

### `test-public-camera-id-enumeration`

Record exact build, package versions and complete machine-readable CameraManager output. Enumerate IDs, hardware level, focal lengths, logical/physical IDs and open results twice. A probe screenshot or count is insufficient.

### `test-gcam-build-and-lens-matrix`

For one explicitly identified and lawfully acquired third-party build, record package/version/signer metadata without redistributing the APK. Test photo/video routes and correlate CameraService opens, IDs, focal lengths, crop regions and output metadata. Installation or main-camera capture does not imply auxiliary support.

### `test-stock-video-route-matrix`

Test 1080p30, 1080p60 and 4K30 across 0.6x, 1x and 2x before and during recording. Confirm physical routing only through synchronized metadata or sensor evidence.

### `test-lens-handover-continuity`

Use fixed geometry, illumination and color targets. Measure field-of-view, white-balance, exposure, focus, timestamp and physical-route discontinuities at handover. A regression requires controlled build-to-build change.

### `test-build-controlled-image-regression`

Capture matching scenes and settings before and after firmware updates. Preserve original hashes and metadata privately, and compare clipping, color, tone, sharpness and latency. Forum-compressed examples alone cannot establish a regression.

### `test-preview-final-processing-delta`

Capture preview/final pairs, RAW/JPEG where available, and HDR/beauty variants under fixed light. Compare in a common color space while logging face detection, exposure and processing latency.

### `test-cross-lens-autofocus`

Measure near, mid and far targets on 0.6x, 1x and 2x. Record AF state, lens position, timing, sharpness, route and build. Compare another unit where possible before classifying firmware versus actuator/calibration failure.

### `test-stock-camera-soak`

Run a bounded repeatable camera workload while recording thermal, memory, battery, CameraService, tombstone, pstore and reboot information. Stop on unsafe temperature or repeated instability. Do not assign a cause without a matching artifact.

## Non-claims

- A community report does not prove Camera2 internals, hidden APIs, vendor-tag meanings or privilege boundaries.
- One rear ID in a probe does not prove auxiliary sensors are absent.
- A stock UI lens label does not prove which sensor produced the frame.
- Corroboration raises priority but does not establish root cause.
- An official stability statement does not enumerate every fixed or remaining defect.
- This project does not recommend or redistribute third-party camera packages, private logs or user photographs.

## Maintenance

Update the register when exact build/app versions or raw exports appear, independent reports corroborate or contradict an entry, controlled tests produce target evidence, or firmware changes public IDs, routing, focus, processing or stability.

Machine-readable source: `research/community-camera-evidence.v1.json`  
Validation: `tools/validate-community-camera-evidence.py`
