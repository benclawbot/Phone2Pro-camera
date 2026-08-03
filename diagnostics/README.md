# Phone2Pro diagnostics app

A standalone Android 16 diagnostics application for building an evidence-backed specification of the CMF Phone 2 Pro camera platform.

## Full specification run

The launcher action, **Build full camera specification**, creates one JSON report in `Downloads/Phone2Pro Diagnostics`. The run remains fully on-device and does not persist the YUV test frames.

The report includes:

- public Camera2 IDs and complete characteristics;
- numeric hidden/system-only ID probes and exact open failures;
- availability callbacks and open latency;
- public stream and capture-session matrix;
- standard, MediaTek, and Nothing characteristic/request/result/session keys;
- default request templates and runtime Java value classes;
- a metadata-complete still capture;
- an eight-frame YUV burst with frame, sensor timestamp, exposure, ISO, latency, and throughput data;
- sensor calibration, colour transforms, black/white levels, optics, distortion, shading, and stream timing;
- a conservative routing/privilege classification scoped to what the ordinary diagnostics package actually observed.

The second launcher button opens the earlier focused capture audits for daylight routing, low light, official Expert mode, and stock-camera launch paths.

## Privacy

- No network access is required.
- The full specification run does not save photographs.
- Captured YUV buffers are drained and closed after their timestamps are recorded.
- Focused legacy audits may save explicitly labelled JPEG samples where their instructions say so.

## Build

Requirements:

- JDK 17
- Android SDK platform 36 and Build Tools 36.0.0
- Gradle 9.5.0

From the repository root:

```bash
gradle -p diagnostics lintDebug assembleDebug
```

Install:

```bash
adb install -r diagnostics/app/build/outputs/apk/debug/app-debug.apk
```

Launch the app, grant Camera permission, keep the phone still, and leave the app open until the JSON URI is displayed.
