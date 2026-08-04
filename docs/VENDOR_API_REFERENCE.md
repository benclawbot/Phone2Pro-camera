# MediaTek and Nothing vendor API reference

This reference covers every MediaTek and Nothing camera metadata key materialized for the CMF Phone 2 Pro (`Galaga`, model `A001`) on the observed firmware fingerprint recorded in `data/vendor-tags/database.v1.json`.

The complete per-key reference is generated from committed evidence:

```bash
python3 tools/build-vendor-api-reference.py
python3 tools/validate-vendor-api-reference.py
```

To write the generated JSON to a file:

```bash
python3 tools/build-vendor-api-reference.py \
  --output out/vendor-api-reference.v1.json
```

## Evidence boundary

Each record exposes the following sections:

- `type`: Java/native type, vendor/tag identifiers, byte layout and confidence.
- `values`: advertised values, routing-trace values, enum/bitfield status and write-value status.
- `ordering`: the required characteristic, session, request, physical-request or result phase.
- `dependencies`: exact build, camera IDs, advertisement state and stock call-site evidence.
- `effect`: measured effect, candidate effect or explicit unknown.
- `errors`: observed failures and the guarded probe failure taxonomy.
- `buildScope`: device, model, firmware build and full fingerprint.
- `safety`: read-only, unsupported write or production-enabled classification.
- `sampleConfiguration`: read-only guidance or production write guidance when policy permits.
- `evidence`: repository and external-source references.

The confidence vocabulary is `VERIFIED`, `PARTIALLY_VERIFIED`, `HYPOTHESIS` and `UNKNOWN`. Missing target evidence is never converted into a positive capability claim.

## Current production status

No MediaTek or Nothing vendor write is production-enabled for the observed build.

A key may be advertised, accepted by metadata code or matched to public MediaTek source without proving that:

1. an ordinary application may write it;
2. the value has the inferred target type or layout;
3. the value changes routing or image processing;
4. the operation is safe across session recreation, rollback and error recovery.

Write-capable keys therefore remain `UNSAFE_OR_UNSUPPORTED_WRITE`, expose no write sample and require fallback to public Camera2 without vendor writes.

Read-only characteristics and results expose introspection guidance. Consumers must preserve the returned typed value and must not assign enum names to opaque integers, arrays or byte blobs without separate target-build evidence.

## Ordering rules

- Characteristics are read after obtaining `CameraCharacteristics` for the selected camera ID.
- Session parameters are applied before session creation. A change requires recreation unless a target trace proves dynamic support.
- Request parameters are applied after request-template creation and before request build/submission.
- Physical-request parameters require a verified physical-camera path and remain unsupported for ordinary logical-camera use.
- Result keys are read only from the matching delivered result.

These are lifecycle placement rules. They do not prove that a key is writeable or effective.

## Promoting a key to production

A write sample may be published only after all of the following are committed for the exact firmware fingerprint:

- target-verified Java/native type and array or structure layout;
- target-verified accepted value or value domain;
- one-variable baseline, write and rollback probe;
- measured causal effect rather than metadata acceptance alone;
- bounded timeout, error and recovery behavior;
- explicit public Camera2 fallback;
- allowlisting in `currentProductionWriteKeys`.

Until then, the generated record remains useful as a versioned research and diagnostics reference, not as production configuration guidance.
