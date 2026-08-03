# Nothing Camera Static Camera-open Path

Status: static bytecode finding for CAM-024, CAM-026 and CAM-043.

Analyzed artifact:

```text
Camera-16.1.01.93.20.apk
SHA-256 f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea
```

## Evidence classification

### VERIFIED

The repository's decompiler-independent DEX analyzer can parse all seven DEX
files in the analyzed APK and recover exact method descriptors, referenced
strings and invoke targets without reconstructing proprietary source code.

### PARTIALLY VERIFIED

Static bytecode establishes an application-owned path that accepts an integer
camera ID and eventually invokes Android `CameraManager.openCamera` with its
string representation:

```text
SettingContext.getCameraId()
  -> ModuleContext.openCameraAsync(int) / resumeCameraAsync(int)
  -> CameraContext.openCamera(int, ConditionVariable)
  -> CameraContext$3.execute(Object[])
  -> String.valueOf(int)
  -> CameraManager.openCamera(String, StateCallback, Handler)
```

The integer is therefore selected before the framework open call and is not
intrinsically fixed to public camera ID `0` inside the final dispatch method.
This proves the presence of an explicit camera-endpoint-selection mechanism in
the application bytecode. A subsequent Galaga-specific extraction now establishes the configured manual
values: ID `2` for `[0.6,1)`, ID `0` for `[1,2)`, and ID `3` for `[2,10]`.
Static analysis alone still does not prove that each branch executed in a
particular runtime capture.

The APK also contains distinct static paths for:

- creating `SessionConfiguration` and applying `setSessionParameters`;
- assigning `OutputConfiguration.setPhysicalCameraId` in dual-output capture
  and preview components;
- enumerating camera IDs and maintaining separate rear-camera and rear-logical-
  camera collections;
- selecting first-back, wide-angle, tele and SAT camera IDs from device
  information and configuration state;
- updating `pref_camera_id_key` and recreating a session in response to
  lens/mode state changes.

These paths show that direct endpoint selection, vendor session parameters and
physical-output selection coexist in the stock application. They do not yet
establish which mechanism is causally responsible for each Expert optical
route.

### UNKNOWN

The following remain unresolved until fresh-process runtime traces are
captured for 0.6×, 1× and 2× separately:

- whether the configured integers `2`, `0` and `3` are observed at every
  corresponding runtime open on the tested firmware;
- whether route-specific session parameters are required in addition to the
  selected camera ID;
- whether physical-output IDs are part of Expert still capture or only
  specialized dual-output modes;
- whether any native/Binder stage changes the active sensor after the
  framework endpoint is opened.

## Revised hypothesis ranking

1. **Direct camera endpoint selection — VERIFIED static configuration /
   PARTIALLY VERIFIED runtime behaviour.** The Galaga manual route table maps
   0.6× to ID `2`, 1× to ID `0`, and 2× through 10× to ID `3`, and the selected
   integer reaches the application-owned Camera2 open path.
2. **System logical SAT plus vendor configuration — HYPOTHESIS for other
   modes.** SAT and physical-output paths coexist in the APK, but ID `4` is not
   the endpoint in the recovered Galaga manual table.
3. **Direct endpoint plus MediaTek session parameters — HYPOTHESIS.** Session
   parameters may supplement direct opens, but they are not the primary manual
   lens selector represented by this table.
4. **Entirely hidden HAL routing after a fixed public open — weakened
   HYPOTHESIS.** A later HAL stage may still exist, but a fixed public open alone
   cannot explain the recovered endpoint table.

See [`GALAGA_EXPERT_DIRECT_ROUTE.md`](GALAGA_EXPERT_DIRECT_ROUTE.md) and the
reproducible `tools/apk/extract-galaga-manual-route.py` report.

## Next decisive experiment

Instrument the final application dispatch method and session construction in a
fresh stock process. Record, for each isolated Expert route:

```text
`nothing-camera-id-set` and helper return values
`nothing-module-open-request` camera ID
`nothing-camera-context-open` camera ID
`nothing-open-dispatch` camera ID
framework `open-camera` camera ID
SessionConfiguration session-parameter keys and values
OutputConfiguration physical camera ID
capture result focal length and active physical ID/vendor status
```

The experiment must use a fresh process per route and verify the resulting
image by focal length, geometry and field of view. A static call site or a
single observed key is not sufficient to declare routing reproduced.
