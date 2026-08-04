# Camera capability matrix

The authoritative machine-readable matrix is [`spec/camera-capability-matrix.v1.json`](../spec/camera-capability-matrix.v1.json).

## Row semantics

Each row records:

- the owning layer: hardware, public API, stock app, vendor API, firmware, security, or replacement app;
- reachability from an ordinary replacement application;
- the exact known configuration or limitation;
- repository or issue evidence;
- confidence;
- current replacement-app use;
- firmware/build scope;
- active issues for unresolved work.

`VERIFIED` describes what the committed evidence directly supports. `PARTIALLY_VERIFIED` identifies a bounded result with remaining mechanism or coverage gaps. `HYPOTHESIS` is an executable policy or target that still requires device measurement. `UNKNOWN` must not be enabled in production.

## Update rules

Run:

```sh
python3 tools/validate-capability-matrix.py
```

The validator rejects duplicate IDs, invalid vocabulary, missing build scopes, stale repository evidence paths, unresolved rows without issue links, and inaccessible capabilities marked as enabled.

New firmware must use a new or explicitly updated build scope. Vendor or auxiliary-route rows may move to production use only after an exact-build probe produces evidence and the corresponding active issue is resolved.
