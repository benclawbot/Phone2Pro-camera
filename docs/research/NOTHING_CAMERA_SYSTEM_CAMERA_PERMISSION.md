# Nothing Camera system-camera permission evidence

Status: binary-manifest request recovered from Nothing Camera `16.1.01.93.20`.

Analyzed artifact:

```text
Camera-16.1.01.93.20.apk
SHA-256 f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea
```

The result can be reproduced without apktool, JADX, `aapt`, or Android SDK tools:

```bash
python3 tools/apk/extract-manifest-permissions.py \
  /private/path/Camera-16.1.01.93.20.apk \
  --expect-permission android.permission.CAMERA \
  --expect-permission android.permission.SYSTEM_CAMERA \
  --json /private/output/nothing-camera-permissions.json
```

The parser reads Android binary XML directly from `AndroidManifest.xml` and emits only derived strings and hashes.

## VERIFIED

The analyzed stock APK manifest requests both:

```text
android.permission.CAMERA
android.permission.SYSTEM_CAMERA
```

`android.permission.SYSTEM_CAMERA` is therefore an explicit package-level prerequisite in the stock application. This aligns with the recovered Galaga manual route table that selects camera endpoints `2`, `0`, and `3` before the framework `CameraManager.openCamera` call.

## PARTIALLY VERIFIED

The manifest request strengthens the direct-system-endpoint explanation because an ordinary third-party camera package generally operates with `android.permission.CAMERA`, while the stock package additionally declares the system-camera permission.

It does not independently establish that every direct endpoint open requires only this permission, or that the permission alone is sufficient.

## UNKNOWN

A manifest declaration does not prove:

- that `android.permission.SYSTEM_CAMERA` was granted to the installed package;
- which protection level and signature allowlist applied on the tested firmware;
- whether the package runs under a privileged UID or shared UID;
- the relevant AppOps state;
- the SELinux domain and CameraService policy decision;
- whether additional vendor permissions, Binder identity, session parameters, or native services are required;
- whether an independently signed application can lawfully obtain equivalent access.

## Next decisive checks

On the controlled test device, capture the following for the installed stock package and the replacement package:

```text
adb shell dumpsys package <package>
adb shell cmd package get-privapp-permissions <package-or-partition-context>
adb shell appops get <package>
adb shell ps -AZ | grep <package>
adb shell dumpsys media.camera
```

Record the package signature digest, UID, granted permissions, AppOps, SELinux domain, and the CameraService rejection or success result for IDs `2` and `3`. Do not enable the production `SystemEndpointAccess` policy until those observations identify a lawful, reproducible authorization path.
