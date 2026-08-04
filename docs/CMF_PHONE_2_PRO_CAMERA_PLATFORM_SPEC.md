# CMF Phone 2 Pro camera platform specification

**Specification version:** 0.1.0  
**Publication date:** 2026-08-04  
**Status:** Living specification  
**Device:** CMF Phone 2 Pro, model A001, codename `galaga`, MT6878  
**Primary observed build:** `Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys`

The machine-readable claim and decision register is [`spec/platform-spec-manifest.v0.1.json`](../spec/platform-spec-manifest.v0.1.json). This document consolidates completed workstreams and explicitly bounds incomplete work. It is authoritative for what the repository currently claims; it is not a substitute for raw private diagnostics, missing firmware artifacts, or unfinished device tests.

## Confidence and implementation vocabulary

- **VERIFIED:** directly supported by committed code, normalized evidence, or an identified diagnostic record.
- **PARTIALLY_VERIFIED:** the observation or contract is bounded, but mechanism, coverage, integration, or device validation remains incomplete.
- **HYPOTHESIS:** an executable target or policy awaiting physical measurement.
- **UNKNOWN:** evidence is absent or insufficient; no value or effect is inferred.
- **ENABLED:** eligible for current production use within the named build scope.
- **ENABLED_WITH_FALLBACK:** usable only with the documented fail-closed fallback.
- **DISABLED:** not production-usable.
- **DIAGNOSTIC_ONLY / DOCUMENTATION_ONLY:** retained for investigation or reference, not product behavior.

Every claim below uses the same ID as the manifest. Claims are scoped to the recorded build unless stated otherwise.

## Hardware

### C-HW-001 — Main optical route

