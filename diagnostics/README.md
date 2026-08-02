# Phone2Pro diagnostics app

A standalone, dependency-light Android app that collects the phone's public Camera2, sensor, codec, memory, and thermal capabilities.

The interface intentionally contains one action: **Start diagnostics and create report**. It requests camera permission, runs the complete audit, and automatically writes one JSON report to `Downloads/Phone2Pro Diagnostics`.

The diagnostics app does not implement the future camera UI, photo capture, gallery thumbnail, or default-viewer flow. Those requirements are documented separately for the production camera app.

## Build

Requirements:

- JDK 17
- Android SDK platform 36 and Build Tools 36.0.0
- Gradle 9.5.0

From the repository root:

```bash
gradle -p diagnostics lintDebug assembleDebug
```

Install `diagnostics/app/build/outputs/apk/debug/app-debug.apk`, launch it, press the single button, grant camera permission, and retrieve the generated report from `Downloads/Phone2Pro Diagnostics`.
