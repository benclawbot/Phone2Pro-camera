# Evidence and Confidence Model

## Purpose

This project combines device experiments, decompiled applications, native binaries, firmware artifacts, public source code, documentation and community reports. The evidence model prevents a plausible interpretation from silently becoming a platform fact.

## Evidence classes

| Class | Meaning | Typical examples |
|---|---|---|
| `device-observed` | Reproducible result collected from the target device | CameraCharacteristics dump, EXIF, logcat, trace, open-camera error |
| `source-confirmed` | Behaviour established in relevant source or decompiled code | AOSP implementation, Nothing Camera call site, kernel source |
| `documentation-confirmed` | Behaviour specified by authoritative documentation | Android camera metadata or HAL contract |
| `binary-confirmed` | Behaviour established from disassembly, symbols or native call graph | JNI registration, vendor library branch, Binder transaction |
| `community-corroborated` | Independent reports agree with the observation | GCam reports of IDs 0 and 1 only |
| `inferred` | Best explanation supported by multiple observations but not yet traced | A vendor key likely controls a feature pipeline |
| `unverified` | Candidate claim or lead awaiting evidence | Guessed enum value or permission |

## Confidence levels

- **C0 — Unknown:** no useful evidence.
- **C1 — Lead:** one weak or indirect source.
- **C2 — Supported:** one direct observation or multiple independent indirect sources.
- **C3 — Strong:** reproducible observation plus implementation or authoritative documentation.
- **C4 — Confirmed:** traced end-to-end or reproduced with controlled positive and negative tests.

## Required fields for every capability

- Stable capability ID.
- Human-readable name.
- Device and firmware build.
- Owning layer: app, framework, service, HAL, vendor pipeline, kernel or hardware.
- Interface: Camera2 key, session parameter, intent, Binder method, JNI method, native symbol, sysfs/ioctl or other.
- Direction: characteristic, request, result, session, callback or service call.
- Type and valid values.
- Dependencies and mutually exclusive settings.
- Required permissions, identity, UID, signature, SELinux domain and process context.
- Test procedure and raw artifacts.
- Observed behaviour and exact error/fallback.
- Evidence class and confidence.
- Replacement-app usability: public, hidden-but-callable, privileged, root-only, firmware-only, unsupported or unknown.
- Safety and stability notes.

## Negative-result rule

A failure must be recorded as:

```text
<mechanism> failed under <build, identity, state and parameters>
```

It must not be generalized to:

```text
<feature> is impossible
```

without locating the enforcing layer or exhausting all materially distinct call paths.

Examples:

- Widget focal preset ignored → external widget route not honoured under that build.
- Camera ID 3 cannot be opened through public CameraManager → direct public open rejected.
- Zoom ratio remains on camera 0 → public rear route does not switch sensors under the tested session.

None of these alone disproves an internal SAT route, a hidden logical device, a vendor session configuration or a privileged service.

## Artifact handling

Every raw artifact should record:

- SHA-256 hash;
- acquisition time and timezone;
- device build fingerprint;
- package version;
- command/tool version;
- collection procedure;
- transformations applied;
- original and normalized paths.

Derived documentation links back to the artifact and never replaces it.

## Source quality order

For implementation claims, prefer:

1. Target-device observation plus traced target implementation.
2. Target firmware/APK/native binary.
3. Matching official source release.
4. Current AOSP source and official Android documentation.
5. MediaTek public source from a related platform.
6. Reputable open-source implementation.
7. Community reports.

Lower-priority evidence remains useful for discovery but cannot override direct target-device evidence.
