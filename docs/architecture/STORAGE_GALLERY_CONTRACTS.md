# Storage, gallery and system viewer contracts

Status: executable interface specification for CAM-107.

These contracts define safe asset publication, metadata privacy and recovery behavior. The current CameraX single-frame implementation continues to use its existing MediaStore output path until it is migrated to this transaction model.

## Evidence classification

- **VERIFIED:** Lifecycle validation, recovery decisions, metadata allowlists, published-only thumbnail/viewer rules and unit tests are implemented.
- **PARTIALLY VERIFIED:** The current application already opens the exact saved URI in the system viewer, but it has not yet migrated capture writes to the new journaled pending-row transaction.
- **HYPOTHESIS:** Stale-row timeouts and background scheduler choices require device testing.
- **UNKNOWN:** Final EXIF/XMP library choice, thumbnail cache policy and OEM gallery behavior remain unknown.

## Transactional MediaStore lifecycle

Every capture receives a `CaptureAssetRecord` and passes through validated states:

```text
RESERVED_PENDING
→ WRITING
→ PROCESSING (optional)
→ READY_TO_PUBLISH
→ PUBLISHED
```

Failure paths end in `FAILED` or `ABANDONED`.

Only `PUBLISHED` is visible to other applications. `MediaStoreWritePlan` requires Android 10+ rows to be reserved with `IS_PENDING=1`; publication is the explicit final `IS_PENDING=0` update after image bytes and metadata are complete.

`AssetLifecyclePolicy` rejects:

- direct publication from a reservation;
- publication without durable complete bytes;
- ready-to-publish state without durable bytes;
- transitions out of terminal states;
- failure reasons attached to non-failed assets.

This prevents partial encodes, failed processing and half-written metadata from becoming visible gallery assets.

## Background processing

An asset may enter `PROCESSING` after its durable source bytes exist. UI shutter readiness is independent from processing, but publication remains blocked until the final processed asset reaches `READY_TO_PUBLISH`.

The storage journal is durable and separate from in-memory UI state. Each record preserves:

- stable asset ID and MediaStore URI;
- display name and MIME type;
- optical route and capture profile;
- orientation;
- lifecycle;
- whether a durable source is recoverable;
- last update time;
- explicit failure reason.

## App termination recovery

`AssetRecoveryPolicy` replays the journal at startup:

- published asset: keep;
- ready asset with durable bytes: publish;
- writing/processing asset with durable source: resume;
- recent pending asset without durable source: wait for an active writer;
- stale pending asset without durable source: delete hidden MediaStore row;
- failed/abandoned record: remove terminal journal entry after cleanup.

A stale or inconsistent asset is deleted while still hidden; it is never made visible merely to preserve work.

## Metadata privacy

`MetadataPrivacyPolicy.privateByDefault()` excludes:

- location;
- device make/model identity;
- diagnostic XMP;
- processing XMP.

The standard allowlist retains non-sensitive photographic metadata required for correct rendering and organization:

- orientation;
- capture timestamp;
- exposure time;
- sensitivity;
- focal length;
- lens route;
- capture profile;
- software identifier.

Every sensitive field requires explicit opt-in. `MetadataWritePlan` records both included and privacy-omitted fields so diagnostics can explain why metadata is absent without recovering the private value.

## Orientation

Asset orientation is restricted to 0, 90, 180 or 270 degrees and is recorded before publication. Pixel rotation versus EXIF orientation remains an encoder/storage implementation choice, but the final asset must have one unambiguous display orientation.

## Gallery thumbnails

`ThumbnailReference` can only be created from a `PUBLISHED` record. It references the exact asset URI, route, capture profile and orientation and provides a non-empty accessibility label.

Pending, processing, failed and abandoned assets cannot appear as latest-photo thumbnails.

## System viewer

`ViewerIntentSpec.forPublished()` creates a platform-neutral contract for:

```text
ACTION_VIEW
exact content URI
exact MIME type
read permission grant
```

The app must open the specific selected asset, not a broad gallery landing page or an inferred file path. Current `MainActivity` already follows this exact-URI behavior for its existing saved image.

## Current migration boundary

The contracts are ready for a journal implementation and MediaStore transaction adapter. The existing CameraX output path has not yet been migrated, so this work must not be described as active crash-recovery support until the adapter and device tests are complete. The architecture nevertheless prevents future storage code from publishing partial assets or silently adding sensitive metadata.
