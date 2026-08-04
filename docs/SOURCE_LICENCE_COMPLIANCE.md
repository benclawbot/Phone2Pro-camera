# Source, licence and compliance register

**Register version:** 2026.08.04-1  
**Machine-readable source:** [`compliance/source-license-register.v1.json`](../compliance/source-license-register.v1.json)

This document records upstream licence declarations, repository decisions, redistribution handling, clean-room boundaries, and unresolved release gates. It is an engineering compliance record, not legal advice, a patent opinion, or a substitute for counsel.

## Dependency decisions

| ID | Component and version | Upstream-declared licence | Project use | Decision | Redistribution / attribution |
|---|---|---|---|---|---|
| `project-source` | Phone2Pro-camera repository history | MIT | Source and binary | Approved | Preserve repository copyright and permission notice. |
| `android-gradle-plugin` | `com.android.application` 9.3.0 | Apache-2.0 | Build only | Approved build-only | Not bundled by the project; retain upstream notices if redistributed. |
| `android-sdk-platform-36` | Android SDK platform API 36 | `LicenseRef-Android-SDK-Terms` | Build/platform API | Approved build-only; release review required | SDK packages are not redistributed by this repository. |
| `androidx-activity` | `androidx.activity:activity:1.13.0` | Apache-2.0 | Runtime | Approved runtime | Include Apache-2.0 and applicable notices in a distributed application notice bundle. |
| `androidx-camera-core` | `androidx.camera:camera-core:1.6.1` | Apache-2.0 | Runtime | Approved runtime | Same Apache/notice obligation. |
| `androidx-camera-camera2` | `androidx.camera:camera-camera2:1.6.1` | Apache-2.0 | Runtime | Approved runtime | Same Apache/notice obligation. |
| `androidx-camera-lifecycle` | `androidx.camera:camera-lifecycle:1.6.1` | Apache-2.0 | Runtime | Approved runtime | Same Apache/notice obligation. |
| `androidx-camera-view` | `androidx.camera:camera-view:1.6.1` | Apache-2.0 | Runtime | Approved runtime | Same Apache/notice obligation. |
| `junit4` | `junit:junit:4.13.2` | EPL-1.0 | Test only | Approved test-only | Not included in application runtime; preserve upstream licence if redistributed. |
| `hamcrest-core` | `org.hamcrest:hamcrest-core:1.3` via JUnit | BSD-3-Clause | Transitive test only | Approved test-only | Preserve BSD notice if redistributed. |
| `python-jsonschema` | `jsonschema`, currently unpinned | MIT | CI only | Approved CI-only with pinning gate | Not bundled; pin and resolve before a release baseline. |
| `pyyaml` | `PyYAML`, currently unpinned | MIT | CI only | Approved CI-only with pinning gate | Not bundled; pin and resolve before a release baseline. |
| `github-actions-checkout` | `actions/checkout@v4` | MIT | CI only | Approved CI-only | Not bundled; preserve licence if vendored. |
| `github-actions-setup-python` | `actions/setup-python@v5` | MIT | CI only | Approved CI-only | Not bundled; preserve licence if vendored. |

The upstream links and declaration locations are stored in the machine-readable register. The project records upstream declarations; it does not independently certify their legal interpretation.

## Direct-declaration coverage

The validator checks that every direct `implementation(...)` and `testImplementation(...)` line in `camera-app/app/build.gradle.kts`, the Android application plugin declaration, SDK 36 compile/target declarations, validation-workflow actions, and validation-workflow pip packages are represented by a register entry.

The diagnostics application currently adds no external runtime libraries. Transitive dependencies beyond the recorded JUnit/Hamcrest relationship must be generated from the resolved Gradle and Python graphs before a release. This is a release gate, not an assertion that no other transitive software exists.

## Proprietary and private artifact handling

