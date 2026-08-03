# AOSP Camera Boundary Analysis

Status: active research for CAM-091, CAM-056 and CAM-081.

This note establishes the standard Android contracts that must be compared with the CMF Phone 2 Pro target firmware. It does not assume that Nothing's implementation is identical to AOSP.

## 1. Logical and physical cameras

Primary references:

- https://source.android.com/docs/core/camera/multi-camera
- https://android.googlesource.com/platform/system/media/+/main/camera/docs/metadata_definitions.xml
- https://android.googlesource.com/platform/frameworks/base/+/main/core/java/android/hardware/camera2/CameraCharacteristics.java

A public logical multi-camera device normally declares the logical multi-camera capability and publishes a set of physical camera IDs. A client opening the logical device may then request streams from supported physical devices and, where the implementation reports it, observe which physical device is active.

### Target comparison

The current Galaga public Camera2 dump contains only IDs `0` and `1`, and neither publishes physical IDs. Therefore the standard public physical-camera selection route is not currently advertised by those public devices.

This conclusion is intentionally narrow. It does not prove that the provider lacks auxiliary devices or logical combinations. Android also has concepts for hidden physical cameras and system-only camera devices, and CameraService may return different visibility according to device classification and caller permissions.

### Required target checks

- Inspect provider device names and metadata before CameraService filtering.
- Locate any `SYSTEM_CAMERA` capability or system-only kind for IDs 2–5.
- Inspect logical-camera metadata for hidden physical IDs in provider/HAL artifacts.
- Compare `getCameraIdList`, `getCameraIdListNoLazy` and service/provider enumeration paths on the target Android 16 framework.
- Determine whether stock Camera opens ID 4 as a CameraDevice, uses it as an application-level SAT identifier, or translates it into a different provider endpoint.

## 2. System-camera visibility

Primary references:

- AOSP camera metadata definitions.
- AOSP CameraService and CameraProviderManager source under `frameworks/av/services/camera/`.

Android's camera stack distinguishes cameras intended for general applications from cameras restricted to system clients. Enumeration and connection are separate boundaries: a device can be filtered from public lists, rejected when opened, or both.

### Target hypotheses to test

1. IDs 2–5 are provider devices classified as system-only and filtered by CameraService.
2. IDs 2 and 3 are hidden physical devices behind system-only logical ID 4.
3. ID 4 is not a framework camera ID at all; it is a stock-app/MediaTek SAT token that determines a later session configuration.
4. The stock app receives an OEM-specific device list through a hidden framework or vendor service.

These hypotheses are mutually distinguishable by provider manifests, CameraService traces, stock-app open hooks and HAL logs.

## 3. Vendor tags

Primary references:

- AOSP camera metadata definitions.
- Camera provider/HAL interfaces under `hardware/interfaces/camera/`.

Vendor tags extend the metadata namespace and can appear as characteristics, capture requests, capture results or session parameters. Visibility of a key name does not establish that every caller may set it successfully, that every value is valid, or that the key has an effect in every session.

### Target comparison

Galaga ID 0 exposes a large MediaTek/Nothing key inventory. High-priority lens-routing candidates include:

- `com.mediatek.insensorzoomfeature.insensorzoomPhysicalIdsStatus`
- `com.mediatek.insensorzoomfeature.insensorzoomEnableHints`
- `com.mediatek.seamlessfeature.sensorScenario`
- `com.mediatek.seamlessfeature.forceSensorMode`
- `com.mediatek.seamlessfeature.configCellCropSensorIds`
- `com.mediatek.seamlessfeature.configCellFullSensorIds`
- `com.mediatek.seamlessfeature.configSensorScenarios`
- `com.mediatek.cameraflex.flexibleCapabilities`
- `com.mediatek.multicamfeature.availableMultiCamFeatureSensorManualUpdated`
- `com.mediatek.streamingfeature.pipDevices`

The key inventory supports testing these paths, but the causal role and caller restrictions remain unknown.

### Required target checks

- Recover native metadata types and vendor section/tag IDs.
- Trace stock-app writes and session ordering.
- Capture provider/HAL metadata at `configureStreams` and request submission.
- Test one evidence-backed setting at a time from an ordinary app.
- Record accepted-but-ineffective values separately from rejected values.

## 4. Session parameters

Primary references:

- AOSP camera metadata definitions.
- Camera2 session configuration APIs and Camera HAL interfaces.

Some controls must be supplied as session parameters before stream configuration and cannot be reproduced by changing an ordinary repeating request after a session is active.

### Target comparison

The device advertises vendor session keys for HDR, EIS, ZSL, proprietary initialization, CameraFlex, in-sensor zoom and seamless sensor configuration. The external widget experiment may have established the focal string in application state without reproducing the complete session-time configuration used by the internal Expert path.

### Required target checks

- Hook `SessionConfiguration.setSessionParameters` and stock wrappers.
- Diff session parameters for fresh launches at 0.6×, 1× and 2×.
- Detect whether switching closes/reopens the CameraDevice or only recreates the session.
- Preserve request ordering and initialization calls when building a reproducer.

## 5. Physical-camera request keys

Primary references:

- `CameraCharacteristics.REQUEST_AVAILABLE_PHYSICAL_CAMERA_REQUEST_KEYS`.
- Logical multi-camera documentation.

When a public logical camera supports per-physical overrides, it advertises the keys that may be applied to a physical camera. The current ID 0 dump reports no physical IDs and no physical-camera request keys.

### Target consequence

A replacement app cannot presently rely on the standard public `setPhysicalCameraKey` path for ID 0. That route should still be retested if a hidden/system logical device becomes reachable or firmware changes the public metadata.

## 6. Active physical camera reporting

Primary references:

- Android camera metadata definitions for active physical ID.
- Android NDK camera metadata definitions.

Where supplied, active-physical-ID metadata can identify the physical sensor used by a logical route. Its absence does not prevent alternative vendor result keys from reporting sensor state.

### Target checks

- Search standard and vendor result inventories for physical/sensor status.
- Hook raw metadata before the stock app consumes it.
- Correlate results with EXIF focal length, aperture, field of view and camera availability.

## 7. Current AOSP-based conclusion

The public Galaga camera description does not expose the standard Android public logical/physical multi-camera contract. That establishes the limitation of the current public route, not the limit of the firmware.

The next decisive evidence must come from below or beside that public contract:

1. provider/HAL enumeration and device classification;
2. stock-app CameraDevice and session hooks;
3. vendor session/request metadata;
4. framework/service identity checks;
5. native MediaTek routing code.

The project should not close the auxiliary-lens question until those layers are mapped or an exact privilege boundary is demonstrated.
