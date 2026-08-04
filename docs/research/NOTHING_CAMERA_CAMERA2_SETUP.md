# Nothing Camera Camera2 setup reconstruction

**Issue:** CAM-028 / #34  
**APK:** `com.nothing.camera` `16.1.01.93.20`  
**APK SHA-256:** `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`

The machine-readable index is `data/apk/nothing-camera-camera2-setup/index.v1.json`.

## VERIFIED static setup order

The exact APK contains 357 direct Camera2/session/output/request operations across 252 first-party methods. The canonical setup order is:

1. acquire the camera-open semaphore for up to 3 seconds, optionally wait 500 ms for the mode-open condition, then call `CameraManager.openCamera(String.valueOf(id), callback, null)`;
2. ask the active submode to create its preview request builder;
3. apply session keys before session creation;
4. collect output configurations, session request, optional input configuration and session type, then create the session;
5. apply ordinary preview keys after session creation has been dispatched;
6. accept the configured session only if the module and camera state are still current;
7. configure/finalize the preview surface and submit repeating preview;
8. on preference changes, reapply setting and feature modifiers before resubmitting repeating preview;
9. create still requests with template 2, add mode targets/modifiers and submit a single request or burst;
10. reprocessing creates a request from a prior `TotalCaptureResult` and requires an input path.

An existing session is aborted before replacement. Session-key caching retains only keys advertised by `CameraCharacteristics` as available session keys, and those cached keys can be copied into later builders.

## Session variants

The primary path creates `SessionConfiguration(type, outputs, executor, stateCallback)`, installs the built preview request as session parameters, conditionally installs `InputConfiguration`, and calls `CameraDevice.createCaptureSession(SessionConfiguration)`.

A special internal type `-2` is translated to session type `2` and uses an input configuration. A separate compatibility path calls `createCaptureSessionByOutputConfigurations`. The exact meaning and runtime availability of hidden/proxy session types is not promoted beyond the static branch.

Deferred preview configurations are supported: an `OutputConfiguration` may be created from size/class, a concrete surface is added later, and `finalizeOutputConfigurations` is called after the preview `SurfaceTexture` exists.

## Mode and lens differences

| Family | Preview | Capture/session difference |
|---|---|---|
| Photo | template 1 | template 2 still; JPEG/YUV/RAW readers; ZSL and MTK quick-preview gates |
| Video | template 3 | recorder/codec output; quality, FPS, HDR/night and stabilization session rules |
| Dual/physical | mode template | physical IDs on outputs and request physical-ID sets; dual YUV/RAW combinations |
| Bokeh | base or dual preview | physical IDs selected from zoom; targets change for normal, night, HDR/MFNR paths |
| Night/HDR reprocess | template 1 | input configuration plus reprocess request from capture result |
| Slow motion | high-speed/record | high-speed request list and `setRepeatingBurst` |

Twelve methods assign `OutputConfiguration.setPhysicalCameraId`, and twelve methods create a request with an explicit physical-ID set. This proves stock logical-multi-camera plumbing, not public authorization for those physical endpoints.

## Request modifier layers

Session settings are applied first. Preview settings are then layered with feature managers for AE/AF/AWB, face detection and zoom. Still capture adds mode-specific modifiers, including MFNR, ZSL/remosaic/night state and target changes. The complete direct-call inventory is stored as two integrity-checked `operations-*.b64part` chunks containing base64-encoded gzip TSV data.

## Minimal public equivalent

A clean-room public implementation can reproduce the ordinary public main-camera path:

```java
cameraManager.openCamera(publicCameraId, deviceCallback, cameraHandler);

CaptureRequest.Builder preview = device.createCaptureRequest(
        CameraDevice.TEMPLATE_PREVIEW);
preview.addTarget(previewSurface);

ImageReader jpeg = ImageReader.newInstance(width, height,
        ImageFormat.JPEG, 2);
List<OutputConfiguration> outputs = List.of(
        new OutputConfiguration(previewSurface),
        new OutputConfiguration(jpeg.getSurface()));

SessionConfiguration config = new SessionConfiguration(
        SessionConfiguration.SESSION_REGULAR,
        outputs,
        cameraExecutor,
        sessionCallback);
config.setSessionParameters(preview.build());
device.createCaptureSession(config);

// onConfigured
session.setRepeatingRequest(preview.build(), previewCallback, cameraHandler);

CaptureRequest.Builder still = device.createCaptureRequest(
        CameraDevice.TEMPLATE_STILL_CAPTURE);
still.addTarget(jpeg.getSurface());
session.capture(still.build(), stillCallback, cameraHandler);
```

Only public keys reported by `CameraCharacteristics` should be copied. This intentionally excludes Nothing/MediaTek vendor tags, hidden `ProxySession` APIs, inaccessible physical IDs and proprietary post-processing; it is not stock feature parity.

## Evidence boundary

This is a complete static direct-API reconstruction for the exact APK. It does not prove runtime stream-combination acceptance, physical-camera authorization, HAL sensor-scenario selection or proprietary processing execution.

## Validation

```bash
python3 tools/validate-nothing-camera-camera2-setup.py
python3 -m unittest tests/test_validate_nothing_camera_camera2_setup.py
```
