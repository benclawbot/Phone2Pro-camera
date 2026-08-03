# Execution Plan

## Status

The repository structure, evidence model, capability schema, baseline device map, external-source index and AOSP boundary analysis are in place. The full research and implementation backlog is represented by GitHub issues #2–#102.

Work has started on:

- CAM-005 — normalize the current diagnostic baseline.
- CAM-090 — build the external-source index.
- CAM-091 — cross-reference target behaviour with AOSP camera contracts.
- CAM-092 — resolve official Galaga kernel sources.

## Dependency order

```text
Artifacts/build matrix
        ↓
Public capability normalization ───────────────┐
        ↓                                      │
APK acquisition → static call graph            │
        ↓                                      │
Expert/SAT/session call-site targets            │
        ↓                                      │
Dynamic Java/Camera2/Binder/native traces       │
        ↓                                      │
Firmware/provider/HAL/security boundary         │
        ↓                                      │
Minimal routing and vendor-feature reproducers  │
        └───────────────────────────────────────┘
                          ↓
             Canonical capability database
                          ↓
             Replacement-camera architecture
                          ↓
                 Production implementation
```

External AOSP, MediaTek, Nothing OSS, firmware, community, open-source camera and academic research runs in parallel, but target-device claims remain anchored to direct evidence.

## Sprint 1 — Establish immutable evidence

Primary issues: CAM-001 through CAM-005, CAM-010, CAM-020, CAM-090 through CAM-093.

Deliverables:

1. Artifact manifest with hashes and acquisition context.
2. Firmware/package/diagnostic build matrix.
3. Normalized capability entries for the uploaded diagnostic.
4. Exact Nothing Camera APK/split/version/signature inventory.
5. Matching or nearest available Galaga firmware package index.
6. AOSP Android 16 source revisions pinned for framework comparison.

Exit condition:

- Every existing finding can be traced to an artifact and build.
- Required missing artifacts are listed with acquisition instructions.

## Sprint 2 — Recover the Expert-mode route statically

Primary issues: CAM-021 through CAM-030, CAM-060 and CAM-061.

Deliverables:

1. Manifest/component/permission map.
2. Package and call graphs.
3. Galaga feature flags and routing tables.
4. Complete lens-button call chains until Camera2, Binder or JNI boundaries.
5. Stock call sites for every routing-relevant vendor key.
6. Native method and library dependency map.

Exit condition:

- We know exactly which methods to instrument for 0.6×, 1× and 2×.
- Static ambiguities are converted into explicit dynamic trace probes.

## Sprint 3 — Differential runtime tracing

Primary issues: CAM-040 through CAM-047.

Deliverables:

1. Synchronized trace harness.
2. Three controlled fresh-launch Expert traces.
3. CameraDevice/session/request snapshots.
4. Binder and CameraService transaction map.
5. JNI/native routing traces where required.
6. Ranked minimal reproducer candidates.

Exit condition:

- The first differing causal configuration for each optical route is identified or the unresolved boundary is below the currently observable layer.

## Sprint 4 — Firmware and privilege boundary

Primary issues: CAM-050 through CAM-059 and CAM-080 through CAM-086.

Deliverables:

1. Provider/HAL and service inventory.
2. Native symbol/call graph.
3. Framework diff against AOSP.
4. System-camera/hidden-ID filtering path.
5. Permission, signature, UID, Binder and SELinux map.
6. Exact auxiliary-lens enforcement diagram.

Exit condition:

- A failure to reproduce a route can be assigned to an exact enforcing layer.
- If reproducible, the smallest required configuration and compatibility limits are known.

## Sprint 5 — Vendor capability characterization

Primary issues: CAM-062 through CAM-071.

Deliverables:

- Guarded probe harness.
- Typed and tested MFNR/AIS, HDR, 3A, ZSL, stabilization, in-sensor zoom, seamless, multicam and ISP records.
- Production allowlist and safe fallback rules.

Exit condition:

- Each relevant vendor key is usable, conditionally usable, read-only, privileged, ineffective, unsafe or explicitly unknown.

## Sprint 6 — Replacement camera specification

Primary issues: CAM-100 through CAM-111.

Deliverables:

- Runtime capability negotiation.
- Camera and lens backend interfaces.
- Session/capture engine.
- Quick/Auto/Max Detail specifications.
- Computational pipeline contracts.
- UI, storage, privacy, diagnostics and resource budgets.

Implementation can begin before every vendor issue is closed because the architecture isolates optional vendor and auxiliary-lens backends.

## Canonical release outputs

Primary issues: CAM-120 through CAM-127.

- Camera capability matrix.
- Routing specification.
- Vendor API reference.
- Firmware interface reference.
- Stock-camera behaviour reference.
- Replacement-camera SDK guide.
- Benchmark suite and results.
- Versioned CMF Phone 2 Pro Camera Platform Specification.

## Immediate artifact request queue

The following artifacts unlock the highest-value next steps:

1. Nothing Camera base and split APKs matching version `16.1.01.93.20`.
2. `dumpsys package com.nothing.camera` and package path/signature output.
3. Matching framework and vendor partitions or OTA package for the tested build.
4. Camera provider/service manifests and camera-related native libraries.
5. Existing decompilation project or exported jadx sources, if already available.
6. Prior diagnostic JSON files for static, night, daylight, Expert and direct-ID audits.

Raw proprietary or personal artifacts should not be committed publicly. Store hashes, metadata and derived clean-room findings in the repository; retain raw files in a controlled local evidence store.
