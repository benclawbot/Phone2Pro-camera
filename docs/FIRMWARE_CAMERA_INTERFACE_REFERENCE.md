# Firmware camera interface reference

**Reference version:** `2026.08.04-1`  
**Target:** CMF Phone 2 Pro (`A001`, `Galaga`)  
**Observed build:** `2606151653`  
**Issue:** CAM-123 / #98

The machine-readable reference is:

```text
research/firmware/galaga-camera-interface-reference.v1.json
```

It consolidates the repository's build matrix, system-camera enforcement model,
privilege-boundary model, Galaga hardware map, stock Expert routing, typed
vendor-tag database and vendor API reference.

## Evidence boundary

The reference preserves four evidence classes:

- `VERIFIED`: directly observed or deterministically derived from committed target evidence.
- `PARTIALLY_VERIFIED`: supported by target behavior or official Galaga source, but not proven byte-identical to the observed firmware.
- `HYPOTHESIS`: a falsifiable candidate that is not enabled for replacement use.
- `UNKNOWN`: an opaque boundary with no production assumption.

The exact device fingerprint and stock-camera APK identity are bound through
`data/builds/version-matrix.json`. The official kernel source release
`Galaga-B4.1-260415-1710` predates the observed firmware build `2606151653`.
That mismatch is retained on every source-backed kernel interface.

## Interface coverage

The reference contains versioned records for:

| Layer | Included boundaries |
|---|---|
| Framework | `CameraManager`, CameraService enumeration, characteristics, status filtering and connect |
| Stock application | Expert route selection and package-identity dependency |
| Provider/HAL | Provider classification, provider interface and camera-device session boundary |
| Vendor metadata | Characteristics, session, request and result keys |
| Native libraries | Proprietary ELF/JNI/native routing and tuning boundary |
| Configuration | System/vendor XML, properties, overlays and init services |
| Kernel | Sensor V4L2, EEPROM, autofocus actuator, CSI, clocks, power and reset |
| Permissions | `SYSTEM_CAMERA`, package grants, roles, allowlists and AppOps boundary |
| SELinux | Application, cameraserver, provider/HAL, service and device policy boundary |
| ISP/tuning | Proprietary metadata buffers, tuning blobs, services and firmware |

Each record lists owner, process, interface type, method or symbol, direction,
identity requirements, build scope, confidence, evidence, version differences
and replacement-app use.

## Decisive current conclusions

- Public camera IDs `0` and `1` are ordinary-app routes on the tested build.
- IDs `2` through `5` are hidden from ordinary enumeration and rejected at
  characteristics as system-only devices.
- The current probe does not independently reach the CameraService connect gate
  for those IDs.
- Stock Expert routing directly selects camera IDs `2`, `0` and `3`.
- The exact stock package authorization recipe remains unresolved.
- Provider generation and instances, build-matched HAL methods, native symbol
  maps, firmware configuration, SELinux policy, and ISP/tuning contracts remain
  explicit opaque boundaries.
- No unknown provider, native, SELinux or ISP interface is enabled for production use.

## Firmware differences

Only one exact observed build is currently indexed. The reference therefore
retains two distinct contexts rather than pretending to provide a cross-build
behavioral diff:

1. exact observed firmware/package identity `2606151653`;
2. official Galaga source release `Galaga-B4.1-260415-1710`, marked as predating
   and not exactly matching the observed target.

A later firmware capture must create a new version-matrix entry and update each
affected interface record. Changes in source or package identity do not prove a
behavioral change without linked experiments.

## Validation

Run:

```bash
python3 tools/validate-firmware-camera-interface-reference.py
python3 -m unittest tests/test_validate_firmware_camera_interface_reference.py
```

The validator rejects missing interface ownership/process/method/identity
fields, category gaps, invalid confidence, hidden production assumptions,
missing evidence paths, lost build scope, and source-release mismatch drift.
