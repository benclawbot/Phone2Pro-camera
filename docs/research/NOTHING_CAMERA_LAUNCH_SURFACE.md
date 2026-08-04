# Nothing Camera launch, widget, shortcut and restoration map

**Issue:** CAM-027 / #33  
**APK:** `com.nothing.camera` `16.1.01.93.20`  
**APK SHA-256:** `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`

The machine-readable index is `data/apk/nothing-camera-launch-surface/index.v1.json`.

## VERIFIED — manifest launch surface

Fourteen first-party launch/configuration components participate in camera, widget or preset flows; twelve are explicitly exported. `CameraActivity` accepts main/widget, image-capture, video-capture and Bluetooth-open actions. Voice and secure wrappers accept the corresponding public, voice and secure actions and retarget or delegate into `CameraActivity`.

`CameraShortCutActivity` declares `android.media.action.SHORTCUT_CAMERA` but is explicitly **not exported**. It is an owning-package remapper: it forwards its intent to `CameraActivity`. Exported preset/settings activities with DEFAULT-only filters have no named public action contract.

The Nothing card provider is exported for `android.nothing.action.APPCARD_UPDATE`. Its card resource configures `CameraPresetWidgetActivity` and supports 1×1 through 2×2 placement.

## VERIFIED — static launcher shortcuts

The binary shortcut resource `res/fQ.xml` defines:

| Shortcut | Facing | Submode | Target |
|---|---:|---|---|
| `backvideo` | `1` | `video` | non-exported `CameraShortCutActivity` |
| `portraitcamera` | `0` | `bokeh` | non-exported `CameraShortCutActivity` |
| `selfiephoto` | `1` | — | non-exported `CameraShortCutActivity` |

All use `android.media.action.SHORTCUT_CAMERA` and are package-owned launcher entries, not a general external API.

## VERIFIED — parser and consumer chain

The exact DEX contains 126 literal call sites for 58 launch/state keys. Every key is mapped in `parameters.v1.tsv` to its API, method, DEX and code offset. `routes.v1.json` links each key to its normalization and consumer.

The main chain is:

1. activity, voice, secure or shortcut wrapper normalizes the incoming intent;
2. `CameraActivity.onNewIntent` reconciles new/old widget IDs, modes and facing;
3. `CameraScheduler.onNewIntent` dispatches to `SettingContext`, `CameraUI` and `ModuleContext`;
4. `LaunchIntentParser` resolves public mode/facing, Assistant and `CAMERA_PREFIX_*` parameters;
5. setting checks constrain flash, HDR, ratio, timer, filter, beauty, video size/FPS and other values;
6. `ModuleContext.onNewIntent` converts focal text through product focal/zoom tables and calls `FeatureManager.setZoomRatio`.

The 37 widget-prefix parameters cover focal length, EV, RAW, motion photo, action mode, watermark fields, grid, photo/video HDR, ratio, resolution/FPS, slow motion, time lapse, flash, timer, filter/strength, retouching, bokeh, portrait, speed, quality, color mode, facula, global exposure, facing, mode/submode and widget identity.

A focal label is therefore not a direct endpoint command. It is parsed, converted to zoom, checked against mode/SAT/facing state and then consumed by the active module.

## VERIFIED — widget and preset state

Widget configuration requires `widget_id`; `-1` is rejected. Per-widget data uses `PRESET_SHORT_WIDGET_<widgetId>` with keys including `PRST_ID`, `S_MOD`, `F_VAL`, `PRST_N_LBL`, `PRT_NAME` and `CVR_BMP_CLR`. Changes notify `CameraWidgetManager.onConfigChanged`.

Preset order is stored under `camera_preset_list`, the default under `camera_default_preset`, and records under `camera_preset_<id>`. `PresetDataParser.mapPresetKey/mapPresetValue` materializes preset values as `CAMERA_PREFIX_*` extras before the normal launch parser consumes them.

During backup restore, `CameraBackUpAgent` sets `camera_restore_in_progress=true` for preset/widget files, validates and saves restored presets, then clears the flag. `CameraWidgetProvider` reads the flag before serving update requests.

On a hot `MAIN` intent without a fresh widget ID, `CameraActivity.onNewIntent` can restore the previous `CAMERA_PREFIX_FLAG_WIDGET` into the new intent before scheduler dispatch.

## VERIFIED comparison; runtime boundary retained

On the audited Galaga build, external widget focal launches requesting 15 mm, 24 mm and 50 mm all remained on the 5.56 mm physical / 24 mm-equivalent main route. Internal Expert controls produced distinct 15/24/50 mm-equivalent outputs and the static route table maps them to IDs 2/0/3.

This establishes an external-to-internal behavior mismatch: the extras are real and parsed, but the tested external path did not reproduce internal Expert endpoint selection. It does not prove that every external route always falls back, nor does manifest export prove CameraService authorization.

## Validation

```bash
python3 tools/validate-nothing-camera-launch-surface.py
python3 -m unittest tests/test_validate_nothing_camera_launch_surface.py
```
