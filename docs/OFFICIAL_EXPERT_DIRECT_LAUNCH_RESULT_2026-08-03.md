# Official Expert direct-launch result and widget focal follow-up

Date: 2026-08-03

## v0.5.0 observed result

The v0.5.0 diagnostics application launched the exported Nothing Camera activity while requesting the internally mapped rear-camera IDs `2`, `0`, and `3`. The official Expert interface stayed on the `1×` route instead of opening the expected ultrawide, main, and telephoto routes.

This is a useful negative result rather than evidence that the internal ID mapping was wrong. The mapping remains independently confirmed by Nothing's Galaga configuration and the earlier Expert-mode EXIF captures:

- ID `2` — ultrawide, 1.64 mm / 15 mm equivalent.
- ID `0` — main, 5.56 mm / 24 mm equivalent.
- ID `3` — telephoto, 7.10 mm / 50 mm equivalent.

## Why direct IDs stayed at 1×

Static inspection of `LaunchIntentParser.tryToGetIntentCameraId()` explains the behaviour. On a device where SAT is enabled, ordinary externally supplied rear physical IDs are normalized to the configured SAT/logical camera ID before the mode is opened. On Galaga that SAT endpoint is system-only ID `4`.

Therefore, supplying `2`, `0`, or `3` through the tested `CAMERA_FACING` intent fields does not directly select those physical cameras. The exported activity opens the SAT route, and Expert/manual mode starts at its default or persisted `1×` state.

The direct-ID launch contract is consequently not a viable automatic lens-selection mechanism for an ordinary application.

## Separate Nothing Camera widget preset path

The official APK contains a second exported launch path used by Nothing Camera's own widgets and presets. It first opens a rear route and then applies a focal-length preset through `LaunchIntentParser.parseWidgetParam()`.

The v0.6.0 diagnostic exercises this contract with:

- Action: `com.nothing.camera.WIDGET_CAMERA`
- Activity: `com.nothing.camera.activity.CameraActivity`
- `com.nothing.camera.WIDGET_CAMERA = true`
- `com.nothing.camera.IS_FROM_WIDGET = true`
- `android.intent.extras.CAMERA_PREFIX_FLAG_WIDGET = "preset-1"`
- `android.intent.extras.CAMERA_PREFIX_MAIN_MODE = "photo"`
- `android.intent.extras.CAMERA_PREFIX_SUB_MODE = "manual"`
- `android.intent.extras.CAMERA_PREFIX_FACING = "0"`
- `android.intent.extras.CAMERA_PREFIX_FOCALLENGTH_VALUE` set separately to `15mm`, `24mm`, and `50mm`

The Galaga focal configuration maps those values to:

| Preset | Expected optical route | Expected internal ID | Expected EXIF |
|---|---|---:|---|
| `15mm` | 0.6× ultrawide | `2` | 1.64 mm / 15 mm equivalent |
| `24mm` | 1× main | `0` | 5.56 mm / 24 mm equivalent |
| `50mm` | 2× telephoto | `3` | 7.10 mm / 50 mm equivalent |

For manual mode, the widget parser contains focal-ratio logic that selects the wide route below 1×, the main route at 1×, and the telephoto route at or above the configured tele anchor. This happens after the ordinary rear-ID normalization that defeated the v0.5.0 test.

## Validation decision

The widget focal contract is the final low-risk exported-activity route worth testing. Its result has two possible interpretations:

1. If all three EXIF signatures match, an ordinary application can automatically hand off to the privileged stock camera on a chosen physical lens.
2. If the camera remains at 1× or otherwise ignores the focal values, the widget/preset path is restricted, sanitized, or dependent on internal state unavailable to third-party callers. Automatic stock-camera lens handoff should then be considered closed for this firmware.

## Boundary even on success

A successful widget-preset launch would not grant Camera2 ownership of IDs `2`, `3`, or `4`. Nothing Camera would still own the privileged session and perform capture internally. The calling application could associate and process only the saved output after return; it would not receive raw preview frames, burst frames, private `CaptureResult` metadata, or direct access to the ultrawide and telephoto sensors.
