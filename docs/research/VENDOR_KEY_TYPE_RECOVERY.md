# Vendor Key Type Recovery

Status: active for CAM-060, CAM-061 and CAM-062.

## Why type recovery is required

A Camera2 vendor key name does not contain enough information to construct a safe request. The same conceptual control may be represented as:

- a single byte, integer or long;
- an array of primitive values;
- a structured byte payload;
- a `Rect`, `Size`, range or another framework type;
- an opaque proprietary metadata blob.

Using the wrong generic or native type can fail before the HAL, be silently rejected, or destabilize the camera service. Therefore, no write probe is permitted until the target type is recovered.

## Evidence order

Use evidence in this order:

1. **Target runtime key object** — recover the Java `TypeReference`, vendor ID, native type and tag from the installed framework key.
2. **Working stock call site** — observe the value passed by Nothing Camera in the correct mode and lifecycle phase.
3. **Target framework/vendor binary** — recover metadata registration tables or symbol-backed type declarations.
4. **Matching official source** — use only when the target build and source revision are demonstrated to match.
5. **Public MediaTek-derived source** — use as a hypothesis or type hint, never as target proof.
6. **Value-shape inference** — last resort and never sufficient for writes.

## Runtime tool

`tools/frida/dump-camera-key-types.js` performs read-only enumeration inside the stock process. It attempts to record:

- key name;
- key Java class;
- underlying `CameraMetadataNative.Key` class;
- Java generic type;
- vendor ID;
- native metadata type;
- metadata tag;
- characteristic value and Java value class;
- the exact type/value used by stock `CaptureRequest.Builder.set()`;
- session-parameter key types and values.

Run:

```bash
frida -U -f com.nothing.camera \
  -l tools/frida/dump-camera-key-types.js \
  -o traces/key-types.log
```

Reflection success depends on the installed framework implementation. A missing private field or hidden method is recorded as missing data, not interpreted as an absent key.

## Current direct target evidence

The static hardware audit establishes the routing-related domains:

- `com.mediatek.configure.setting.initrequest`: request and session;
- `com.mediatek.configure.setting.proprietaryRequest`: request and session;
- `com.mediatek.cameraflex.flexibleCapabilities`: request and session;
- `com.mediatek.streamingfeature.pipDevices`: request and session;
- `com.mediatek.insensorzoomfeature.insensorzoomPhysicalIdsStatus`: request, result and session;
- `com.mediatek.insensorzoomfeature.insensorzoomEnableHints`: request, result and session;
- `com.mediatek.insensorzoomfeature.insensorzoomIsInternalAP`: characteristic, request and session;
- `com.mediatek.seamlessfeature.configCellCropSensorIds`: request and session;
- `com.mediatek.seamlessfeature.configCellFullSensorIds`: request and session;
- `com.mediatek.seamlessfeature.configSensorScenarios`: request and session;
- `com.mediatek.seamlessfeature.sensorScenario`: request and result;
- `com.mediatek.seamlessfeature.forceSensorMode`: request and result.

The audit does not include the exact generic/native types for these keys. Those remain pending runtime recovery.

## External type hint: multicamera feature list

A publicly accessible MediaTek-derived metadata mirror contains an internal tag declaration corresponding to `availableMultiCamFeatureSensorManualUpdated` and associates it with a 64-bit integer metadata type.

Handling rules:

- The source carries a restrictive MediaTek proprietary notice.
- No code or substantial text from that file is copied into this project.
- The observation is recorded only as a low-confidence type hint.
- The target value is represented as ten integers, but array element width still must be verified on the installed phone.
- Runtime reflection or target binary registration remains required before the type becomes verified.

Source locator for reproducibility:

```text
repository: cc-china/MTK_AS_Camera2
commit: 9b3b73174047f0ea8d2f7860813c0a72f37a2d7a
path: camerapostalgo/include/utils/metadata/client/mtk_metadata_tag_info.inl
internal tag: MTK_MULTI_CAM_FEATURE_SENSOR_MANUAL_UPDATED
```

This source is not treated as official MT6878/Galaga source and is excluded from implementation reuse.

## Type verification states

| State | Meaning | Allowed action |
|---|---|---|
| `unknown` | Name/domain only | observe only |
| `shape-observed` | Characteristic/result value class seen | observe only |
| `external-type-hint` | Non-target source proposes a type | observe only |
| `target-runtime-type` | Installed key object reports Java/native type | stock-value trace allowed |
| `stock-value-observed` | Exact type and working stock value captured | isolated reproducer design |
| `write-validated` | Controlled positive/negative test proves effect and recovery | build-specific allowlisted adapter |

## Required route-key output

For every routing candidate, the final record must contain:

```yaml
name: com.mediatek.example.key
javaType: int[]
nativeType: TYPE_INT32
vendorId: 123456789
tag: 0x8ABC0001
domains: [request, session]
stockValues:
  06x: [ ... ]
  1x: [ ... ]
  2x: [ ... ]
applicationPhase:
  - before-session-creation
  - repeating-request
writeValidation:
  status: not-tested
```

Unknown fields remain explicitly unknown. They are not filled from naming conventions or neighbouring MediaTek platforms.
