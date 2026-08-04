# Android 16 camera contract reference

Status: pinned AOSP/official Android cross-reference for CAM-091.

Reference: **Android 16 / API 36**, branch `android16-release`.
Target: **CMF Phone 2 Pro** (`Galaga`), Android 16, MediaTek MT6878.

## Evidence classification

- **VERIFIED:** Pinned Android 16 source symbols, official release history, and target observations are indexed without treating optional capability absence as a deviation.
- **PARTIALLY VERIFIED:** A standards match identifies expected behavior but does not prove the OEM binaries are byte-identical to AOSP.
- **UNKNOWN:** Unobserved target interfaces, route-specific vendor values, and lower-layer behavior remain unknown until measured on matching firmware.

## Target comparison summary

| State | Count | Meaning |
|---|---:|---|
| `CONFORMING` | 4 | Observed target behavior follows the standard contract. |
| `NOT_ADVERTISED` | 4 | The optional standard capability is not advertised on the public target route; this is not a deviation. |
| `OEM_EXTENSION` | 1 | The target exposes an OEM/vendor extension within an Android-defined extension point; semantics remain device-specific. |
| `DEVIATION` | 0 | Observed target behavior conflicts with the pinned standard contract. |
| `UNKNOWN` | 3 | Available target evidence does not establish conformance or deviation. |

**No target deviation is currently confirmed.** Optional capability absence and OEM vendor tags are classified separately.

## Contract index

