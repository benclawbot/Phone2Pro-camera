# Privacy, security and on-device data handling

Status: executable security contract for CAM-110.

The replacement camera processes user images locally. The production application has no network permission or network client dependency.

## Evidence classification

- **VERIFIED:** The production manifest requests only camera permission, disables application backup, forbids cleartext traffic, and passes automated no-network validation. Data lifetime, redaction and resource-release contracts are implemented and tested.
- **PARTIALLY VERIFIED:** Individual acquisition and processing implementations must adopt `SensitiveResourceLease` as they migrate from CameraX single-frame capture.
- **UNKNOWN:** Device-specific memory zeroization guarantees after Android/native buffer release remain outside application control.

## Permission baseline

The production manifest currently declares:

```text
android.permission.CAMERA
```

It does not declare `INTERNET`, network-state or location permissions. It also sets:

```text
android:allowBackup="false"
android:usesCleartextTraffic="false"
```

`tools/validate-camera-privacy.py` checks the real production manifest, source imports and application dependencies in CI. It rejects Internet/network permissions, cleartext or backup regressions, common Java/network imports and common HTTP client dependencies.

A future location feature requires a separate user-facing setting, permission request, privacy review and metadata policy. It must not be added as an implicit camera permission.

## Data lifetimes

`DataHandlingPolicy.privateByDefault()` provides one rule for every sensitive class:

| Data | Lifetime | Persistent by default | Diagnostic export |
|---|---|---:|---:|
| Preview frame | until consumed | no | no |
| Capture source frame | until capture completion | no | no |
| Processing intermediate | until processing completion/failure | no | no |
| Final image | until user deletion | yes | no |
| Location | never collected | no | no |
| Camera metadata | until capture completion | no | redacted opt-in only |
| Device identity | app session | no | no raw identity |
| Diagnostic event | app session/bundle completion | no | redacted opt-in only |
| Crash context | app session | no | redacted opt-in only |

`SensitiveResourceLease` gives buffers and metadata containers a single explicit owner and idempotent release. Access after release fails. Implementations remain responsible for closing Android `Image`, `ImageReader`, native allocations and temporary files behind the lease.

## Diagnostic consent

Diagnostics are opt-in:

- `OFF`: no diagnostic event is exported.
- `REDACTED_EVENTS`: event type, timestamps, route/backend category, error category and timings only.
- `REDACTED_METADATA`: may also include allowlisted build/configuration descriptors.

No consent level permits image or thumbnail bytes.

`DiagnosticRedactionPolicy` removes:

- image and thumbnail bytes;
- content URIs and file paths;
- location;
- device serials;
- user-entered text;
- arbitrary camera metadata values.

Event-only consent also omits the build fingerprint. A `RedactedDiagnosticEvent` rejects any field marked sensitive, preventing later code from bypassing the redactor accidentally.

## Crash diagnostics and logging

Crash and error reporting may contain only structured categories and non-sensitive state transitions. It must never serialize exception objects blindly because messages can include URIs, paths or vendor metadata values.

Recommended fields:

```text
event type
timestamp
backend ID
route ID
error category
stage
duration
redacted build descriptor (metadata consent only)
```

Logs must not contain pixels, base64 images, file contents, precise location, full content URIs, device serials or arbitrary request/result values.

## No-cloud guarantee

Every production processing stage declares `NetworkPolicy.DENIED` through `ProcessingSecurityContract`. The contract has no network-enabled state.

The on-device pipeline may use CPU, GPU, DSP, NPU or vendor hardware through local platform APIs, but it must not require:

- Internet connectivity;
- remote inference;
- cloud storage;
- telemetry upload;
- remote feature configuration needed for capture.

Offline operation is therefore a functional requirement, not merely a privacy preference.

## Temporary files

Temporary file use is disabled by default. A processing stage that requires temporary storage must declare it explicitly, use app-private storage, journal its lifetime, remove it on success/failure/startup recovery and never expose it through MediaStore.

The transactional storage contracts in `STORAGE_GALLERY_CONTRACTS.md` ensure only completed final assets become visible.

## Current integration boundary

The manifest and repository validation are active today. The lifetime and redaction models are ready for integration into acquisition, processing and diagnostics. The current CameraX JPEG path already keeps processing on device, but comprehensive buffer-lease instrumentation and structured crash diagnostics remain incremental implementation work rather than completed runtime claims.
