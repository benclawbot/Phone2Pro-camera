# Open-source Android camera architecture review

**Index version:** 2026.08.04-1  
**Target:** CMF Phone 2 Pro replacement camera  
**Project licence:** MIT  
**Issue:** CAM-096 / #80

## Purpose

This review compares revision-pinned open-source Android camera projects against the replacement app’s capture/session, RAW/YUV, burst, gyro, storage, error-handling, privacy and testing requirements.

It is an engineering compliance record, not legal advice. “Open source” does not automatically mean that code can be copied into this MIT project. Every recommendation records a reuse decision and an implementation mode.

## Reviewed projects

### `androidx-camera-pipe`

Revision `08835fcf4a40e042e26efd86a3ac70d79b561e86` of `androidx/androidx` is Apache-2.0. CameraPipe separates immutable graph configuration, streams, session parameters, default/required request parameters, backend selection, graph state, request listeners and device-quirk flags. Its simulator and session tests are directly relevant to the existing portable session engine.

**Decision:** `DIRECT_REUSE_APPROVED`. Keep attribution/NOTICE obligations and prefer the existing published AndroidX dependency rather than copying internals unnecessarily.

### `grapheneos-camera`

Revision `db39c2ddc9d1427fafcec9d8eb2c30f817b6a597` is MIT. The app uses CameraX and demonstrates privacy-first capture intents, MediaStore/SAF handling, early `ImageProxy` closure, staged image extraction/write/thumbnail work, pending-item finalization, incomplete-output cleanup, EXIF controls and regression tests.

**Decision:** `DIRECT_REUSE_WITH_ATTRIBUTION_REVIEW`. Reuse only after checking copied-file provenance, dependencies and retained notices.

### `open-camera`

The reviewed SourceForge master snapshot identifies revision `0dd4cb` / application commit `8b577f` and GPL-3.0-or-later licensing. It provides mature Camera2 capability probing, device quirks, RAW/DNG, bracketing, queued saving, MediaStore/SAF and user-visible failure handling.

**Decision:** `CLEAN_ROOM_PATTERN_ONLY`. Use behavior and test inventories; do not copy implementation into the MIT app without a deliberate GPL-compatible distribution decision.

### `motioncam`

Revision `cc7f7c9cad5234bc939699b1ab1ffbc4bdfd6690` is GPL-3.0-only. It demonstrates NDK Camera2 session ownership, explicit callback/error events, bounded RAW buffering, timestamp-selected buffer consumption, background RAW capture and multi-frame processing.

**Decision:** `CLEAN_ROOM_PATTERN_ONLY`. Derive independent buffer ownership, backpressure and timestamp requirements from observed behavior and public interfaces.

### `photoncamera`

Revision `92a68b5f456f25611093188f2c56ea0beeb30b3c` is GPL-3.0-only at repository level. It contains Camera2 RAW/YUV capture, burst frame selection, gyro snapshots, deblur inputs, processing executors and multiple saver paths. Some files retain upstream Apache headers, but repository-level reuse still requires file-by-file provenance and legal review.

**Decision:** `CLEAN_ROOM_PATTERN_ONLY`. Use the gyro/frame-association and capture-state concepts as independent requirements, not copied code.

### `libre-camera`

Revision `23490e2c73c3281ec28dccbeb377ec4bad1d177c` is GPL-3.0-only. The Flutter app demonstrates a compact privacy-oriented settings surface, optional EXIF, save-location selection and common photo/video controls. Its Flutter camera abstraction also documents limitations for multiple-camera switching, custom resolution and frame-rate control.

**Decision:** `CLEAN_ROOM_PATTERN_ONLY`. Use UI and settings lessons only; it is not a backend candidate for the replacement app’s low-level RAW, burst or vendor-session requirements.

## Domain comparison