| Contract | Introduced | Android 16 anchors | Target state | Confidence | Target observation |
|---|---|---|---|---|---|
| Camera2 device and request pipeline | Android 5.0 / API 21 | [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraManager.java`: `getCameraIdList`, `getCameraCharacteristics`, `openCamera`<br>[`official-camera-hal`](https://source.android.com/docs/core/camera/camera3) — `Camera HAL3 request/result pipeline` | `CONFORMING` | `VERIFIED` | The ordinary Galaga diagnostic application enumerates public IDs 0 and 1, reads their characteristics, and opens them through Camera2. |
| Logical multi-camera capability | Android 9 / API 28 | [`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `android.request.availableCapabilities.LOGICAL_MULTI_CAMERA`, `android.logicalMultiCamera.physicalIds`, `android.logicalMultiCamera.sensorSyncType`<br>[`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraCharacteristics.java`: `getPhysicalCameraIds`, `getAvailablePhysicalCameraRequestKeys`<br>[`official-multi-camera`](https://source.android.com/docs/core/camera/multi-camera) — `logical device`, `physical streams`, `physical request controls` | `NOT_ADVERTISED` | `VERIFIED` | Public Galaga ID 0 does not advertise LOGICAL_MULTI_CAMERA, physical IDs, or physical-camera request keys. |
| Hidden physical camera characteristics | Android 10 / API 29 | [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraManager.java`: `getCameraCharacteristics`<br>[`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraCharacteristics.java`: `getPhysicalCameraIds`<br>[`official-multi-camera`](https://source.android.com/docs/core/camera/multi-camera) — `hide physical sub-cameras from getCameraIdList` | `NOT_ADVERTISED` | `VERIFIED` | Public Galaga ID 0 does not advertise physical members. Direct queries of IDs 2 through 5 follow the separate system-camera rejection contract rather than the hidden-physical-member contract. |
| Physical output and request controls | Android 9 / API 28 | [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/params/OutputConfiguration.java`: `setPhysicalCameraId`<br>[`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CaptureRequest.java`: `Builder.setPhysicalCameraKey`<br>[`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `android.request.availablePhysicalCameraRequestKeys` | `NOT_ADVERTISED` | `VERIFIED` | The public Galaga camera exposes neither physical IDs nor available physical request keys, so the standard public physical-output route is unavailable. |
| Active physical camera reporting | Android 10 / HAL 3.5 | [`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `android.logicalMultiCamera.activePhysicalId`<br>[`official-multi-camera`](https://source.android.com/docs/core/camera/multi-camera) — `ANDROID_LOGICAL_MULTI_CAMERA_ACTIVE_PHYSICAL_ID` | `NOT_ADVERTISED` | `VERIFIED` | Public Galaga ID 0 does not advertise the logical multi-camera contract, so absence of standard active-physical reporting is expected. |
| System-only camera visibility and authorization | Android 11 / API 30 | [`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `android.request.availableCapabilities.SYSTEM_CAMERA`<br>[`frameworks-av-android16`](https://android.googlesource.com/platform/frameworks/av/+/4b2111885ff934799e70eddae2527a9848c3be29/) — `services/camera/libcameraservice/CameraService.cpp`: `shouldSkipStatusUpdates`, `shouldRejectSystemCameraConnection`, `connectHelper`<br>[`frameworks-av-android16`](https://android.googlesource.com/platform/frameworks/av/+/4b2111885ff934799e70eddae2527a9848c3be29/) — `services/camera/libcameraservice/common/CameraProviderManager.h`: `SystemCameraKind`<br>[`official-system-cameras`](https://source.android.com/docs/core/camera/system-cameras) — `android.permission.SYSTEM_CAMERA`, `privapp-permissions.xml`, `Camera2PermissionTest.testSystemCameraDiscovery` | `CONFORMING` | `VERIFIED` | Galaga IDs 2 through 5 are omitted from the ordinary list and rejected at characteristics with the exact system-only-device message; connect is not independently reached by the current probe. |
| Zoom ratio control | Android 11 / API 30 | [`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `android.control.zoomRatio`, `android.control.zoomRatioRange`<br>[`official-multi-camera`](https://source.android.com/docs/core/camera/multi-camera) — `ANDROID_CONTROL_ZOOM_RATIO best practice` | `CONFORMING` | `VERIFIED` | Public Galaga zoom remains on ID 0 and behaves as digital crop. The absence of public optical switching is not a standards deviation because ID 0 does not advertise logical multi-camera. |
| Session-wide capture parameters | Android 9 / API 28 | [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/params/SessionConfiguration.java`: `setSessionParameters`, `getSessionParameters`<br>[`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraCharacteristics.java`: `getAvailableSessionKeys`<br>[`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `android.request.availableSessionKeys` | `UNKNOWN` | `UNKNOWN` | Galaga exposes vendor session keys and the stock APK sets session parameters, but no route-specific typed key/value sequence has been causally reproduced for 0.6x, 1x, and 2x. |
| Vendor metadata extensions | Android 5.0 / API 21 | [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraCharacteristics.java`: `getKeys`, `getAvailableCaptureRequestKeys`, `getAvailableCaptureResultKeys`<br>[`hardware-interfaces-android16`](https://android.googlesource.com/platform/hardware/interfaces/+/5688f7eb1e117ed26e642a695de300b7683acb87/camera/) — `camera/provider/aidl/android/hardware/camera/provider/ICameraProvider.aidl`: `getVendorTags`<br>[`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) — `vendor extension namespace` | `OEM_EXTENSION` | `VERIFIED` | Public Galaga ID 0 exposes a large MediaTek/Nothing vendor-key inventory. Names and types are observable; routing causality, value domains, and caller restrictions remain unknown. |
| Camera2 and CameraX extensions | Android 12 / API 31 | [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) — `core/java/android/hardware/camera2/CameraExtensionCharacteristics.java`: `getSupportedExtensions`, `getExtensionSupportedSizes`<br>[`official-camera-extensions`](https://source.android.com/docs/core/camera/camerax-vendor-extensions) — `ro.camerax.extensions.enabled`, `OEM vendor library` | `UNKNOWN` | `UNKNOWN` | The current evidence does not establish whether Galaga exposes a usable Camera2/CameraX extension route relevant to auxiliary optical lenses. |
| CameraService visibility, characteristics, and connection stages | Android 11 / API 30 | [`frameworks-av-android16`](https://android.googlesource.com/platform/frameworks/av/+/4b2111885ff934799e70eddae2527a9848c3be29/) — `services/camera/libcameraservice/CameraService.cpp`: `shouldSkipStatusUpdates`, `shouldRejectSystemCameraConnection`, `connectHelper`<br>[`frameworks-av-android16`](https://android.googlesource.com/platform/frameworks/av/+/4b2111885ff934799e70eddae2527a9848c3be29/) — `services/camera/libcameraservice/common/CameraProviderManager.cpp`: `collectDeviceIdsLocked` | `CONFORMING` | `VERIFIED` | The Galaga ordinary probe reaches enumeration and characteristics rejection for IDs 2 through 5 but its open attempt repeats the characteristics preflight failure, so connect remains unobserved. |
| Camera HAL AIDL and HIDL interface generations | Android 13 / AIDL camera HAL support | [`hardware-interfaces-android16`](https://android.googlesource.com/platform/hardware/interfaces/+/5688f7eb1e117ed26e642a695de300b7683acb87/camera/) — `camera/provider/aidl`: `ICameraProvider`<br>[`hardware-interfaces-android16`](https://android.googlesource.com/platform/hardware/interfaces/+/5688f7eb1e117ed26e642a695de300b7683acb87/camera/) — `camera/device/aidl`: `ICameraDevice`, `ICameraDeviceSession`<br>[`official-camera-hal`](https://source.android.com/docs/core/camera/camera3) — `AIDL camera HAL`, `HIDL camera HAL compatibility` | `UNKNOWN` | `UNKNOWN` | The exact Galaga provider interface generation, instance name, version/hash, and device-session contract have not yet been confirmed from target firmware evidence. |

## Version differences and target consequences

### Camera2 device and request pipeline

**Standard contract:** Applications enumerate CameraDevice IDs, query fixed characteristics, configure output streams, and submit one-shot or repeating capture requests.

Version history:
- Camera2 was added in Android 5.0 / API 21.
- Android 8 introduced stable Treble HIDL camera HAL interfaces.
- Android 13 added AIDL camera HAL support while retaining HIDL compatibility.

**Galaga comparison — `CONFORMING` / `VERIFIED`:** The ordinary Galaga diagnostic application enumerates public IDs 0 and 1, reads their characteristics, and opens them through Camera2.

Target evidence:
- [`target-filtering`](./SYSTEM_CAMERA_FILTERING_MODEL.md)

### Logical multi-camera capability

**Standard contract:** A logical camera advertises LOGICAL_MULTI_CAMERA and may expose physical IDs, physical streams, per-physical controls, and physical results.

Version history:
- Android 9 introduced public logical/physical multi-camera APIs.
- Android 10 removed the Android 9 mandatory physical-stream replacement rule and added stream-combination queries for HAL 3.5+.
- Individual physical request support remains optional and is capability-driven.

**Galaga comparison — `NOT_ADVERTISED` / `VERIFIED`:** Public Galaga ID 0 does not advertise LOGICAL_MULTI_CAMERA, physical IDs, or physical-camera request keys.

Target evidence:
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)

### Hidden physical camera characteristics

**Standard contract:** From API 29, a physical ID may be omitted from getCameraIdList yet remain queryable as a physical member of a reachable logical camera.

Version history:
- Before API 29, physical IDs returned by getPhysicalCameraIds were also directly listed/openable.
- From API 29, unlisted physical IDs can be queried but only used through their logical camera unless separately listed.

**Galaga comparison — `NOT_ADVERTISED` / `VERIFIED`:** Public Galaga ID 0 does not advertise physical members. Direct queries of IDs 2 through 5 follow the separate system-camera rejection contract rather than the hidden-physical-member contract.

Target evidence:
- [`target-filtering`](./SYSTEM_CAMERA_FILTERING_MODEL.md)
- [`target-privilege-boundary`](./CAMERA_PRIVILEGE_BOUNDARY.md)

### Physical output and request controls

**Standard contract:** Physical output targeting and per-physical request overrides are valid only for advertised physical members of a logical camera and supported request keys.

Version history:
- OutputConfiguration.setPhysicalCameraId and physical request keys were added with API 28 logical multi-camera support.
- Support is optional and limited to advertised physical IDs and keys.

**Galaga comparison — `NOT_ADVERTISED` / `VERIFIED`:** The public Galaga camera exposes neither physical IDs nor available physical request keys, so the standard public physical-output route is unavailable.

Target evidence:
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)

### Active physical camera reporting

**Standard contract:** HAL 3.5+ logical cameras report the active physical camera ID in results when the logical multi-camera contract applies.

Version history:
- The active physical ID result requirement applies to HAL device version 3.5, introduced with Android 10.
- The key is meaningful only for a logical multi-camera device.

**Galaga comparison — `NOT_ADVERTISED` / `VERIFIED`:** Public Galaga ID 0 does not advertise the logical multi-camera contract, so absence of standard active-physical reporting is expected.

Target evidence:
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)

### System-only camera visibility and authorization

**Standard contract:** A HAL marks a system camera with SYSTEM_CAMERA capability; CameraService filters it from unauthorized callers and requires regular CAMERA plus SYSTEM_CAMERA and eligible device policy.

Version history:
- System cameras and android.permission.SYSTEM_CAMERA were introduced in Android 11.
- The official contract requires device-specific privileged-permission allowlisting in addition to normal CAMERA permission.

**Galaga comparison — `CONFORMING` / `VERIFIED`:** Galaga IDs 2 through 5 are omitted from the ordinary list and rejected at characteristics with the exact system-only-device message; connect is not independently reached by the current probe.

Target evidence:
- [`target-filtering`](./SYSTEM_CAMERA_FILTERING_MODEL.md)
- [`target-privilege-boundary`](./CAMERA_PRIVILEGE_BOUNDARY.md)

### Zoom ratio control

**Standard contract:** CONTROL_ZOOM_RATIO defines a field-of-view control; logical multi-camera implementations may use it for HAL optical switching, but the API does not require every public camera to contain multiple physical sensors.

Version history:
- Zoom ratio was introduced in Android 11.
- For Android 11+ logical optical-zoom devices, AOSP recommends zoom ratio for zoom and crop region for aspect-ratio cropping.

**Galaga comparison — `CONFORMING` / `VERIFIED`:** Public Galaga zoom remains on ID 0 and behaves as digital crop. The absence of public optical switching is not a standards deviation because ID 0 does not advertise logical multi-camera.

Target evidence:
- [`target-direct-route`](./GALAGA_EXPERT_DIRECT_ROUTE.md)
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)

### Session-wide capture parameters

**Standard contract:** Session parameters are a declared subset of capture request keys passed during session initialization; unsupported keys are ignored and changes may require session recreation.

Version history:
- SessionConfiguration and setSessionParameters were added in API 28.
- Android 15 / API 35 added setup-time session support queries, but the Android 16 target still uses the same declared session-key contract.

**Galaga comparison — `UNKNOWN` / `UNKNOWN`:** Galaga exposes vendor session keys and the stock APK sets session parameters, but no route-specific typed key/value sequence has been causally reproduced for 0.6x, 1x, and 2x.

Target evidence:
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)
- [`target-direct-route`](./GALAGA_EXPERT_DIRECT_ROUTE.md)

### Vendor metadata extensions

**Standard contract:** Camera providers may define vendor metadata sections and typed tags beyond the standard namespace; presence and visibility do not guarantee that an arbitrary caller can set a key or produce an effect.

Version history:
- Vendor metadata extension points are part of the Camera2/HAL3 model.
- AIDL and HIDL providers expose versioned vendor-tag descriptors through their respective interfaces.

**Galaga comparison — `OEM_EXTENSION` / `VERIFIED`:** Public Galaga ID 0 exposes a large MediaTek/Nothing vendor-key inventory. Names and types are observable; routing causality, value domains, and caller restrictions remain unknown.

Target evidence:
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)

### Camera2 and CameraX extensions

**Standard contract:** Extensions expose OEM processing modes through a declared Camera2/CameraX extension contract; extension availability is queried per public camera and does not imply direct access to hidden camera IDs.

Version history:
- CameraExtensionCharacteristics was added in API 31 / Android 12.
- Android 12+ CameraX extension support requires ro.camerax.extensions.enabled on supporting devices.
- Later releases expanded extension request/result controls without changing the requirement for declared support.

**Galaga comparison — `UNKNOWN` / `UNKNOWN`:** The current evidence does not establish whether Galaga exposes a usable Camera2/CameraX extension route relevant to auxiliary optical lenses.

Target evidence:
- [`target-vendor-tags`](./AOSP_CAMERA_BOUNDARIES.md)

### CameraService visibility, characteristics, and connection stages

**Standard contract:** Caller-sensitive enumeration/status filtering, characteristics authorization, and camera connection are distinct stages; failure at an earlier stage does not prove a later stage was reached.

Version history:
- The system-camera stage separation became directly relevant with Android 11 system-only devices.
- Android 16 retains separate provider classification, status filtering, characteristics checks, and connection checks.

**Galaga comparison — `CONFORMING` / `VERIFIED`:** The Galaga ordinary probe reaches enumeration and characteristics rejection for IDs 2 through 5 but its open attempt repeats the characteristics preflight failure, so connect remains unobserved.

Target evidence:
- [`target-filtering`](./SYSTEM_CAMERA_FILTERING_MODEL.md)
- [`target-privilege-boundary`](./CAMERA_PRIVILEGE_BOUNDARY.md)

### Camera HAL AIDL and HIDL interface generations

**Standard contract:** Android 13+ supports AIDL camera HALs and continues to support HIDL camera HALs, but camera features introduced in Android 13+ are available only through AIDL interfaces.

Version history:
- Android 8 introduced stable HIDL camera HAL interfaces through Treble.
- Android 13 added AIDL camera HAL support and made new Android 13+ camera HAL features AIDL-only.
- Android 16 still supports existing HIDL camera HAL implementations.

**Galaga comparison — `UNKNOWN` / `UNKNOWN`:** The exact Galaga provider interface generation, instance name, version/hash, and device-session contract have not yet been confirmed from target firmware evidence.

Target evidence:
- [`target-privilege-boundary`](./CAMERA_PRIVILEGE_BOUNDARY.md)

## Pinned Android 16 source revisions

| Source | Revision | Scope |
|---|---|---|
| [`frameworks-base-android16`](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/) | `99b01a65cc4c104933788b3143285ab6bae65827` | AOSP frameworks/base Android 16 |
| [`frameworks-av-android16`](https://android.googlesource.com/platform/frameworks/av/+/4b2111885ff934799e70eddae2527a9848c3be29/) | `4b2111885ff934799e70eddae2527a9848c3be29` | AOSP frameworks/av Android 16 |
| [`system-media-android16`](https://android.googlesource.com/platform/system/media/+/f01e84b958fb6a887dc0e74e4b5ebd159f03860a/camera/docs/metadata_definitions.xml) | `f01e84b958fb6a887dc0e74e4b5ebd159f03860a` | AOSP system/media Android 16 camera metadata |
| [`hardware-interfaces-android16`](https://android.googlesource.com/platform/hardware/interfaces/+/5688f7eb1e117ed26e642a695de300b7683acb87/camera/) | `5688f7eb1e117ed26e642a695de300b7683acb87` | AOSP hardware/interfaces Android 16 camera HAL |

## Unresolved target checks

- `session-parameters`: Galaga exposes vendor session keys and the stock APK sets session parameters, but no route-specific typed key/value sequence has been causally reproduced for 0.6x, 1x, and 2x.
- `camera-extensions`: The current evidence does not establish whether Galaga exposes a usable Camera2/CameraX extension route relevant to auxiliary optical lenses.
- `camera-hal-interface-generation`: The exact Galaga provider interface generation, instance name, version/hash, and device-session contract have not yet been confirmed from target firmware evidence.

## Generation

This document is generated from `research/contracts/android16-camera-contracts.json`:

```bash
python3 tools/research/build-aosp-camera-contract-reference.py \
  --markdown docs/research/AOSP_CAMERA_CONTRACT_REFERENCE.md \
  --json /private/android16-camera-contract-reference.json
```
