# Nothing Camera vendor-key static call-site map

**Issue:** CAM-029 / #35  
**APK:** Nothing Camera `16.1.01.93.20`  
**APK SHA-256:** `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`

The complete coverage map is `data/vendor-tags/callsites/coverage.v1.json`. It partitions every one of the 162 device-observed MediaTek/Nothing keys into six exact stock-DEX references and 156 keys with no exact literal or resolved field reference. Directions remain authoritative in `data/vendor-tags/inventory.json`; advertised characteristic values remain in `data/vendor-tags/advertised-values.json`.

## Resolved static keys

| Key | Binding | Stock use |
|---|---|---|
| `com.mediatek.configure.setting.initrequest` | available-session-key lookup → `mQuickPreviewKey` | quick-preview configuration |
| `com.mediatek.control.capture.flipmode` | `CaptureRequest.Key<int[]>` → `sMTKFlipKey` | setting writer, MediaTek capture engines, HAL JPEG result reader |
| `com.mediatek.control.capture.zsl.mode` | available-session-key lookup → `mKeyZslMode` | session lookup, accessor and support condition |
| `com.mediatek.hdrfeature.hdrMode` | `CaptureRequest.Key<Integer>` → `MTK_ENABLE_SHDR` | shared request writer |
| `com.mediatek.streamingfeature.hfpsMode` | `CaptureRequest.Key<Integer>` → `MTK_STREAMING_FEATURE_HFPS_MODE` | video output/session request writers and snapshot condition |
| `com.nothing.camera.eis.supereismode` | `CaptureRequest.Key<Integer>` → `NT_SUPER_EIS_ENABLE` | shared request writer |

The exact 35 static evidence events across 18 methods are in `research/apk/vendor-key-callsite-referenced.v1.json`. All seven DEX hashes and the scan scope are in `research/apk/vendor-key-callsite-scan.v1.json`.

## Evidence boundary

`NO_EXACT_STATIC_REFERENCE` does not mean unused. Reflection, dynamically assembled names, JNI/native use, firmware-side metadata and missing split APKs remain outside DEX proof. Method roles identify static code capability and do not establish that a branch executed on Galaga.

## Reproduction

```bash
python3 tools/apk/build-vendor-key-callsite-map.py
python3 tools/validate-vendor-key-callsite-map.py
python3 -m unittest tests/test_validate_vendor_key_callsite_map.py
```

A new APK, split, native-library recovery or runtime trace must add versioned evidence rather than silently changing this reference.
