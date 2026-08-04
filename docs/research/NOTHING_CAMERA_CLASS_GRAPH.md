# Nothing Camera package and class dependency graph

**Reference:** `2026.08.04-1`  
**Issue:** CAM-022 / #28  
**Evidence:** static DEX references only

## Scope

The graph covers 320,221 defined methods across 7 DEX files. It retains 679 camera-routing candidates and bounds the committed graph to 80 class nodes and 70 weighted direct-reference edges.

## Highest-centrality camera classes

| Class | Role | Candidate methods | Max score | In | Out | Signals |
|---|---|---:|---:|---:|---:|---|
| `com.nothing.common.utils.LogUtil` | `NATIVE_BRIDGE` | 1 | 20 | 129 | 2 | vendor-routing-key |
| `com.nothing.camera.mode.NcfBokehMode` | `CLASS` | 4 | 20 | 1 | 105 | sat-multicam, vendor-routing-key |
| `com.nothing.camera.offlinealgo.ncf.NcfSimulationMode` | `CLASS` | 4 | 20 | 8 | 90 | sat-multicam, vendor-routing-key |
| `com.nothing.common.setting.SettingContext` | `CONTEXT` | 6 | 20 | 1 | 78 | sat-multicam, vendor-routing-key |
| `com.nothing.camera.mode.PhotoMode` | `CLASS` | 3 | 20 | 0 | 73 | vendor-routing-key |
| `com.nothing.camera.pipeline.ncf.NcfCaptureCommonParameter` | `CLASS` | 0 | 0 | 99 | 0 |  |
| `com.nothing.camera.pipeline.node.NightNode` | `CLASS` | 1 | 20 | 0 | 72 | vendor-routing-key |
| `com.nothing.camera.pipeline.CaptureHolder` | `CLASS` | 0 | 0 | 91 | 0 |  |
| `com.nothing.common.setting.SettingCharacteristics` | `CLASS` | 3 | 20 | 45 | 15 | sat-multicam, vendor-routing-key |
| `com.nothing.camera.modeLegacyV2.CameraVideoMode` | `CLASS` | 4 | 20 | 0 | 55 | camera-id-constant, expert-ui, sat-multicam, vendor-routing-key |
| `com.nothing.yuvutils.YuvUtils` | `CLASS` | 24 | 11 | 3 | 1 | jni-native |
| `com.nothing.camera.modeLegacyV2.BokehMode` | `CLASS` | 3 | 20 | 23 | 31 | vendor-routing-key |
| `com.nothing.common.setting.Utils` | `CLASS` | 1 | 20 | 56 | 0 | vendor-routing-key |
| `com.nothing.common.motion.libyuv.util.YuvUtil` | `NATIVE_BRIDGE` | 22 | 11 | 0 | 1 | jni-native |
| `com.nothing.camera.mode.NcfPhotoMode` | `CLASS` | 3 | 20 | 1 | 42 | sat-multicam, vendor-routing-key |
| `com.nothing.camera.activity.CameraActivity` | `CLASS` | 4 | 26 | 1 | 32 | camera-id-constant, vendor-routing-key |
| `com.nothing.camera.pipeline.ncf.NcfCaptureCommonParameter$Builder` | `CLASS` | 0 | 0 | 70 | 0 |  |
| `com.nothing.camera.modeLegacyV2.BokehMode$BokehDisHandler` | `CLASS` | 1 | 20 | 0 | 44 | vendor-routing-key |
| `com.nothing.camera.pipeline.ExtensionsInterfaceProxyImplService$ExtensionsInterfaceProxySubImplService` | `CLASS` | 1 | 21 | 0 | 41 | camera-enumeration, sat-multicam |
| `com.nothing.camera.pipeline.DataCollector$Extra` | `CLASS` | 0 | 0 | 65 | 0 |  |
| `com.nothing.cameracore.context.module.usecaseV2.DualYuvPreview` | `USE_CASE` | 1 | 53 | 2 | 6 | physical-output, sat-multicam |
| `com.nothing.camera.pipeline.node.UltraHdrNode` | `CLASS` | 1 | 20 | 0 | 40 | vendor-routing-key |
| `com.nothing.cameracore.context.module.usecase.DualYuvImageCapture` | `USE_CASE` | 1 | 53 | 0 | 5 | physical-output, sat-multicam |
| `com.nothing.cameracore.context.module.usecaseV2.DualYuvImageCapture` | `USE_CASE` | 1 | 53 | 0 | 4 | physical-output, sat-multicam |
| `com.nothing.camera.offlinealgo.ncf.NcfSimulationBokehMode` | `CLASS` | 3 | 20 | 9 | 20 | vendor-routing-key |
| `com.nothing.camera.pipeline.ncf.mtk.NcfSTRawHdrNode` | `CLASS` | 1 | 13 | 0 | 42 | sat-multicam |
| `com.nothing.camera.pipeline.ncf.qcom.NcfQcomBokehNode` | `CLASS` | 1 | 13 | 0 | 42 | sat-multicam |
| `com.nothing.cameracore.context.module.CameraContext$5` | `CONTEXT` | 1 | 28 | 0 | 25 | session-construction, session-parameters |
| `com.nothing.camera.pipeline.ncf.mtk.NcfBokehNode` | `CLASS` | 1 | 13 | 0 | 40 | sat-multicam |
| `com.nothing.camera.pipeline.ncf.mtk.NcfSingleCaptureNode` | `CLASS` | 1 | 13 | 1 | 39 | sat-multicam |

