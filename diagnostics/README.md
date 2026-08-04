# CMF Phone 2 Pro camera specification app

This Android application builds one evidence-backed JSON specification of the camera platform exposed to an ordinary application.

## What the full run records

- Device, Android build, memory, thermal state, sensors and hardware codecs.
- Public Camera2 IDs, complete characteristics, physical IDs, extensions and concurrent sets.
- Public stream formats, dimensions, frame durations and stall durations.
- Numeric camera-ID probes for hidden or system-only endpoints.
- Camera-open outcomes, exceptions, callbacks, availability transitions and latency.
- Actual capture-session configuration for preview, JPEG, YUV, RAW and mixed outputs.
- Standard, MediaTek and Nothing characteristic, request, result and session keys.
- Default request templates and runtime value classes.
- One metadata-complete YUV still capture.
- An eight-frame YUV burst with frame numbers, sensor timestamps, exposure, ISO, latency and throughput.
- Sensor calibration, colour transforms, black and white levels, optics, distortion, pose, shading and timing.
- A conservative routing and privilege classification scoped to what the ordinary diagnostics package observed.

## Privacy

The run is fully on-device. It does not require network access and does not persist captured photographs. YUV images are drained and closed after their timestamps are recorded. The final JSON is saved to:

```text
Downloads/Phone2Pro Diagnostics
```

## Build

Requirements:

- JDK 17
- Android SDK Platform 36
- Android Build Tools 36.0.0
- Gradle 9.5.0

From the repository root:

```bash
gradle -p diagnostics lintDebug assembleDebug
```

Install the debug build:

```bash
adb install -r diagnostics/app/build/outputs/apk/debug/app-debug.apk
```

Launch **CMF Camera Specification**, grant Camera permission, keep the phone still and leave the application open until the saved report URI is displayed.
