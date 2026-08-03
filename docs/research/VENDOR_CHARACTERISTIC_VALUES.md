# Advertised Vendor Characteristic Values

Status: direct CameraCharacteristics evidence; enum meanings remain unresolved unless stated.

Source artifact: `phone2pro-static-hardware-vendor-20260802_223117_378.json`.

Machine-readable values: `data/vendor-tags/advertised-values.json`.

## Interpretation rule

The values below are the arrays advertised by the target firmware. They establish that the corresponding numeric modes exist in the published metadata surface. They do not establish:

- the semantic name of each numeric value;
- whether an ordinary application may set the related request or session key;
- which combinations are valid;
- whether an accepted value produces an effective pipeline change;
- whether the stock application uses every advertised mode.

Enum names must be recovered from matching MediaTek source, stock-app constants, target native binaries or controlled differential tests.

## Rear ID 0: high-value advertised modes

| Subsystem | Characteristic | Advertised values |
|---|---|---|
| 3D noise reduction | `available3dnrmodes` | `0, 1` |
| photo HDR | `availableHdrModesPhoto` | `0, 1` |
| video HDR | `availableHdrModesVideo` | `0` |
| VHDR | `availableVhdrModes` | `0` |
| multi-stream HDR | `availableMStreamHdrModes` | `0, 6` |
| multi-frame blending | `availablemfbmodes` | `0, 1, 2, 255` |
| AIS | `availableaismodes` | `0, 1` |
| continuous shot | `availableCShotModes` | `0, 1` |
| high-FPS mode | `availableHfpsModes` | `0, 1` |
| ZSL | `available.zsl.modes` | `0, 1` |
| postview | `availablepostviewmodes` | `0, 1` |
| background prerelease | `availableprereleasemodes` | `0, 1` |
| Video AI NR | `videoAinrAvailableModes` | `0, 1` |
| preview compression | `CameraPreviewCompressionModes` | `0, 1` |
| AOV modes | `availableAovModes` | `0, 1` |
| AOV pipeline config | `availablePipelineConfig` | `0, 1` |

The rear metadata advertises an MFB sentinel or special value `255` and multi-stream HDR value `6`. Their meanings are deliberately not guessed here.

## Stream and metadata limits

- High-FPS maximum: `1920 × 1080 @ 60`.
- High-FPS with EIS maximum: `1920 × 1080 @ 60`.
- Slow-motion tuple: `640 × 480 @ 120`, final field `8` unresolved.
- ISP metadata size for RAW: `1920 × 1088`.
- ISP metadata size for YUV: `1280 × 720`.
- AOV image sizes: `640 × 480` and `320 × 240`.
- HDR10+ VSS support: `1`.
- HDR10+ EIS support: `1`.
- Flash calibration and customization are advertised on the rear camera.

## Multicamera feature codes

The rear camera advertises ten multicamera feature values:

```text
983040   0x000F0000
983050   0x000F000A
983046   0x000F0006
983042   0x000F0002
983055   0x000F000F
983062   0x000F0016
917518   0x000E000E
524293   0x00080005
65559    0x00010017
65564    0x0001001C
```

The visible high/low-word structure is a useful reverse-engineering lead, but it is not proof of a bitfield layout or feature taxonomy. These values should be searched verbatim in MediaTek source, decompiled constants and native binaries before assigning names.

## In-sensor zoom clue

`com.mediatek.insensorzoomfeature.insensorzoomIsInternalAP` advertises `[0]` on both public cameras.

Possible interpretations include a false boolean, a mode identifier or a declaration that the public application is not the internal controller. The metadata name makes this key highly relevant to lens routing, but the value cannot be interpreted safely without source or stock traces.

The daylight public-zoom test separately observed `com.nothing.camera.insensorzoom.enable = 0` while the route remained on the main sensor. Together, these results prioritize tracing stock session initialization rather than blindly setting an assumed enable value.

## Front/rear differences

The front camera exposes materially different HDR arrays:

| Characteristic | Rear ID 0 | Front ID 1 |
|---|---|---|
| photo HDR | `0, 1` | `0, 3, 1` |
| video HDR | `0` | `0, 3` |
| VHDR | `0` | `0, 6` |
| continuous shot | `0, 1` | `0` |
| flash calibration available | `1` | `0` |

These differences show that the vendor metadata is camera-specific rather than a single unfiltered global catalogue. They also provide useful enum-recovery anchors: values `3` and `6` can be traced in front-camera stock mode setup and MediaTek source.

## Probe priority

The safest order is:

1. Recover enum definitions from source and stock-app constants.
2. Trace stock request/session writes for a known working mode.
3. Reproduce the complete stream and session configuration without modifying values.
4. Change one evidence-backed value at a time.
5. Compare request acceptance, capture results, effective geometry, image output, latency and logs.
6. Record accepted-but-ineffective values separately from rejected values.

Blind iteration over numeric values is excluded because some keys configure ISP buffers, sensor scenarios or proprietary pipelines and may destabilize the camera service.