| ID | Artifact class | Decision | Redistribution rule |
|---|---|---|---|
| `private-diagnostic-json` | User-controlled diagnostic output | Reference by hash, metadata, and derived findings only | Do not redistribute without explicit owner permission. |
| `user-camera-images` | User photographs | Reference metadata only unless permission is recorded | Do not redistribute without explicit owner permission. |
| `stock-camera-apk-and-splits` | Proprietary stock application binaries | Reference-only interoperability research | Do not commit or redistribute. |
| `framework-vendor-firmware-artifacts` | Mixed open-source, proprietary, and unknown system binaries | Record per-artifact hash, path, build ID, source, and licence before use | Do not redistribute unless rights are verified. |
| `papers-and-public-datasets` | Research papers, datasets, and companion code | Citation-only by default | Reuse or redistribution requires a recorded source-specific licence and attribution decision. |

The canonical missing-artifact and handling record is [`data/artifacts/diagnostic-manifest.yaml`](../data/artifacts/diagnostic-manifest.yaml). A hash or observation does not grant redistribution rights.

## Clean-room boundary

### Learned behavior that may inform independent implementation

- Public Camera2/CameraX behavior, documented API behavior, stock user-interface behavior, output metadata, timing, and failure states may be observed and recorded.
- Black-box compatibility findings may be converted into independently written interface requirements and tests.
- Replacement implementations may use public specifications, permissively licensed sources, and independently designed algorithms with recorded provenance.

### Copying that is prohibited by project policy

- Do not copy decompiled stock-camera source, resources, proprietary configuration, or native implementation into replacement code.
- Do not commit vendor firmware, APK bytecode, extracted proprietary symbols, tuning assets, or user images to the public repository.
- Do not convert access to a private diagnostic or binary into an assumption that it may be redistributed.
- Do not paste constants, tables, names, or code whose provenance cannot be explained by public documentation, an approved dependency, or independent derivation.

### Required separation records

- Research evidence records identify source, build, hash, handling restrictions, and confidence.
- Implementation commits cite behavioral requirements or public specifications rather than copied proprietary code.
- A contributor exposed to restricted source discloses the exposure before implementing the corresponding component.
- Reviewers stop and investigate suspicious similarity before merge.

The replacement-camera SDK guide is intentionally written in terms of portable contracts, observed behavior, and explicit unknowns. It does not reproduce stock implementation code.

## Patent-sensitive areas

The following areas remain **not cleared** for release-level patent conclusions:

- multi-frame denoise, HDR, super-resolution, fusion, and other computational photography algorithms;
- image/video codecs or containers beyond use of platform-provided APIs;
- vendor algorithms, tuning, and proprietary request semantics.

Implementation work may continue as research or portable contracts, but an enabled release path requires a separate patent/algorithm review. The register does not claim that a technique is patented, unpatented, licensed, or infringing.

## Release gates

Before a distributable release:

1. generate and review the resolved runtime and test dependency graph, including transitives;
2. pin `jsonschema` and `PyYAML` and record the resolved Python graph;
3. produce application third-party notices from the resolved release graph;
4. verify that no private/proprietary artifacts are present in source, build inputs, or the APK;
5. review enabled computational and codec functionality for patent/licence concerns;
6. update this register for every dependency, artifact, paper, dataset, build tool, licence, or reuse-decision change.

## Contributor checklist

A new dependency or external source cannot merge until its register entry contains:

- stable component identity and version or commit;
- upstream/source location;
- declared licence or an explicit `LicenseRef-*`/unknown status;
- use scope and approve/reject/review decision;
- redistribution and attribution handling;
- declaration/evidence location;
- clean-room and patent notes when applicable.

Run:

```sh
python3 tools/validate-compliance-register.py
```

The validator checks direct-declaration coverage, register vocabulary, evidence paths, unpinned-package review gates, private/proprietary non-redistribution, clean-room completeness, patent status, release gates, and this document’s coverage of every dependency/artifact ID.
