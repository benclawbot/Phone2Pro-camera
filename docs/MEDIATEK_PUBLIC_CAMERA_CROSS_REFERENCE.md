# MediaTek public camera cross-reference

**Index version:** 2026.08.04-1  
**Target:** CMF Phone 2 Pro (`A001`, `Galaga`, MT6878)  
**Observed build:** `2606151653`  
**Issue:** CAM-094 / #78

## Purpose

This reference links the target MediaTek/Nothing Camera2 metadata inventory to revision-pinned public MediaTek, ChromiumOS, AOSP and official Galaga kernel sources. It is a hypothesis generator, not a compatibility claim.

The governing rule is strict: a matching name, type, enum, class or flow is an analogue only. It does not establish identical numeric values, native metadata types, request direction, writeability, side effects, feature availability or Android routing on Galaga.

## Source revisions

- `chromeos-platform-camera-head-2026-01` — ChromiumOS `platform/camera` commit `3866159aea9c4927e27ad5aec54cc341ff1fe663`. This bounds the current indexed public repository state.
- `chromeos-mtkcam-content-2021` — commit `d2ba4bb97b93bde4cbcdb3fdf95959093f5a8e12`. This revision exposes the broad MediaTek logical-camera, feature-policy, capture/streaming, sensor, metadata, IPC and MFB/HDR interfaces used by this index.
- `chromeos-mtkcam-request-2023` — commit `238d0bcbcf1df0ea82e0995cf47ea0c137aee127`. This pins pass1/pass2 request-manager examples.
- `chromeos-mtkcam-pipeline-2023` — commit `87bf21205c86c1b659ac7d883b50c8464a4cd54b`. This pins capture/streaming pipeline and session-policy examples.
- `aosp-system-media-android16` — Android 16 `platform/system/media` commit `f01e84b958fb6a887dc0e74e4b5ebd159f03860a`. This is the metadata transport baseline.
- `nothing-galaga-kernel-2026-04` — official Galaga device-modules commit `2b0af666da693dcf4088b583bae7d77f4a4373e3`. It proves target sensor/ISP topology below Android userspace, while remaining older than the observed June build.

## Cross-reference entries

### `aosp-vendor-tag-contract`

AOSP defines `CAMERA_METADATA_VENDOR_TAG_BOUNDARY`, `metadata_vendor_id_t`, vendor enumeration callbacks, `get_camera_metadata_tag_type` and `VENDOR_SECTION_START`. These interfaces explain how vendor names and native types enter Camera2 metadata. They do not define any MediaTek or Nothing value semantics.

### `mtk-mfb-ais-parameter-family`

`MtkCameraParameters.h` exposes `KEY_MFB_MODE`, `KEY_MFB_MODE_MFLL`, `KEY_MFB_MODE_AIS` and `KEY_MFB_MODE_AUTO`. This is a direct name-family match for MFNR/AIS research, but it is a legacy Camera1 string surface from an older platform.

### `mtk-hdr-sensor-enums`

`IHalSensor.h`, sensor custom information and `MtkCameraParameters.h` separate sensor VHDR/ZHDR enums, static HDR capability and higher-level video HDR parameters. The target advertised HDR value `6` must not be assigned a historical enum meaning without target traces.

### `mtk-logical-camera-and-sync`

`IHalLogicalDeviceList`, `HalLogicalDeviceList`, `getSupportedFeature`, `getSensorSyncPrimaryDevId`, sensor sync commands and dual-camera mode show a public logical-device and synchronization architecture. They do not prove which Galaga sensors are public, physical or stock-only.

### `mtk-feature-setting-and-zsl-policy`

The feature-policy interfaces represent `mainFrame`, `subFrames`, `preFakeFrames`, `postFakeFrames` and a ZSL-flow decision. This provides a flow analogue for target ZSL, postview and prerelease metadata, not their exact buffer or timestamp contract.

### `mtk-capture-feature-graph`

`CaptureFeatureInference`, `CaptureFeatureRequest`, `CaptureFeaturePipe`, capture `P2ANode` and `P2_CaptureProcessor` demonstrate policy-selected multi-frame processing. Target ISP tuning, reprocess and frame-index keys may enter an analogous graph, but the node set and metadata layouts remain unknown.

### `mtk-streaming-feature-graph`

`StreamingFeatureNode`, `PipelineModelSessionFactory` and `ConfigStreamInfoPolicy` separate streaming features, session construction and stream policy. No one-to-one mapping is claimed for `nothing.camera.eis` or `nothing.camera.soisParams`.

### `mtk-v4l2-request-managers`