## Camera open spine

- `APPLICATION_CAMERA_OPEN`: `CameraContext$3.execute(...)`
- `ModuleContext.openCameraAsync(int)`
- `ModuleContext$9.execute(...)`
- `CameraContext.openCamera(int, ConditionVariable)`
- `CameraContext$3.execute(...)`
- `CameraManager.openCamera(String, StateCallback, Handler)`

The machine-readable reference retains the complete bounded static caller paths, including retry and close-then-open command paths.

## Package graph

| Package | Classes | Candidate methods | Roles |
|---|---:|---:|---|
| `androidx.camera.camera2.internal` | 3 | 61 | CLASS:2, INTERFACE:1 |
| `com.sensetime.renderlib` | 3 | 44 | MANAGER:1, CLASS:2 |
| `com.nothing.yuvutils` | 1 | 24 | CLASS:1 |
| `org.tensorflow.lite` | 1 | 24 | CLASS:1 |
| `com.google.android.renderscript` | 1 | 23 | CLASS:1 |
| `com.nothing.common.motion.libyuv.util` | 1 | 22 | NATIVE_BRIDGE:1 |
| `com.arcsoft.imagepp` | 1 | 19 | CLASS:1 |
| `com.nothing.common.setting` | 5 | 16 | CONTEXT:1, CLASS:3, MANAGER:1 |
| `android.hardware.camera2` | 2 | 14 | CLASS:2 |
| `com.nothing.camera.mode` | 4 | 13 | CLASS:4 |
| `com.nothing.camera.pipeline.ncf.mtk` | 8 | 8 | CLASS:8 |
| `com.nothing.camera.pipeline.ncf.qcom` | 6 | 6 | CLASS:6 |
| `com.nothing.cameracore.context.module` | 5 | 4 | CONTEXT:4, CLASS:1 |

## Evidence boundary

- Class edges are resolved DEX invoke references. They do not prove execution on Galaga.
- Callback/executor links that cannot be resolved as direct invokes remain synthetic and separately counted.
- Obfuscation labels are conservative heuristics, not recovered symbol mappings.
- Reflection, Binder, JNI and native-library call graphs remain incomplete until matching runtime/native evidence is captured.

## Reproduction

```bash
python3 tools/apk/build-camera-class-graph.py /private/dex-routing-reports/*.json \
  --output-dir /private/nothing-camera-class-graph
```

The generator consumes normalized per-DEX static routing reports from the controlled analysis workflow. The committed graph binds the exact APK and seven DEX hashes plus aggregate parser counts, so regenerated reports can be checked for drift without redistributing proprietary bytecode.
