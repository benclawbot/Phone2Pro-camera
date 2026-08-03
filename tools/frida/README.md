# Frida Camera-routing Instrumentation

`trace-camera2-routing.js` observes the stock application's Camera2/NDK interactions without modifying requests or bypassing permissions.

Use only on a device and application you are authorized to instrument.

## Purpose

The first objective is to distinguish:

- direct opens of system-only IDs `2`, `3`, `4` or `5`;
- repeated opening of public ID `0` with differing vendor/session metadata;
- Camera2-independent native or Binder configuration.

The script records JSON messages for:

- camera ID enumeration and characteristics queries;
- every `CameraManager.openCamera(...)` overload;
- output physical-camera IDs;
- session parameters;
- capture-request builder writes;
- physical-camera request overrides;
- completed request snapshots;
- session creation and request submission;
- the NDK `ACameraManager_openCamera` symbol when loaded.

It prioritizes routing-relevant metadata but defaults to logging every request key so normalized 0.6×/1×/2× traces can be diffed later.

## Requirements

Attaching to a privileged stock application generally requires one of:

- an authorized rooted/debug device with a matching `frida-server`;
- an engineering/userdebug firmware build;
- an authorized repackaged test APK with Frida Gadget.

The repository does not provide a privilege bypass. Android production restrictions and SELinux policy remain part of the research boundary.

## Basic run

Start Frida server under the authorized test setup, then spawn the stock package:

```bash
mkdir -p traces
frida -U -f com.nothing.camera \
  -l tools/frida/trace-camera2-routing.js \
  --no-pause \
  -o traces/nothing-camera-frida.log
```

Recent Frida versions may resume spawned applications automatically and omit `--no-pause`. Use the syntax supported by the installed Frida release.

To attach to an already running process:

```bash
frida -U -n com.nothing.camera \
  -l tools/frida/trace-camera2-routing.js \
  -o traces/nothing-camera-frida.log
```

The Frida CLI wraps `send()` payloads in its own message envelope. Preserve the raw log and normalize it in a derived artifact rather than editing the original.

## Controlled trace protocol

Create three separate fresh-process runs:

1. Launch Expert mode, select 0.6×, wait for preview stability, capture one image, exit.
2. Force-stop/restart, select 1×, wait, capture one image, exit.
3. Force-stop/restart, select 2×, wait, capture one image, exit.

For every run, also collect:

```bash
adb shell am force-stop com.nothing.camera
adb logcat -c
adb logcat -v epoch > traces/<route>-logcat.txt
adb shell dumpsys media.camera > traces/<route>-camera-before.txt
# perform the controlled route/capture
adb shell dumpsys media.camera > traces/<route>-camera-after.txt
```

Use a separate synchronized collection script or terminal so logcat is stopped cleanly after the scenario.

## High-value records

Inspect these message kinds first:

- `open-camera`
- `set-session-parameters`
- `set-output-physical-id`
- `builder-set-physical-key`
- `create-session`
- `submit-request`
- `ndk-open-camera`

Then diff `builder-set` and `builder-build` records for:

```text
com.mediatek.configure.setting.*
com.mediatek.cameraflex.*
com.mediatek.insensorzoomfeature.*
com.mediatek.seamlessfeature.*
com.mediatek.multicamfeature.*
com.mediatek.streamingfeature.pipDevices
com.mediatek.control.capture.*remosaic*
com.nothing.camera.*
nothing.camera.*
```

## Interpretation

| Trace result | Meaning |
|---|---|
| 0.6× opens `2`, 2× opens `3` | direct system-camera route |
| every route opens `4`, physical/session state changes | system logical/SAT camera |
| every route opens `0`, vendor/session metadata changes | public ID with vendor/SAT routing |
| every route opens `0`, no Camera2 differences | inspect JNI, native libraries and vendor Binder services |
| internal button works but widget trace lacks transition/reopen | exported launch state does not reproduce the internal controller sequence |

## Limitations

- Hook installation can fail when a class or method differs on Android 16; the script emits `hook-unavailable` records rather than silently assuming coverage.
- Vendor wrappers can write metadata below `CaptureRequest.Builder`; native metadata and provider/HAL traces may still be required.
- A Java open hook does not prove which physical sensor produced the final frame. Correlate with EXIF, geometry and field of view.
- Instrumentation can change timing. Repeat each route and compare stable differences only.