`SyncReqMgr` and `ReqApiMgr` separate pass1 synchronization from pass2 request API execution. This is useful for locating timing and request boundaries, but Galaga may use a different ISP7SP path.

### `mtk-3a-ipc-boundary`

`IPCHal3a`, `Hal3AIpcAdapter`, `Hal3aIpcServerAdapter` and `IHal3A` show a public client/server 3A boundary. ChromeOS uses a sandboxed camera-algorithm transport; the Galaga Android process and transport must be measured independently.

### `mtk-in-sensor-zoom-and-seamless-analogue`

`IHalSensor::ConfigParam` exposes `scenarioId`, continuous configuration and HDR mode, while policy interfaces produce frame sets. These structures can guide tests for in-sensor zoom and seamless mode changes, but there is no exact public match for the target key names.

### `galaga-kernel-camera-topology`

The official Galaga device tree declares four enabled sensor nodes and the MT6878 source tree declares CAMSYS, HCP and V4L2 image-sensor interfaces. This proves hardware wiring and lower-layer interfaces, not Android logical IDs, vendor tags or stock routing.

### `nothing-specific-no-public-match`

No exact public symbol match is recorded for `nothing.camera.eis`, `nothing.camera.hint` or `nothing.camera.soisParams`. Similar EIS or tuning components are insufficient to infer types, enum values or effects.

## Platform differences

`different-soc-and-isp-generation`: most detailed ChromiumOS content is MT8183-era; Galaga is MT6878 with ISP7SP-era kernel components.

`camera1-versus-camera2-control-surfaces`: several public names are Camera1 strings, while the target inventory contains Camera2 characteristic/request/result/session keys.

`chromeos-versus-android-service-boundary`: ChromeOS uses Mojo and sandboxed camera-algorithm IPC; Galaga uses an Android CameraProvider/CameraService stack.

`public-source-age`: the detailed public implementation predates the 2026 target firmware.

`kernel-userspace-gap`: official Galaga kernel source omits the exact provider, vendor-tag table, feature graph, tuning, stock controller and camera firmware.

`logical-camera-not-public-route-proof`: logical-camera classes and four wired sensors do not establish third-party auxiliary access.

## Testable hypotheses

### `hyp-mfnr-ais-mode-selection`

Guarded typed-key probes should compare accepted MFB values with frame count, exposure spread, motion sensitivity, result metadata and latency. The hypothesis fails if repeated trials remain indistinguishable from a single-frame baseline.

### `hyp-hdr-value-six`

Synchronized request/result and image traces should determine whether value `6` selects a middleware HDR mode, sensor scenario or nothing at all. Historical VHDR enum values are not imported into the target database.

### `hyp-zsl-prerelease-policy`

Stock traces should correlate ZSL timestamps, postview streams and prerelease keys with buffer selection and latency. Optical focal length should remain a separate variable.

### `hyp-cameraflex-logical-policy`

Stock 0.6x/1x/2x sessions should be compared for CameraFlex/multicam session metadata, physical result IDs, sensor activation and package-identity effects.

### `hyp-insensorzoom-seamless-scenario`

Zoom transitions should be correlated with sensor scenarios, crop regions, remosaic state, session recreation and frame discontinuities.

### `hyp-isp-tuning-reprocess-graph`

ISP tuning and frame-index hints should be compared with raw/YUV inputs, P2 timing, frame sequences, metadata sizes and output formats.

### `hyp-nothing-eis-sois-private-extension`

Stock stabilization traces should compare Nothing-specific keys with crop margin, gyro/EIS metadata, latency and output motion. No public enum mapping is assumed.

### `hyp-3a-ipc-target-boundary`

Build-matched process maps, library imports and synchronized 3A metadata should identify the first target component consuming AE/AWB/AF vendor controls.

## Non-claims

- A matching class, parameter or enum name does not prove identical numeric values, native metadata types or runtime effects on Galaga.
- The public MT8183-era ChromeOS implementation is not treated as source for the Android 16 MT6878 proprietary HAL.
- Four wired sensors in the Galaga device tree do not prove four public or physical Camera2 IDs.
- This index does not authorize writes to unknown vendor keys.
- Missing exact public symbols do not prove a feature is Nothing-only.
- This work does not close the typed vendor-tag, firmware, stock-app or build-matched binary issues.

## Maintenance

Update this index when a newer official Galaga source drop appears, the tested firmware or stock camera changes, runtime traces establish target types/effects, or a closer public MT6878/ISP7SP implementation becomes available.

Validation: `tools/validate-mediatek-public-cross-reference.py`.