**Claim:** The observed rear main route has 5.56 mm physical focal length, 24 mm equivalent focal length, and a verified 4080×3072 output record.  
**Confidence:** VERIFIED. **Implementation:** ENABLED.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [CAM-101](https://github.com/benclawbot/Phone2Pro-camera/issues/84).  
**Limit:** Aperture, calibration consistency, and complete color/stabilization metadata remain under [CAM-018](https://github.com/benclawbot/Phone2Pro-camera/issues/25).

### C-HW-002 — Ultrawide optical observation

**Claim:** The stock camera produced a 0.6× output with 1.64 mm physical focal length, 15 mm equivalent focal length, and 3264×2448 geometry. The ordinary-app endpoint, active physical sensor, and route mechanism are unresolved.  
**Confidence:** PARTIALLY_VERIFIED. **Implementation:** DISABLED.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [routing specification](../spec/camera-routing-spec.v1.json).  
**Unknowns:** [CAM-026](https://github.com/benclawbot/Phone2Pro-camera/issues/32), [CAM-042](https://github.com/benclawbot/Phone2Pro-camera/issues/39), [CAM-047](https://github.com/benclawbot/Phone2Pro-camera/issues/44), [CAM-069](https://github.com/benclawbot/Phone2Pro-camera/issues/64), [CAM-070](https://github.com/benclawbot/Phone2Pro-camera/issues/65), and caller-identity issues.

### C-HW-003 — Telephoto optical observation

**Claim:** The stock camera produced a 2× output with 7.1 mm physical focal length, 50 mm equivalent focal length, and 4096×3072 geometry. The ordinary-app endpoint, active physical sensor, and route mechanism are unresolved.  
**Confidence:** PARTIALLY_VERIFIED. **Implementation:** DISABLED.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [routing specification](../spec/camera-routing-spec.v1.json).  
**Unknowns:** The same route, scenario, multicamera, and caller-identity issues as C-HW-002.

## Public API

### C-API-001 — Public camera IDs

**Claim:** Ordinary-app Camera2 enumeration exposes rear ID `0` and front ID `1` on the observed build.  
**Confidence:** VERIFIED. **Implementation:** ENABLED.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [CAM-010](https://github.com/benclawbot/Phone2Pro-camera/issues/17).

### C-API-002 — Candidate IDs 2–5

**Claim:** Candidate IDs `2`, `3`, `4`, and `5` were not openable by the ordinary diagnostics application. They remain system, privileged, vendor, or otherwise filtered candidates; their ownership is not inferred.  
**Confidence:** PARTIALLY_VERIFIED. **Implementation:** DISABLED.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [CAM-010](https://github.com/benclawbot/Phone2Pro-camera/issues/17).  
**Unknowns:** Provider classification, framework filtering, SELinux, service identity, and stock package dependencies.

### C-API-003 — Stream combinations

**Claim:** The complete high-resolution, reprocessing, video, constrained-high-speed, and mandatory stream-combination matrix is not verified.  
**Confidence:** UNKNOWN. **Implementation:** DIAGNOSTIC_ONLY.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [CAM-011](https://github.com/benclawbot/Phone2Pro-camera/issues/18).  
**Required work:** [CAM-014](https://github.com/benclawbot/Phone2Pro-camera/issues/21) and [CAM-017](https://github.com/benclawbot/Phone2Pro-camera/issues/24).

### Public binder boundary

The production architecture permits CameraX for verified public configurations and direct Camera2 for explicit public stream/request control. CameraX plans cannot claim arbitrary session parameters, physical outputs, reprocessing inputs, or vendor keys. See [capture session and request engine](architecture/CAPTURE_SESSION_REQUEST_ENGINE.md).

## Stock APK

### C-APK-001 — Expert route observations

**Claim:** The stock Expert interface produced distinct 0.6×, 1×, and 2× output records. The controller-to-camera transitions for auxiliary routes remain bounded at an opaque stock/system/vendor boundary.  
**Confidence:** PARTIALLY_VERIFIED. **Implementation:** DIAGNOSTIC_ONLY.  
**Evidence:** [diagnostic manifest](../data/artifacts/diagnostic-manifest.yaml), [routing specification](../spec/camera-routing-spec.v1.json).  
**Unknowns:** Full UI call chains, session construction, Binder/native transitions, and synchronized route traces.

### C-APK-002 — External widget handoff

**Claim:** External widget focal launches are stock-camera handoffs. The committed audit remained on the 5.56 mm or 24 mm-equivalent route and does not prove ordinary-app auxiliary access.  
**Confidence:** VERIFIED. **Implementation:** DIAGNOSTIC_ONLY.  
**Evidence:** [diagnostic manifest](../data/artifacts/diagnostic-manifest.yaml), [routing specification](../spec/camera-routing-spec.v1.json).  
**Limit:** Internal Expert state creation remains separate from the exported widget path.

### C-APK-003 — Package provenance gap

**Claim:** Complete base/split package hashes, signature, install path, runtime package dump, and decompilation provenance are not present in the repository.  
**Confidence:** UNKNOWN. **Implementation:** DOCUMENTATION_ONLY.  
**Evidence:** [diagnostic manifest missing-artifact register](../data/artifacts/diagnostic-manifest.yaml).  
**Required work:** CAM-020 through CAM-030.

## Firmware

### C-FW-001 — Observed build identity

**Claim:** The canonical observed build is the Galaga EEA Android 16 fingerprint shown in this document’s header.  
**Confidence:** VERIFIED. **Implementation:** DOCUMENTATION_ONLY.  
**Evidence:** [diagnostic manifest](../data/artifacts/diagnostic-manifest.yaml).

### C-FW-002 — Missing firmware interface evidence

**Claim:** Build-matched framework camera artifacts, vendor camera libraries, and firmware partitions are absent. Provider/HAL versions, native interfaces, configuration, policy, and complete security boundaries therefore remain incomplete.  
**Confidence:** UNKNOWN. **Implementation:** DOCUMENTATION_ONLY.  
**Evidence:** [diagnostic manifest missing-artifact register](../data/artifacts/diagnostic-manifest.yaml).  
**Required work:** CAM-050 through CAM-059, CAM-082, CAM-093, and CAM-123.

No firmware-level statement in this version should be interpreted as proof of a specific provider implementation, transaction, native symbol, sensor scenario, or enforcement layer unless separately cited.

## Vendor API

### C-VND-001 — Vendor inventory mechanism

**Claim:** `VendorTagDiagnostics` enumerates characteristic, request, result, session, physical-request, and default-template entries. Runtime reflection is used when permitted; unavailable types remain unknown.  
**Confidence:** VERIFIED. **Implementation:** DIAGNOSTIC_ONLY.  
**Evidence:** [VendorTagDiagnostics.java](../diagnostics/app/src/main/java/com/phone2pro/diagnostics/VendorTagDiagnostics.java), [diagnostic manifest](../data/artifacts/diagnostic-manifest.yaml).  
**Limit:** The raw static hardware/vendor report is private and not redistributed; the complete derived typed database is still required by [CAM-060](https://github.com/benclawbot/Phone2Pro-camera/issues/55).

### C-VND-002 — Production vendor policy

**Claim:** No MediaTek or Nothing vendor key is production-enabled. An exact build allowlist, safe isolated probe, effective result verification, correct setting scope, and public fallback are mandatory before use.  
**Confidence:** VERIFIED. **Implementation:** ENABLED as a deny-by-default policy, not as an enabled vendor feature.  
**Evidence:** [vendor extension adapter](architecture/VENDOR_EXTENSION_ADAPTER.md), [engineering guide](REPLACEMENT_CAMERA_SDK.md).  
**Unknowns:** CAM-060 through CAM-071.

The tested vendor API reference requested by CAM-122 remains incomplete. Unknown values, enums, structures, ordering, and effects are not guessed in this specification.

## Routing

### C-RT-001 — Production rear route

**Claim:** The verified ordinary-app rear route is public camera ID `0` mapped to the main optical route.  
**Confidence:** VERIFIED. **Implementation:** ENABLED.  
**Evidence:** [routing specification](../spec/camera-routing-spec.v1.json), [backend contracts](architecture/CAMERA_BACKEND_CONTRACTS.md).

### C-RT-002 — Auxiliary route boundary

**Claim:** Stock ultrawide and telephoto routes are bounded at unresolved stock, system, vendor, logical, or sensor-scenario transitions. They are unavailable to production replacement routing.  
**Confidence:** PARTIALLY_VERIFIED. **Implementation:** DISABLED.  
**Evidence:** [routing specification](../spec/camera-routing-spec.v1.json).  
**Fallback:** Return unavailable, offer an explicit stock-camera handoff, or offer clearly labelled main-camera digital framing.

### C-RT-003 — Digital truthfulness

**Claim:** Public zoom/crop on ID `0` is labelled digital unless active-sensor evidence proves an optical or in-sensor transition.  
**Confidence:** VERIFIED as a product policy; exact crop behavior remains unmeasured. **Implementation:** ENABLED_WITH_FALLBACK.  
**Evidence:** [routing specification](../spec/camera-routing-spec.v1.json), [UI state architecture](architecture/UI_STATE_ARCHITECTURE.md).  
**Unknown:** [CAM-013](https://github.com/benclawbot/Phone2Pro-camera/issues/20).

## Security

### C-SEC-001 — No-network production policy

**Claim:** The replacement app requests camera permission only, disables backup and cleartext traffic, and rejects network permissions, network imports, and common HTTP dependencies through repository validation.  
**Confidence:** VERIFIED. **Implementation:** ENABLED.  
**Evidence:** [privacy and security architecture](architecture/PRIVACY_SECURITY.md), [privacy validator](../tools/validate-camera-privacy.py), [Android manifest](../camera-app/app/src/main/AndroidManifest.xml).

### C-SEC-002 — Diagnostic privacy

**Claim:** Diagnostic exports are opt-in and exclude image pixels, thumbnails, paths, content URIs, location, serials, user text, and arbitrary metadata values by default.  
**Confidence:** VERIFIED. **Implementation:** ENABLED.  
**Evidence:** [privacy and security architecture](architecture/PRIVACY_SECURITY.md), [diagnostics architecture](architecture/DIAGNOSTICS_CAPABILITY_REPORTING.md).

Image buffers and sensitive metadata have explicit lifetimes. Optional location/device/processing metadata is omitted without affirmative policy.

## Processing

### C-PROC-001 — Portable processing contracts

**Claim:** The repository defines portable, replaceable contracts for burst metadata, clock calibration, frame scoring, reference selection, local alignment, stage ordering, color/transfer transitions, artefact detection, metadata propagation, encoding, and conservative fallback.  
**Confidence:** VERIFIED at the contract/test level. **Implementation:** DISABLED as a complete device pipeline.  
**Evidence:** [burst/alignment contracts](architecture/BURST_ALIGNMENT_CONTRACTS.md), [rendering pipeline](architecture/IMAGE_RENDERING_PIPELINE.md).

### C-PROC-002 — Unverified device performance and quality

**Claim:** Algorithm choice, image quality, motion behavior, memory/latency targets, and stock-versus-replacement performance are not physically benchmarked to completion.  
**Confidence:** UNKNOWN. **Implementation:** DISABLED.  
**Evidence:** [resource budgets](architecture/RESOURCE_BUDGETS.md), [CAM-126](https://github.com/benclawbot/Phone2Pro-camera/issues/101).  
**Required work:** CAM-015, CAM-097, and CAM-126.

The mandatory processing fallback is reference-first: reduce stages, mask unreliable regions, or return the selected reference frame instead of forcing artificial detail.

## Replacement app

### C-APP-001 — Validated architecture surface

**Claim:** The repository contains validated portable contracts for backend lifecycle, route truthfulness, session/request planning, capture modes, UI state, transactional storage, vendor isolation, privacy, diagnostics, and resource policy.  
**Confidence:** VERIFIED. **Implementation:** ENABLED_WITH_FALLBACK.  
**Evidence:** [replacement camera engineering guide](REPLACEMENT_CAMERA_SDK.md), [guide manifest](../spec/replacement-camera-sdk-guide.v1.json).

### C-APP-002 — Current integration boundary

**Claim:** The application can use the verified public main route. Auxiliary routing, complete computational integration, measured budgets, complete stream coverage, and end-to-end benchmark validation remain incomplete.  
**Confidence:** PARTIALLY_VERIFIED. **Implementation:** ENABLED_WITH_FALLBACK.  
**Evidence:** [capability matrix](../spec/camera-capability-matrix.v1.json), [engineering guide](REPLACEMENT_CAMERA_SDK.md).  
**Unknowns:** CAM-011, CAM-015, CAM-026, CAM-047, CAM-062, CAM-097, and CAM-126.

The implementation baseline is deliberately conservative: public ID `0`, explicit unsupported states, bounded recovery, private metadata, hidden pending assets, on-device processing, and no enabled vendor controls.

## Decision register

| ID | Adopted decision | Evidence basis | Revisit trigger |
|---|---|---|---|
| D-001 | Use public rear ID `0` as the production baseline endpoint. | C-API-001, C-RT-001 | A new build changes public enumeration or open behavior. |
| D-002 | Never represent main-camera digital crop as ultrawide or telephoto optical output. | C-HW-002, C-HW-003, C-RT-003 | Reproduced active-sensor evidence establishes a different route. |
| D-003 | Keep every vendor feature disabled until exact-build effective probing and public fallback exist. | C-VND-001, C-VND-002 | CAM-060/061/062 evidence reaches verified-supported status. |
| D-004 | Keep processing on-device and deny network capability. | C-SEC-001, C-SEC-002 | Requires an explicit specification revision; no current revisit issue. |
| D-005 | Use private-by-default metadata and omit optional sensitive fields without consent. | C-SEC-002, C-APP-001 | Requires an explicit privacy-policy revision. |
| D-006 | Bound request retries, session recreation, and camera reopen; never loop permanent failures. | C-APP-001 | Device benchmarks justify different bounds. |
| D-007 | Prefer reference-frame/reduced processing over forced multi-frame artefacts. | C-PROC-001, C-PROC-002 | Validated algorithms and benchmarks demonstrate safe alternatives. |
| D-008 | Treat every untested firmware build as incompatible with existing vendor/auxiliary allowlists. | C-FW-001, C-FW-002, C-VND-002 | Diagnostics are rerun on the new fingerprint. |
| D-009 | Reference private diagnostics and user images by metadata/hashes without redistributing raw artifacts. | C-APK-001, C-VND-001 | Artifact owner grants permission and compliance register permits distribution. |

## Known unknowns

The principal unresolved areas are:

- complete public stream combinations, RAW/reprocessing, video, high-speed, and concurrency;
- manual 3A, zoom/crop, calibration, color, stabilization, and burst benchmarks;
- stock package provenance, code graphs, mode pipelines, request builders, and native dependencies;
- synchronized stock Java/Binder/native/output traces;
- provider/HAL versions, framework modifications, native libraries, configuration, kernel interfaces, permissions, and SELinux rules;
- complete typed vendor database, enum/structure meanings, safe probes, and feature-family effects;
- auxiliary route reproduction for an ordinary application;
- computational algorithm selection, device quality, latency, memory, battery, and thermal benchmarks;
- complete stock behavior, vendor API, and firmware interface references.

These unknowns are active issues, not implicit permission to infer values.

## Versioning and update policy

Create a new specification version, or explicitly update this version’s manifest and changelog, when any of the following occurs:

1. a new Nothing OS build fingerprint is tested;
2. the stock camera package version, splits, signature, or install path changes;
3. a vendor or auxiliary route changes confidence or reachability;
4. provider, HAL, framework, policy, native, kernel, or package artifacts are acquired;
5. physical benchmarks replace hypothetical processing/resource targets;
6. a material claim changes evidence, confidence, build scope, or implementation use.

Any update must modify both this document and `spec/platform-spec-manifest.v0.1.json`, preserve previous versions in history, and pass `python3 tools/validate-platform-spec.py`.
