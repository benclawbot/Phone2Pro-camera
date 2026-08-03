# Experiment protocols and result records

Status: authoritative workflow for CAM-003.

The project separates **what must be tested** from **what was observed**:

```text
data/experiments/protocols.json   reusable, versioned protocols
data/experiments/results.json     executed result records
schemas/experiment-protocol.schema.json
schemas/experiment-result.schema.json
```

Run validation with:

```bash
python3 tools/experiments/validate-experiments.py
```

CI runs the same validator in addition to the repository-wide structured-data
checks.

## Protocol requirements

Every protocol must define:

- a stable protocol ID and integer version;
- objective and tightly bounded scope;
- scene, subject distance, background, lighting measurement, camera motion,
  subject motion, orientation, thermal, battery and network conditions;
- fresh-process or other explicit launch procedure;
- ordered capture sequence and repetitions;
- at least one positive control and one negative control;
- stabilization, delay, timeout, clock and required timestamp fields;
- mandatory raw artifacts, SHA-256, build matrix, package version, tool version,
  command, capture timing and camera metadata collection;
- pass and inconclusive criteria;
- the required negative-result template from `docs/EVIDENCE_MODEL.md`;
- prohibited generalizations and confidence-upgrade requirements;
- device, data-handling and stop-condition safety rules.

A positive control shows that the known path, scene, metadata association and
collection pipeline are functioning. A negative control exercises a materially
adjacent path or deliberately absent condition so a test result can be scoped
to one mechanism rather than generalized to the feature.

## Result requirements

Every result record must include:

- the exact protocol ID and version;
- one immutable `buildMatrixEntryId`;
- UTC experiment timing, clock source and timing precision;
- package name/version/version code;
- UID, SELinux, permissions and AppOps when observed, or explicit unknowns;
- device/application state and all tested parameters;
- tool names, versions and exact commands;
- outcomes for every positive and negative control in the protocol;
- ordered capture records and capture-level timestamps;
- raw artifact name, size, SHA-256, acquisition time, controlled-store path,
  normalized repository reference and transformations;
- observed behavior, verdict, scope limits, evidence class and confidence;
- the exact pass or fail criteria that were triggered.

A record marked `completed` must have exact timing, non-null capture timestamps,
and observed tool versions. Legacy records with missing timing or tool identity
must remain `partial`; they cannot be upgraded by filling invented values.

## Negative-result language

A negative observation must use one of these scoped forms:

```text
<mechanism> failed under <build, identity, state and parameters>
<behavior> was not observed under <build, identity, state and parameters>
```

Do not write:

```text
The feature is impossible.
The route does not exist.
No privileged mechanism can work.
```

unless the enforcing layer has been located or all materially distinct paths
have been exhausted. The validator rejects prohibited language inside the
formal `negativeResultStatement`.

Example:

```text
Exported widget focal preset routing failed under build
nothing-galaga-eea-android16-2606151653-f88325f3, stock package
com.nothing.camera 16.1.01.93.20, the exported widget launch state, and focal
parameters 15 mm, 24 mm and 50 mm.
```

This does not disprove internal Expert routing, a logical SAT route, a hidden
camera endpoint, privileged service behavior or a HAL route.

## Existing migrated result

`result-stock-route-isolation-galaga-20260803` combines the two existing,
independently hashed diagnostic artifacts needed to compare:

- internal Expert 0.6x / 1x / 2x behavior; and
- the exported widget 15 mm / 24 mm / 50 mm focal-launch path.

The positive controls pass because the internal Expert audit associates 1.64,
5.56 and 7.10 mm physical focal lengths with 15, 24 and 50 mm equivalents. The
negative control records that the exported widget parser received all three
values while associated outputs remained on the 5.56 mm / 24 mm-equivalent
route.

The result remains `partial`: the legacy artifacts preserve generation times,
but not exact launch/capture timestamps, diagnostic application version, UID,
SELinux, permissions or AppOps. Those gaps are listed in the result rather than
silently filled.

## Execute a new experiment

1. Copy an existing protocol only when its objective, controls and material
   conditions match. Otherwise create a new protocol ID or increment the
   version for a changed procedure.
2. Select or create the exact firmware/package matrix entry before collection.
3. Synchronize the device and host clocks; record the clock source and timezone.
4. Record scene, lighting, motion and device preconditions before launch.
5. Run every control and capture in the declared order. Do not skip a failed
   positive control and continue to a confident feature conclusion.
6. Preserve raw artifacts in the controlled artifact store, calculate SHA-256,
   and record acquisition and transformation history.
7. Write the result record before interpreting the mechanism broadly.
8. Run the experiment validator and repository test suite.

## Versioning rules

Increment a protocol version when any of the following changes materially:

- launch path or fresh-process policy;
- control definition;
- capture order, repetitions or parameters;
- scene, lighting or motion requirements;
- metadata or timing requirements;
- pass, inconclusive or confidence criteria.

Editorial clarifications that do not change execution may retain the version,
but the change must still be reviewed in Git history.

Never edit an old result to represent a rerun. Create a new result ID and link
the new raw artifacts. Corrections to transcription or provenance must remain
auditable in Git and must not change an artifact hash without a corresponding
new artifact identity.

## Validation invariants

The validator enforces:

- protocol/result JSON Schema conformance;
- unique IDs and contiguous step/capture sequences;
- disjoint positive and negative control IDs;
- exact protocol version references;
- exact build matrix references and package version consistency;
- one result for every declared control role;
- declared artifact use by controls and captures;
- exact artifact name, size, SHA-256 and build link against the diagnostic
  manifest;
- UTC timing order and artifact acquisition bounds;
- completed-result timing/tool requirements;
- scoped negative language and prohibited-generalization checks.

Schema conformance is necessary but not sufficient for scientific validity.
Scene equivalence, control quality, capture association and causal interpretation
still require review of the raw evidence.
