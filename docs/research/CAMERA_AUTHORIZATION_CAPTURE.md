# Camera authorization evidence capture

Status: read-only device evidence workflow for the stock Nothing Camera package and the Phone2Pro replacement package.

## Purpose

Static analysis has established that the stock Galaga camera application requests `android.permission.SYSTEM_CAMERA` and contains direct manual routes to camera endpoints `2`, `0`, and `3`.

The remaining blocker is authorization: whether that permission is granted, which UID and SELinux domain the stock package uses, what AppOps state applies, and what CameraService reports for the installed build.

## Run

```bash
bash tools/device/capture-camera-authorization.sh \
  --serial DEVICE_SERIAL \
  --stock-package com.nothing.camera \
  --replacement-package com.phone2pro.camera \
  --output /private/output/camera-authorization
```

The collector requires `adb` and `sha256sum`. It is read-only and does not:

- open a camera endpoint;
- grant or revoke permissions;
- change AppOps;
- root or remount the device;
- copy APK contents;
- modify SELinux policy.

## Captured evidence

For the device:

```text
build properties
SELinux enforcing state
process SELinux contexts
permission definitions
package-to-UID mapping
CameraService state
camera proxy state
Android service inventory
```

For both the stock and replacement packages:

```text
dumpsys package
AppOps
package path
UID mapping
running PID
privileged permission allow and deny records
CAMERA permission check
SYSTEM_CAMERA permission check
filtered summary of UID, grants and process context
```

Every output file is indexed with size and SHA-256 in `manifest.yaml`.

## Interpretation

A granted `android.permission.SYSTEM_CAMERA` result for the stock package, combined with a privileged or platform-associated UID and SELinux domain, would materially narrow the authorization mechanism.

A denied result for the replacement package would explain why the statically recovered direct endpoints cannot be enabled in an ordinary application build.

These observations still do not prove that IDs `2` and `3` can be opened successfully. Endpoint availability must be established separately with a controlled open attempt and capture-result verification on hardware where the operator is authorized to test.
