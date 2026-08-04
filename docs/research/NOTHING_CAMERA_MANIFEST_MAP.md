# Nothing Camera manifest, component and permission map

**Issue:** CAM-021 / #27  
**Artifact:** Nothing Camera `16.1.01.93.20`  
**APK SHA-256:** `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`  
**Manifest SHA-256:** `dd1666377a40051c3f1f5dd60f27646b2043a12efd691ec40447fa6973840eaf`

The machine-readable reference is split under:

```text
data/apk/nothing-camera-manifest/
```

`index.v1.json` contains package identity, permissions, hashes, security boundaries and route summaries. The activity, service, receiver, provider and library inventories are stored in separate deterministic files.

## Reproduction

The extractor reads Android binary XML directly and does not require apktool, JADX, AAPT or the Android SDK:

```bash
python3 tools/apk/extract-manifest-components.py \
  /private/Camera-16.1.01.93.20.apk \
  --output-dir /private/nothing-camera-manifest
```

Validate the committed reference with:

```bash
python3 tools/validate-nothing-camera-manifest-map.py
python3 -m unittest tests/test_validate_nothing_camera_manifest_map.py
```

## Verified inventory

| Item | Count |
|---|---:|
| Requested permissions | 33 |
| Components | 46 |
| Activities | 14 |
| Services | 13 |
| Receivers | 12 |
| Providers | 7 |
| Effectively exported components | 21 |
| Intent filters | 34 |
| Declared native libraries | 74 |

The APK is signed by the self-issued Nothing platform certificate:

```text
CN=platform, OU=nothing, O=nothing, L=ShenZhen, ST=GuangDong, C=zh
SHA-256 2c4e1f8eb95d96f760336f03b92bc3858111e987c59703f9873c8dc7faa4119d
```

This verifies the certificate carried by the supplied APK. It does not prove the installed package UID, partition, granted permissions, privapp allowlist, AppOps state or SELinux domain.

## Camera launch surfaces

### Main camera activity

`com.nothing.camera.activity.CameraActivity` is explicitly exported and accepts:

- `android.intent.action.MAIN`
- `com.nothing.camera.WIDGET_CAMERA`
- `android.media.action.IMAGE_CAPTURE`
- `android.media.action.VIDEO_CAPTURE`
- `android.bluetooth.headset.action.OPEN_CAMERA`

### Voice and secure routes

`VoiceCameraActivity` is explicitly exported for still and video voice-camera actions. `SecureCameraActivity` is explicitly exported for secure still, secure image-capture, secure shortcut and Bluetooth secure-open actions.

`CameraShortCutActivity` declares `android.media.action.SHORTCUT_CAMERA` but is explicitly **not exported**. The manifest therefore distinguishes the internal shortcut component from the exported secure-camera path.

### Widget and preset routes

The manifest exposes widget and preset activities, the Nothing card widget provider, and associated file/provider surfaces. These records include their exact export state, authorities, metadata and component-level permission where present.

## Service and provider boundaries

The following first-party components are explicitly exported without a manifest component permission:

- `com.nothing.camera.pipeline.ExtensionsInterfaceProxyImplService`
- `com.nothing.algolib.cameraufs.UFSService`
- `com.nothing.camera.provider.SpecialTypeProvider`
- `com.nothing.common.shortcutwidget.provider.CameraWidgetProvider`

`UFSService` runs in the separate process `com.camera.ufs.service`.

`com.nothing.cardclient.FilePermissionProvider` is exported but guarded by `com.nothing.permission.BIND_CARD_SERVICE`.

An exported declaration does not establish that arbitrary callers can perform privileged operations. Binder caller checks, URI grants, intent validation, platform permission grants and SELinux remain separate enforcement layers.

## Permission surface

The APK requests ordinary camera/media permissions plus platform, Nothing and MediaTek capabilities. High-signal requests include:

```text
android.permission.CAMERA
android.permission.SYSTEM_CAMERA
android.permission.WRITE_SECURE_SETTINGS
android.permission.READ_GLOBAL_SETTINGS
android.permission.DEVICE_POWER
android.permission.STATUS_BAR
android.permission.CONTROL_DEVICE_LIGHTS
mediatek.permission.ACCESS_APU_SYS
nothing.permission.NT_ADVANCED_THERMAL_MITIGATION
```

The manifest also declares:

```text
com.nothing.camera.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION
protectionLevel = 0x00000002
```

`SYSTEM_CAMERA` is an explicit package prerequisite and is consistent with the recovered direct Expert-mode endpoint table. A requested permission is not proof that it was granted or that it alone is sufficient for IDs `2` and `3`.

## Native dependencies

The manifest declares 74 native libraries. The inventory includes ArcSoft night, HDR, bokeh, super-resolution and beauty libraries; Qualcomm QNN CPU/GPU/DSP/HTP libraries; Nothing/third-party processing libraries; and APU/neuron dependencies.

A manifest declaration proves an expected library dependency, not that a library was present, loaded, executed or responsible for a particular mode. Exact ELF files, hashes, build IDs and dependency graphs remain work for the build-matched firmware and native-library issues.

## Evidence classification

### VERIFIED

- Package/version and target SDK from the binary manifest.
- Complete base-APK permission and component declarations.
- Explicit and platform-default export calculations for target SDK 36.
- Intent actions, categories, authorities, processes and component permissions.
- Base-APK signing certificate.
- Declared native and optional libraries.

### PARTIALLY VERIFIED

- Requested privileged permissions identify prerequisites and likely policy dependencies, but not installed grants or causal sufficiency.
- Exported components identify reachable framework entry points, but code-level validation and downstream authorization remain untested.

### UNKNOWN

- Split APK manifests and split-only components.
- Installed UID/shared UID, partition and granted permission state.
- Privapp allowlist, AppOps and role assignments.
- Runtime process and SELinux domains.
- Service-side package, signature, UID or token checks.
- Whether every declared native library is present and loaded on build `2606151653`.

Split-package acquisition remains tracked by CAM-020 / #26. Runtime privilege evidence must be captured from the exact tested firmware before any privileged replacement backend is enabled.
