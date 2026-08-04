# Nothing Camera Galaga application configuration

**Issue:** CAM-023 / #29  
**APK:** `com.nothing.camera` `16.1.01.93.20`  
**APK SHA-256:** `f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea`  
**Build scope:** `nothing-galaga-eea-android16-2606151653-f88325f3`

The machine-readable index is `data/apk/nothing-camera-galaga-config/index.v1.json`.

## VERIFIED — exact APK static configuration

The package contains a dedicated `ConfigMapGalaga` selected from `ro.product.device`. Its static initializer defines 223 unique entries. Every entry has a value, inferred value type, code-unit offset, literal-reference count and ProductConfig-link status in `entries.v1.tsv`.

The stock parser reads eight product/region properties, selects the product map, composes platform boolean decisions first, copies remaining product values second, and falls back to the caller-supplied typed default only when no final string exists. A `/sdcard/dev_camera_feature.xml` override parser exists, but no caller was found in the seven DEX files.

Two bundled XML assets contain 23 feature records. They are inventoried and hashed in `assets.v1.json`. The bundled development XML is a template and is not proof that the on-device override path is used.

### Focal labels

The dedicated Galaga focal builder defines these display-equivalent values:

| Zoom | Rear equivalent | Zoom | Front equivalent |
|---:|---:|---:|---:|
| 0.6× | 15 mm | 1.0× | 22 mm |
| 1.0× | 24 mm | 1.2× | 27 mm |
| 2.0× | 50 mm |  |  |
| 3.0× | 70 mm |  |  |
| 4.0× | 100 mm |  |  |
| 5.0× | 120 mm |  |  |
| 6.0× | 140 mm |  |  |
| 10.0× | 240 mm |  |  |
| 30.0× | 700 mm |  |  |

These are UI/configuration labels, not measured optical focal lengths.

### Unconditional stock route tables

| Mode | Zoom region | Configured camera ID |
|---|---|---:|
| Manual | `[0.6,1)` | `2` |
| Manual | `[1,2)` | `0` |
| Manual | `[2,10]` | `3` |
| Night | `[0.6,10]` | `4` |
| Bokeh | `[1,4]` | `5` |
| Slow motion | `[1,2]` | `0` |
| Third-party | `[1,10]` | `0` |

Photo, video and time-lapse use dedicated conditional builders. They are linked by method and code offset rather than flattened into one unconditional route, because their output depends on preferences and reported capabilities.

The Galaga zoom slider defines damping points at `0.6, 1, 2, 3, 4, 5, 6, 10, 20`, focal buttons at `0.6, 1, 2`, and five divider regions.

### Selected Galaga defaults

The full table is machine-readable. Important values include:

- general SAT enabled;
- video SAT enabled;
- 4K60 SAT disabled;
- video SAT restricted to 1080p30 enabled;
- maximum configured zoom `20`;
- night-display maximum zoom `4.0`;
- bokeh default zoom `2`;
- rear default focal label `24mm`;
- wide focal label `15mm`;
- super resolution enabled, RAW super resolution disabled.

## PARTIALLY VERIFIED — consumers and selection

Static DEX evidence links the Galaga selector to `FeatureConfigParser`, ProductConfig, the Galaga EV/flash/resolution-FPS/zoom widget strategy factories, focal builders, zoom builders and a night feature request consumer. Literal reference counts are retained for all 223 keys; the highest-signal direct consumers are listed in `routes.v1.json`.

This proves packaged stock-code configuration and candidate routing. It does not prove that a route opened successfully, that CameraService authorized it, or that the corresponding physical sensor produced frames.

## UNKNOWN — firmware overlays and sensor scenarios

No exact `sensorScenario`/scenario literal or method name was found in the seven APK DEX files. Provider-side sensor scenarios, firmware overlays, native camera services and HAL/ISP configuration therefore remain unknown at this layer and are linked to #26, #48 and #49.

The matching public firmware release is `Galaga_B4.1-260615-1653`, fingerprint build `2606151653`, with boot, firmware, logical-image and checksum assets. Those partition bytes must be inspected before firmware-derived values are promoted.

## Validation

```bash
python3 tools/validate-nothing-camera-galaga-configuration.py
python3 -m unittest tests/test_validate_nothing_camera_galaga_configuration.py
```

The validator rejects entry loss, required-value drift, focal-map drift, camera-route drift and any promotion of the sensor-scenario boundary to verified runtime evidence.
