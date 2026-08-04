# Galaga community release asset verification

**Issue:** CAM-093 / #77  
**Target:** `Galaga-B4.1-260615-1653`  
**Community repository:** `spike0en/nothing_archive`  
**Release tag:** `Galaga_B4.1-260615-1653`

This procedure closes the tooling gap between locating the matching community release and producing a locally verified asset inventory. It does not redistribute firmware and does not mark any partition verified merely because GitHub publishes release metadata or a digest.

## Evidence boundary

The release tag and asset list establish provenance. They do not establish that downloaded bytes are complete, that an image belongs to the EEA target build, or that an extracted partition matches the device fingerprint.

The verifier therefore uses separate states:

- `METADATA_ONLY_NOT_LOCALLY_VERIFIED`: release metadata was retrieved, but no asset bytes were hashed locally;
- `GITHUB_REPORTED_DIGEST_NOT_LOCALLY_VERIFIED`: GitHub reports a SHA-256 value, but local bytes were not checked;
- `DIGEST_NOT_PUBLISHED_NOT_LOCALLY_VERIFIED`: GitHub did not expose a digest and local bytes were not checked;
- `VERIFIED_TWO_PASS_LOCAL_SHA256`: a selected asset was hashed while downloading, re-hashed from disk, size-checked, and compared with the GitHub-reported digest when one exists.

A locally verified release asset is still not automatically a verified partition. Compressed archives must be extracted outside the repository, and their partition images must pass `tools/index-firmware-images.py` plus target-build identity checks.

## Record release metadata without downloading images

Run from the repository root:

```sh
python3 tools/fetch-github-release-assets.py \
  --repository spike0en/nothing_archive \
  --tag Galaga_B4.1-260615-1653 \
  --output /secure/path/galaga-community-release-manifest.json
```

The generated JSON records:

- exact repository and release tag;
- release ID, URL, publication state, and publication timestamp;
- asset IDs, names, byte sizes, content types, and download URLs;
- GitHub-reported SHA-256 values when the API exposes them;
- an explicit verification boundary and per-asset status.

Use `GITHUB_TOKEN` when unauthenticated API rate limits are insufficient. Never place a token in command history or the generated manifest.

## Require GitHub-published digests

For an audit that should fail when any release asset lacks a GitHub-reported digest:

```sh
python3 tools/fetch-github-release-assets.py \
  --output /secure/path/galaga-community-release-manifest.json \
  --require-github-digests
```

A GitHub-reported digest is still provenance, not a substitute for locally hashing the selected bytes.

## Download and verify selected assets

Downloads are opt-in and must name every asset explicitly. The tool refuses `--download-dir` without at least one `--asset`, preventing an accidental multi-gigabyte bulk download.

```sh
python3 tools/fetch-github-release-assets.py \
  --output /secure/path/galaga-community-release-manifest.json \
  --download-dir /secure/path/galaga-release-assets \
  --asset '<exact-release-asset-name>'
```

Repeat `--asset` for additional files. The tool:

1. rejects path traversal, path separators, duplicate names, duplicate selections, non-HTTPS URLs, empty assets, and non-uploaded assets;
2. streams the download to a temporary file while computing SHA-256;
3. verifies the byte count against release metadata;
4. re-hashes the completed temporary file from disk;
5. compares the local digest with GitHub’s digest when published;
6. atomically moves the verified file into the destination;
7. removes partial files after any failure;
8. refuses to overwrite an existing destination.

Keep the download directory outside the repository. Do not commit proprietary archives or images.

## Continue to partition verification

After authorized extraction or reconstruction, index partition bytes separately:

```sh
python3 tools/index-firmware-images.py /secure/path/to/galaga-260615-images \
  --root . \
  --source-id nothing-archive-index \
  --collector '<operator-or-system-id>' \
  --collected-at '<timezone-aware-ISO-8601>' \
  --output /secure/path/galaga-260615-partition-inventory.json
```

Before CAM-093 can close, an independent reviewer must also verify:

- the target fingerprint contains `GalagaEEA` and `2606151653`;
- incremental reconstruction used the exact `260415-1710` base state where applicable;
- required partitions are present or their absence is independently evidenced;
- partition hashes reproduce on a second verification pass;
- proprietary bytes remain outside the public repository.

## Validation

```sh
python3 -m unittest tests/test_fetch_github_release_assets.py -v
python3 -m py_compile tools/fetch-github-release-assets.py
```
