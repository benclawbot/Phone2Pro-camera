# Firmware and package version matrix

Status: authoritative build-context index for CAM-002.

The machine-readable matrix is:

```text
data/builds/version-matrix.json
```

Its schema is:

```text
schemas/version-matrix.schema.json
```

Every diagnostic experiment in `data/artifacts/diagnostic-manifest.yaml` must
contain `buildMatrixEntryId` and point to one existing matrix entry. The
manifest's `deviceBuild.matrixEntryId` identifies the default build context for
the current artifact set.

## Current build entry

The initial matrix entry covers the controlled Android 16 / June 2026 Galaga
diagnostic context:

```text
matrix ID:
  nothing-galaga-eea-android16-2606151653-f88325f3

device:
  Nothing A001 / Galaga / GalagaEEA
  MediaTek MT6878

platform:
  Android 16 / SDK 36
  security patch 2026-06-01
  build ID BP2A.250605.031.A3
  build number 2606151653
  user / release-keys

fingerprint:
  Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys

stock camera:
  package com.nothing.camera
  version 16.1.01.93.20
  SHA-256 f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea
```

The entry is `partial`, not `verified`, because the marketing Nothing OS
version, camera package version code, and diagnostic application package/source
revision were not preserved in the normalized evidence. Those fields remain
explicitly unknown rather than inferred.

## Immutable identity

A matrix entry identifies an exact firmware fingerprint and exact camera APK
set. Its `identitySha256` is the SHA-256 of canonical compact JSON containing:

```json
{
  "buildFingerprint": "<exact fingerprint>",
  "cameraPackages": [
    {
      "packageName": "<package>",
      "sha256": "<APK SHA-256>",
      "versionName": "<version>"
    }
  ]
}
```

Camera packages are sorted by package name, version and hash before hashing.
The matrix ID must end with the first eight hexadecimal characters of the
identity digest.

Changes to the fingerprint, package name, package version or APK hash create a
new matrix entry and a new ID. They must not overwrite an existing identity.
Evidence notes, confidence status, recovered version codes or additional
artifact links may be added to an existing entry by incrementing
`entryRevision`, provided the identity digest remains unchanged.

Repository validation recalculates every identity, verifies the ID suffix,
checks duplicate identities, validates the JSON schema, and confirms all
artifact and diagnostic-build links.

## Add a new tested build

1. Capture the exact device fingerprint, Android release, SDK, security patch,
   build ID/number/type/tags, region, device/product/model and SoC context.
2. Hash every installed stock camera APK or split. Record package name, version
   name, version code when observed, and SHA-256.
3. Create a new matrix entry. Calculate `identitySha256` from the canonical
   identity payload and suffix the entry ID with its first eight characters.
4. Add the diagnostic build record and its immutable artifact IDs.
5. Add `buildMatrixEntryId` to every new experiment artifact.
6. Run the repository validator and unit tests before using the entry in
   conclusions.

Unknown values must remain `null` or be described as unknown where the schema
allows it. Do not derive a security patch or marketing firmware version from a
build ID unless independent device evidence confirms it.

## Diff builds over time

List the entry IDs in the matrix, then compare two exact contexts:

```bash
python3 tools/matrix/diff-version-matrix.py \
  --from nothing-galaga-eea-android16-2606151653-f88325f3 \
  --to <new-matrix-entry-id> \
  --json /private/output/version-matrix-diff.json
```

The report separates:

- device, platform and firmware changes;
- camera package additions, removals, versions, version codes and hashes;
- diagnostic build additions, removals and status changes.

Use `--fail-on-change` in automation when any material change must stop a
baseline comparison. Evidence arrays, artifact-handling prose and diagnostic
artifact lists are excluded from material-change counts so provenance updates
do not masquerade as firmware or APK changes.

A matrix diff describes recorded state. It does not prove a behavioral change;
changed camera behavior still requires linked experiments under both immutable
build contexts.