| Project | Capture/session | RAW/YUV | Burst | Gyro | Storage | Error handling |
|---|---|---|---|---|---|---|
| AndroidX CameraPipe | Full | Partial | Full | Not observed | None | Full |
| GrapheneOS Camera | Partial | Partial | None | Not observed | Full | Full |
| Open Camera | Full | Full | Full | Not observed | Full | Full |
| MotionCam | Full | Full | Full | Not observed | Partial | Full |
| PhotonCamera | Full | Full | Full | Full | Full | Partial |
| Libre Camera | Partial | None | None | None | Full | Partial |

The detailed JSON also compares privacy/intents and testing. `NONE` and `NOT_OBSERVED` are deliberate; the review does not infer missing code from product marketing.

## Recommendations

### `rec-camera-pipe-graph-contract`

Keep `CaptureSessionPlan` as the portable immutable graph description and align its binder adapters with CameraPipe’s separation of streams, session parameters, default/required request parameters, backend and graph state. Do not replace the existing engine wholesale.

### `rec-camera-pipe-simulation`

Add simulator/fake-backend tests around session recreation, repeating-before-capture requirements, disconnect behavior and surface lifecycle. CameraPipe’s testing architecture is directly reusable under Apache-2.0.

### `rec-graphene-storage-pipeline`

Adopt, after attribution/dependency review, a staged output pipeline that closes scarce image resources early, writes once, finalizes MediaStore pending entries, deletes incomplete outputs, supports SAF and keeps location/EXIF disclosure explicit.

### `rec-clean-room-raw-buffer-pool`

Implement an independent bounded RAW/YUV buffer pool with explicit memory accounting, ownership transfer, cancellation, backpressure and timestamp-based selection. MotionCam is requirements evidence only; no GPL code is to be copied.

### `rec-clean-room-gyro-frame-association`

Implement an independent gyro sample ring and immutable per-frame gyro snapshot keyed to the existing timestamp clock domain. Reject clock-domain or tolerance mismatches before alignment. PhotonCamera is concept evidence only.

### `rec-open-camera-test-inventory`

Convert Open Camera’s mature capability, focus/exposure, bracketing, storage and failure cases into tests for the replacement app. Keep project-specific quirks isolated and evidence-driven instead of copying a monolithic controller.

### `rec-libre-camera-ui-boundary`

Use Libre Camera as a clean-room UI/settings reference for privacy defaults, format/resolution controls and save-location selection. Do not adopt Flutter or its camera plugin as the capture backend.

### `rec-no-gpl-code-import`

Block GPL-family source copying and dependencies unless the project explicitly chooses compatible distribution terms and updates the compliance register. Clean-room requirements, independently written tests and high-level architectural observations remain allowed.

## Resulting architecture direction

1. Retain CameraX for verified public lifecycle/use-case binding.
2. Retain direct Camera2 and vendor adapters behind the existing isolated binder boundary.
3. Treat `CaptureSessionPlan`, request scopes, bounded recovery and timestamp correlation as the portable source of truth.
4. Add CameraPipe-style graph simulation and backend conformance tests.
5. Add a privacy-first staged storage pipeline.
6. Add independent bounded RAW/YUV buffering and gyro/frame association only after device capability checks.
7. Keep all GPL-derived work clean-room and traceable to written requirements rather than copied implementation.

## Non-claims

- This review does not certify licence compliance for a future release.
- A permissive project is not approved for wholesale copying; file provenance and dependencies still require review.
- A GPL project’s architecture does not become MIT-compatible merely because it is re-described here.
- The comparison does not prove that Galaga exposes RAW, auxiliary physical cameras, reprocessing or gyro synchronization.
- The review does not replace target-device validation or the source/licence compliance register.

## Maintenance

Update the review when an upstream revision or licence changes, a new dependency is proposed, the replacement app adds RAW/gyro/storage implementation, or a release compliance review changes a reuse decision.

Machine-readable source: `research/open-source-camera-architecture-review.v1.json`  
Validation: `tools/validate-open-source-camera-architecture-review.py`
