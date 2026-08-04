# Versioned external-source index

**Index version:** 2026.08.04-1  
**Target:** CMF Phone 2 Pro (`A001`, `Galaga`)  
**Observed build:** `2606151653`  
**Issue:** CAM-090 / #74

## Purpose

`research/external-source-index.v1.json` is the searchable catalogue for external evidence used by the project. It normalizes source identity without replacing the domain-specific registries that contain detailed findings.

Every record includes:

- classification and publisher;
- exact URL and revision, build, publication year, release tag or report date;
- licence or handling status;
- scope and target relevance;
- confidence and freshness/mismatch status;
- a stable `sourceId` and `citationKey` for claims;
- the authoritative repository registry and record ID.

## Claim references

Claims must store both the normalized `sourceId` and its `citationKey`. A citation key binds the claim to the indexed locator rather than a generic home page.

Examples:

- `nothing-device-modules-6.1-mt6878@2b0af666da693dcf4088b583bae7d77f4a4373e3`
- `aosp-system-media-android16@f01e84b958fb6a887dc0e74e4b5ebd159f03860a`
- `paper-hasinoff-hdrplus-2016@2016`
- `nothing-community-nos32-251103-camera@V3.2-251103-2121`
- `oem-incremental-ota@Galaga-B4.1-260415-1710..260615-1653`

A URL token, release tag, Git object ID or community statement cannot be substituted for a locally reproduced firmware SHA-256 or target implementation proof.

## Classifications

### Official vendor

- `nothing-support-release-note`
- `oem-incremental-ota`

The release note provides exact-build metadata. The incremental OTA remains an unverified proprietary artifact until authorized local acquisition and hashing.

### Community archive

- `nothing-archive-index`

The archive is useful for discovery but derived images and digests require independent reproduction.

### Official source code

- `nothing-kernel-6.1-mt6878`
- `nothing-kernel-modules-mt6878`
- `nothing-device-modules-6.1-mt6878`
- `nothing-galaga-kernel-2026-04`

These are official Galaga sources for `B4.1-260415-1710`. They are deliberately flagged `BUILD_MISMATCH` against the observed `2606151653` firmware.

### Platform source code

- `chromeos-platform-camera-head-2026-01`
- `chromeos-mtkcam-content-2021`
- `chromeos-mtkcam-request-2023`
- `chromeos-mtkcam-pipeline-2023`
- `aosp-system-media-android16`

AOSP Android 16 is the platform metadata baseline. ChromiumOS MediaTek sources are revision-pinned architectural analogues and remain `PLATFORM_MISMATCH` for Galaga Android userspace.

### Reference implementations

- `androidx-camera-pipe`
- `grapheneos-camera`
- `open-camera`
- `motioncam`
- `photoncamera`
- `libre-camera`
- `impl-halide`
- `impl-google-kpn`
- `impl-opencv-photo`

The index preserves each reviewed licence and reuse boundary. GPL-family projects remain clean-room references under the architecture/compliance review.

### Academic primary sources

- `paper-hasinoff-hdrplus-2016`
- `paper-liba-low-light-2019`
- `paper-wronski-mfsr-2019`
- `paper-mildenhall-kpn-2018`
- `paper-zhang-gyro-2018`
- `paper-mertens-exposure-fusion-2007`
- `paper-reinhard-tone-2002`
- `paper-paris-local-laplacian-2011`
- `paper-bhat-burstsr-2021`
- `paper-sidd-2018`
- `paper-dnd-2017`

These records support method assumptions, artefacts and benchmark design. They do not provide automatic code, model, dataset or patent clearance.

### Dataset references

- `benchmark-hdrplus-burst`
- `benchmark-burstsr`
- `benchmark-sidd`
- `benchmark-dnd`

Dataset and benchmark terms remain pending review. Every production method also requires the private controlled Galaga benchmark defined in the literature registry.

### Community reports

- `nothing-community-gcam-32911`
- `nothing-community-camera-feedback-79`
- `nothing-community-nos32-251103-camera`
- `nothing-community-nos41-260415-camera`
- `nothing-community-update-ruined-camera-38107`
- `nothing-community-camera-feedback-20`
- `nothing-community-camera-feedback-39`
- `nothing-community-camera-feedback-146`

Community records are date/build scoped. Their confidence is limited to second-hand lead, single observation or corroborated observation, and `implementationProof` must remain false.

## Search facets

Consumers can filter by:

- `classification` — official, source, implementation, academic, community, dataset;
- `publisher` and `license`;
- `targetRelevance` — direct target, baseline, analogue, method, benchmark or lead;
- `confidence`;
- `freshness` — exact build, mismatch, platform baseline, historical method or date-scoped observation;
- `buildScope` and `sourceRegistry`.

## Freshness and mismatch rules

`BUILD_MISMATCH`, `PLATFORM_MISMATCH`, `EXACT_BUILD_UNVERIFIED_ARTIFACT`, `HISTORICAL_METHOD`, `DATE_SCOPED_OBSERVATION` and `DATASET_TERMS_PENDING` records require explicit mismatch or limitation notes.

A record may become stale when:

- a newer official Galaga source drop appears;
- the tested firmware or stock camera version changes;
- an upstream revision or licence changes;
- a paper/benchmark is superseded for the claimed purpose;
- a community report gains exact build/app context or controlled reproduction.

## Registry coverage

The validator compares the catalogue with these authoritative record selectors:

- `research/galaga-firmware-acquisition.v1.json` → `sources`
- `research/galaga-kernel-source-index.v1.json` → `repositories`
- `research/mediatek-public-camera-cross-reference.v1.json` → `sources`
- `research/community-camera-evidence.v1.json` → `sources`
- `research/open-source-camera-architecture-review.v1.json` → `projects`
- `research/computational-photography-literature.v1.json` → `papers`
- `research/computational-photography-literature.v1.json` → `implementations`
- `research/computational-photography-literature.v1.json` → `benchmarks`, excluding the internal `benchmark-galaga-controlled`

Adding, removing or renaming an external record in those registries makes validation fail until this catalogue is updated.

## Non-claims

- The index does not certify that external content is correct, current or legally reusable beyond the recorded evidence.
- Revision-pinned public source does not prove equivalence to proprietary Galaga userspace.
- Exact-build metadata does not verify firmware bytes or partition hashes.
- Community corroboration does not establish implementation or root cause.
- Academic publication does not establish target performance, licence compatibility or patent clearance.

Validation: `tools/validate-external-source-index.py`.
