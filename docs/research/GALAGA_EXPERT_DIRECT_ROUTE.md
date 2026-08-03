# Galaga Expert/manual direct camera route

Status: static route recovered from Nothing Camera `16.1.01.93.20`.

Analyzed artifact:

```text
Camera-16.1.01.93.20.apk
SHA-256 f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea
DEX files classes.dex through classes7.dex
```

The extraction is reproducible with:

```bash
python3 tools/apk/extract-galaga-manual-route.py \
  /private/path/Camera-16.1.01.93.20.apk \
  --json /private/output/galaga-manual-route.json \
  --markdown /private/output/galaga-manual-route.md
```

The tool performs narrow constant propagation over DEX instructions. It does
not reconstruct or copy proprietary source code.

## VERIFIED

### Product-specific builder selection

The stock APK defines product enum `P24121` with codename `Galaga` and product
number `24121`. `ZoomConfigBuilderFactory.getZoomConfigBuilder()` tests that
product enum and selects `ProductGalagaZoomConfigBuilder`.

### Manual route table

`ProductGalagaZoomConfigBuilder.addManualZoomConfig()` sets maximum manual zoom
to `10` and installs the following route table:

| Requested zoom region | Integer camera endpoint | Project route |
|---|---:|---|
| `[0.6,1)` | `2` | `UltraWide` |
| `[1,2)` | `0` | `Wide` |
| `[2,10]` | `3` | `Telephoto` |

This is a direct camera-endpoint table, not a table containing SAT ID `4` or a
single public endpoint plus only crop ratios.

### Selection and framework-open path

Static bytecode also establishes the relevant selection and open stages:

```text
ProductGalagaZoomConfigBuilder.addManualZoomConfig()
  -> ZoomConfigItem.getCameraIdByZoomValue(float)
  -> CameraBottomFunctionUINode.updateZoomValue(float, boolean)
  -> UiEventProxy.switchCameraDirect(int)
  -> pref_camera_id_key
  -> SettingContext.handleCameraIdChangedForDirectSwitch(String, boolean)
  -> SettingContext.setCameraId(int)
  -> ModuleContext.openCameraAsync(int)
  -> ModuleContext$9.execute(Object[])
  -> CameraContext.openCamera(int, ConditionVariable)
  -> CameraContext$3.execute(Object[])
  -> String.valueOf(int)
  -> CameraManager.openCamera(String, StateCallback, Handler)
```

The final application-owned dispatch converts an integer endpoint to its string
form immediately before `CameraManager.openCamera`.

## PARTIALLY VERIFIED

The recovered mapping agrees with the project’s controlled Expert captures:

| Expert control | Observed physical focal length | Recovered endpoint |
|---|---:|---:|
| 0.6× / 15 mm equivalent | 1.64 mm | `2` |
| 1× / 24 mm equivalent | 5.56 mm | `0` |
| 2× / 50 mm equivalent | 7.10 mm | `3` |

The agreement between independently observed optical output and the APK’s
Galaga-specific route table strongly identifies direct endpoint selection as
the primary manual/Expert lens selector. It is not a substitute for a fresh
runtime trace proving every method and endpoint value on the tested firmware.

## UNKNOWN

Static APK analysis does not yet establish:

- which package signature, UID, permission or SELinux policy allows the stock
  application to open system camera endpoints `2` and `3`;
- whether endpoint-specific session parameters are additionally required for
  stable preview, manual controls, capture or tuning;
- whether the HAL performs further physical-sensor configuration after the
  direct endpoint is opened;
- whether this route table is reused unchanged by every Expert submode.

## Engineering consequence

The earlier four-way routing hypothesis is narrowed for Galaga manual mode:

1. **Direct opening of IDs `2`, `0` and `3`: VERIFIED as static stock
   configuration; PARTIALLY VERIFIED as runtime behaviour.**
2. **SAT logical ID `4`: not the endpoint in the recovered manual route table.**
   It remains relevant to other stock modes and automatic zoom paths.
3. **Public ID `0` plus privileged MediaTek session parameters: not the primary
   selector in this manual table.** Additional parameters may still supplement
   direct opens.
4. **HAL-only routing after a fixed endpoint: not sufficient to explain the
   recovered manual table.** Additional HAL work remains possible after open.

The next implementation target is therefore a privileged auxiliary backend
whose route resolver maps `UltraWide`, `Wide` and `Telephoto` to discovered
endpoints through a capability record, while keeping the privilege mechanism
and any required session parameters independently testable.
