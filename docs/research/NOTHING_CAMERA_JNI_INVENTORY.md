# Nothing Camera JNI and native-library inventory

**Issue:** CAM-030 / #36  
**APK:** `com.nothing.camera` `16.1.01.93.20`  
**APK SHA-256:** `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`

The versioned index is `data/apk/nothing-camera-jni/index.v1.json`. The complete machine-readable inventory is stored as nine ordered base64/zlib chunks. The index records every chunk hash and length plus the decoded JSON hash and length; validation fails before parsing if any byte, order, or file is changed.

## VERIFIED static inventory

The exact APK contains:

- 794 Java native declarations in 90 classes across seven DEX files;
- 69 methods that invoke `System.loadLibrary`;
- 77 packaged `arm64-v8a` ELF libraries;
- 524 exported `Java_*` JNI symbols;
- exact exported-symbol and ELF-offset matches for 501 Java declarations;
- six libraries with `JNI_OnLoad` or `RegisterNatives` indicators;
- no DEX parse errors.

Every native declaration records its Java signature, DEX owner, generated JNI short and long names, priority, ownership status, and exact packaged-library symbol matches where available. Library records include hashes, architecture, build IDs, SONAME, dependencies, JNI export counts, registration indicators and registration-related imports.

The supplemental TSV files expose the library, load-site, native-handle and callback evidence directly for review. The chunked JSON remains the authoritative complete dataset.

## Priority

`HIGH_CAMERA_ROUTING_OR_ISP` highlights declarations whose class, method or signature contains camera, lens, sensor, SAT/multicam, zoom, seamless/remosaic, ISP, RAW, HDR, Night, bokeh, portrait, denoise, super-resolution or stabilization terms. These are first candidates for issues #41, #48 and #49. `MEDIUM_IMAGE_PROCESSING` identifies broader image-processing dependencies.

## Evidence boundaries

- An exported JNI symbol and offset is a static ownership link, not evidence that the method executed on Galaga.
- A method without an exported symbol may use `RegisterNatives`, generated bindings, stripped symbols, reflection, or a firmware-side library.
- Method-local `System.loadLibrary` strings are candidates until an exact packaged-library stem matches.
- Native-handle fields and callback surfaces are naming-based hook points, not proven data flow.
- These 77 libraries are packaged in the application. Provider, HAL and ISP service libraries from `vendor`, `odm`, `system` and `system_ext` remain part of firmware issues #48 and #49.

## Reproduction and validation

The builder produces readable source records from the exact APK. The committed chunked form is reconstructed with the decoder and protected by the index integrity manifest.

```bash
python3 tools/apk/build-nothing-camera-jni-inventory.py /path/to/Camera-16.1.01.93.20.apk /tmp/nothing-camera-jni-readable
python3 tools/decode-nothing-camera-jni-inventory.py --output /tmp/nothing-camera-jni.json
python3 tools/validate-nothing-camera-jni-inventory.py
python3 -m unittest tests/test_validate_nothing_camera_jni_inventory.py
```
