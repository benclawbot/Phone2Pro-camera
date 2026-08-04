# Galaga firmware acquisition and partition indexing

**Index version:** 2026.08.04-1  
**Target device:** CMF Phone 2 Pro (`Galaga`, A001, EEA)  
**Target fingerprint:** `Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys`  
**Target release:** `Galaga-B4.1-260615-1653`  
**Machine-readable provenance:** [`research/galaga-firmware-acquisition.v1.json`](../research/galaga-firmware-acquisition.v1.json)

This document defines a reproducible and rights-conscious acquisition workflow. It does not redistribute firmware or claim hashes that have not been computed from locally acquired bytes.

## Current evidence

The target release is identified by the recorded device fingerprint and Nothing’s release metadata. A community-maintained firmware index records:

- an incremental OTA from `Galaga-B4.1-260415-1710` to `Galaga-B4.1-260615-1653`;
- no full OTA for the target release;
- a community release tag for extracted or reconstructed OTA images.

The exact OEM incremental package endpoint recorded in the source index is hosted through Google’s Android OTA infrastructure. Its opaque URL token is **not** a SHA-256 digest and must never be stored as one.

The community index is useful provenance but is not an OEM source tree or an independent integrity proof. Community image assets must be reproduced or downloaded by an authorized operator and hashed locally before they can support a verified partition record.

## Why CAM-093 remains open

The issue cannot close yet because:

- the incremental OTA bytes have not been acquired and hashed in the controlled workspace;
- the exact base build image set is needed for independent target reconstruction;
- community release asset names, sizes, and digests have not been independently verified;
- no local SHA-256 inventory exists for the target partitions;
- all required partition rows remain `NOT_VERIFIED`.

The merged provenance/indexing framework is groundwork, not evidence that the firmware acquisition is complete.

## Required partition coverage

The acquisition index requires at least these camera-relevant partitions when present in the target build:

| Group | Partitions | Camera relevance |
|---|---|---|
| Logical | `system`, `system_ext`, `product` | Framework services, public API behavior, permissions, overlays, and stock package dependencies |
| Vendor/device logical | `vendor`, `odm` | Camera provider/HAL libraries, tuning, configuration, permissions, and policy |
| Dynamic kernel modules | `vendor_dlkm`, `odm_dlkm`, `system_dlkm` | Kernel modules and module metadata |
| Boot | `boot`, `init_boot`, `vendor_boot`, `dtbo` | Kernel/ramdisks, vendor services/modules, fstab, and device-tree overlays |
| Verification | `vbmeta`, `vbmeta_system`, `vbmeta_vendor` | Verified-boot chain and exact image provenance |
| Camera/accelerator firmware | `ccu`, `apusys` | MediaTek camera-control and accelerator firmware when present |

A missing partition must remain explicitly missing. Do not create placeholder bytes or infer that a partition is absent solely because it is missing from one community archive.

## Acquisition procedure

### 1. Record the source before downloading

For every package or image record:

- source ID from `research/galaga-firmware-acquisition.v1.json`;
- exact URL or device-pull method;
- target and base build identifiers;
- region;
- collection time and collector identity;
- legal/redistribution handling.

Do not commit proprietary package or image bytes to this repository.

### 2. Acquire the OEM incremental OTA

Download the `oem-incremental-ota` package outside the repository using an authorized workstation. Immediately record:

```sh
sha256sum <ota-package>.zip
stat -c '%s' <ota-package>.zip        # Linux
stat -f '%z' <ota-package>.zip        # macOS
```

The locally computed digest and byte size belong in a private acquisition record. They may be copied into a derived inventory only after the file has been re-hashed in the controlled workspace.

### 3. Acquire the exact base build

The target package is incremental from `Galaga-B4.1-260415-1710`. Deterministic target reconstruction requires the exact base partition state expected by the OTA payload.

Acceptable inputs include:

- independently verified base partition images from an authorized archive;
- a user-provided device dump from the exact base build;
- a community image set whose bytes are independently hashed and whose provenance is retained.

A different region or build is not interchangeable.

### 4. Extract or reconstruct without redistributing

Use an audited OTA extraction/reconstruction tool under its applicable licence. Record:

- tool name, version/commit, and licence;
- command line;
- base image hashes;
- OTA package hash;
- output logs;
- output image hashes.

For incremental payloads, extraction without the correct base can produce incomplete or invalid output. A tool’s success exit code is not enough; verify output sizes, hashes, filesystem metadata, and target build properties.

### 5. Create the local partition inventory

Place only the local images to be indexed in an isolated directory. Run:

```sh
python3 tools/index-firmware-images.py /secure/path/to/galaga-260615-images \
  --root . \
  --source-id oem-incremental-ota \
  --collector '<operator-or-system-id>' \
  --collected-at '2026-08-04T10:00:00+02:00' \
  --output /secure/path/to/galaga-260615-inventory.json
```

The tool:

- rejects symlinks;
- hashes regular files in streaming mode with SHA-256;
- recognizes only required partition names and approved firmware/image suffixes;
- records byte size, relative path, source, collection timestamp, and collector;
- marks only locally hashed artifacts `VERIFIED_LOCAL_SHA256`;
- reports every required partition still missing.

The generated private inventory may be reduced to non-sensitive hashes and metadata for repository review. Do not commit absolute paths, user identifiers, package credentials, or proprietary bytes.

### 6. Verify target identity

Before a partition supports a claim, verify target build identity from extracted properties or mounted filesystem metadata where applicable:

- fingerprint contains `2606151653` and the expected `GalagaEEA` region;
- partition metadata is consistent with the target release;
- dynamic partition relationships are preserved;
- vbmeta records correspond to the indexed image set;
- image hashes are reproduced by a second verification pass.

If any identity check is ambiguous, retain `NOT_VERIFIED`.

## Hash and status rules

Only lowercase 64-character SHA-256 values computed from local bytes are accepted. The following are not partition digests:

- OTA URL tokens;
- Git object IDs;
- ETags;
- release tags;
- package names;
- checksums copied without source and independent verification.

A partition can move from `NOT_VERIFIED` to `VERIFIED_LOCAL_SHA256` only when the inventory contains source ID, safe relative path, partition name, positive byte size, SHA-256, timezone-aware collection timestamp, and collector.

## Legal and redistribution handling

Firmware, stock applications, tuning, calibration, and vendor binaries may be proprietary or mixed-rights artifacts. Project policy is:

- keep raw packages and images outside the public repository;
- store links, hashes, sizes, build identifiers, and derived findings only;
- do not mirror OEM packages or community assets without verified rights;
- do not publish user/device dumps without explicit owner permission;
- follow the source/licence register and clean-room boundary in [`docs/SOURCE_LICENCE_COMPLIANCE.md`](SOURCE_LICENCE_COMPLIANCE.md).

## Completion criteria

CAM-093 may close only after:

1. the exact target fingerprint is recorded;
2. the OEM package or equivalent target source is locally hashed;
3. base-build provenance is verified for incremental reconstruction;
4. required partitions are acquired or explicitly proven absent;
5. every acquired partition has independently reproduced SHA-256 and size metadata;
6. extraction commands, tool versions, and provenance are recorded;
7. proprietary artifacts remain outside the repository;
8. a reviewer confirms the inventory and target-build identity.
