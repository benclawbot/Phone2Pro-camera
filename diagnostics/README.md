# Phone2Pro diagnostics app

Standalone dependency-light Android app that audits the phone's public Camera2, sensor, codec, memory, and thermal capabilities.

It also validates the planned gallery flow by creating a local test JPEG in `DCIM/Phone2Pro Camera`, showing its thumbnail in the bottom-left control, and opening it in the phone's default photo viewer.

## Build

Requirements:

- JDK 17
- Android SDK platform 36 and Build Tools 36.0.0
- Gradle 9.5.0

From the repository root:

```bash
gradle -p diagnostics lintDebug assembleDebug
```

Install `diagnostics/app/build/outputs/apk/debug/app-debug.apk`, grant camera permission, and run the audit. Exported reports are written to `Downloads/Phone2Pro Diagnostics`.
