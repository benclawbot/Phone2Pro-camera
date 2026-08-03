# External Research Baseline

Research date: 2026-08-03.

This index starts the external research track. It is deliberately broader than the Nothing Camera APK and will be expanded into source-level cross-references.

## AOSP and official Android camera architecture

### Logical and physical multi-camera

Primary source:

- https://source.android.com/docs/core/camera/multi-camera

Key points to validate against the target firmware:

- A logical camera may combine multiple same-facing physical devices.
- Public clients can control physical streams only when the logical device advertises `LOGICAL_MULTI_CAMERA` and exposes physical IDs.
- `android.logicalMultiCamera.activePhysicalId` can report the active sensor where implemented.
- HAL 3.5+ has explicit stream-combination support requirements.

Target relevance:

- Public IDs `0` and `1` do not advertise physical IDs in the current device dump.
- The firmware can still define hidden or system-camera logical routes distinct from the public camera list.
- We must identify whether stock ID `4` is represented through CameraService/provider metadata, an internal configuration database, or MediaTek application logic.

### Camera metadata contracts

Primary sources:

- https://android.googlesource.com/platform/system/media/+/main/camera/docs/metadata_definitions.xml
- https://android.googlesource.com/platform/frameworks/base/+/main/core/java/android/hardware/camera2/CameraCharacteristics.java

Key points:

- Available request/result/session keys define the accepted standard metadata surface.
- Vendor tags are registered separately and can be visible through Camera2 metadata APIs.
- `availablePhysicalCameraRequestKeys` applies only where physical-device overrides are supported.
- Android's metadata definitions explicitly describe hidden physical IDs and `SYSTEM_CAMERA` behaviour, so public enumeration alone is not a complete firmware camera inventory.

### Camera provider and HAL

Primary source family:

- https://source.android.com/docs/core/camera
- AOSP `hardware/interfaces/camera/`
- AOSP `frameworks/av/services/camera/`

Research tasks:

- Determine AIDL versus HIDL provider implementation on the target build.
- Map CameraService filtering of public, system-only and hidden camera IDs.
- Map package/UID attribution, permissions and app-op checks.
- Compare the target provider's vendor-tag registration with AOSP interfaces.

## Nothing and CMF sources

### Official product and support material

- https://nothing.tech/pages/cmf-phone-2-pro
- https://support.nothing.tech/

These sources establish marketed hardware and supported user-facing modes but do not document privileged camera interfaces.

### Nothing OSS and device source discovery

Discovery sources:

- https://github.com/NothingOSS
- https://nothingarchive.tech/docs/official
- https://nothingarchive.tech/docs/devices

Current lead:

- The device codename is `Galaga` and kernel sources have been reported under a Galaga branch in Nothing's public source repositories.

Required validation:

- Identify the exact official repository and branch.
- Record commit and release correspondence to each firmware build.
- Extract camera-related device tree, defconfig, drivers, power sequences, regulators, GPIO, I²C, sensor, actuator, flash, EEPROM and OIS references.
- Do not assume proprietary userspace HAL or ISP code is present in the kernel release.

### Firmware archives

Discovery source:

- https://nothingarchive.tech/docs/firmware

Use:

- Build a firmware-version matrix.
- Acquire legally redistributable or user-provided images.
- Extract system, system_ext, product, vendor, odm and vendor_dlkm artifacts.
- Diff camera APKs, framework JARs, permissions, overlays, native libraries, service manifests and SELinux policy between releases.

## MediaTek public implementation references

Public MediaTek camera source appears in AOSP-derived vendor trees, ChromeOS camera code and device releases. These references may not exactly match MT6878, so they are taxonomy and implementation leads rather than target proof.

High-value subsystem names already visible in the device metadata:

- MFNR / MFB / AIS.
- HDR / VHDR / MStream HDR / FrameSync.
- 3A controls and results.
- FeaturePipe and post-processing.
- Dual zoom / multicam / CameraFlex.
- In-sensor zoom.
- Seamless sensor scenarios.
- ISP tuning and metadata buffers.
- ZSL, postview and early notification.
- Video AI NR and preview compression.

Starting public-source lead:

- https://chromium.googlesource.com/chromiumos/platform/camera/

Research rule:

- Map names, types and control flow from public MediaTek code to the target key inventory.
- Mark mappings as inferred until confirmed in the target APK, firmware or native libraries.

## Community evidence

Community sources are used for discovery and independent corroboration, never as sole implementation proof.

Starting points:

- https://nothing.community/d/58672-feature-request-unblock-camera2-api-for-telephoto-ultrawide-lenses-on-cmf-phone-2-pro
- https://nothing.community/d/32446-cmf-phone-2-pro-camera-feedback
- GCam and CMF community reports.

Current corroborated observation:

- Multiple third-party users report only IDs `0` and `1` being visible to ordinary Camera2/GCam clients.

Interpretation rule:

- This supports the public-enumeration finding.
- It does not identify the internal stock-camera route or prove that every non-public mechanism is inaccessible.

## Open-source camera implementations

Projects to inspect for reusable architecture and algorithms:

- Android CameraX and CameraPipe.
- Open Camera.
- MotionCam.
- PhotonCamera.
- Libre Camera.
- GrapheneOS Camera.

Research outputs:

- Capture-session architecture.
- Camera2 interoperability patterns.
- RAW/YUV/burst handling.
- Gyroscope-assisted alignment.
- Memory and backpressure handling.
- Thermal degradation policies.
- Licensing constraints and reusable components.

## Computational-photography research

Target topics:

- HDR+ burst capture and merge.
- Multi-frame super-resolution.
- Robust alignment under local motion.
- Frame selection and motion scoring.
- Burst denoising.
- Natural sharpening and tone mapping.
- Dual-camera fusion, if auxiliary capture becomes available.
- Mobile GPU/NPU implementation trade-offs.

Each paper will be recorded with algorithm summary, assumptions, compute/memory cost, licensing/implementation status and relevance to `Quick`, `Auto` or `Max Detail`.

## Immediate external-research actions

1. Resolve the official Galaga kernel-source branch and exact build relationship.
2. Locate firmware dumps matching the diagnostic build fingerprint.
3. Build an AOSP cross-reference for system-camera filtering, hidden physical IDs, vendor tags and session parameters.
4. Search public MediaTek trees for every vendor-key family present in the device dump.
5. Establish a source index with URL, revision, license, target relevance and confidence.
