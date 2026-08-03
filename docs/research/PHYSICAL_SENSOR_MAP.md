# Physical Camera Sensor Map

Status: strong source/observation correlation; runtime module identity still requires confirmation.

Sources:

- Target diagnostics from build `Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys`.
- Official NothingOSS `mt6878/Galaga/16b` kernel-module and device-module source.

## Result summary

| Optical route | Observed target output/active geometry | Official Galaga/16b driver with exact geometry | Current confidence |
|---|---|---|---|
| rear main, 24 mm equivalent | 4080 × 3072; 5.56 mm; f/1.879 | Samsung `s5kgn9sp_mipi_raw`: 8160 × 6144 full, 4080 × 3072 binned | strong candidate, C3 |
| rear ultrawide, 15 mm equivalent | 3264 × 2448 stock capture; 1.64 mm | GalaxyCore `gc08a8_mipi_raw`: 3264 × 2448 | strong candidate, C3 |
| rear telephoto, 50 mm equivalent | 4096 × 3072 stock capture; 7.1 mm; f/1.85 | OmniVision `ov50d40_mipi_raw`: 8192 × 6144 full, 4096 × 3072 binned | strong candidate, C3 |
| front | 2320 × 1744 public array; 3.26 mm; f/2 | GalaxyCore `gc16b3c_mipi_raw`: 2320 × 1744 | strong candidate, C3 |

This is not based on product-marketing guesses. Each proposed base sensor appears in the official Galaga/16b compiled image-sensor candidate list and its source driver exposes the same principal frame geometry observed on the target route.

## Rear main: `s5kgn9sp`

Target evidence:

- Public Camera2 ID `0` has a 4080 × 3072 pixel/active array.
- Stock Expert 1× outputs are 4080 × 3072 in landscape orientation.
- Physical focal length is 5.56 mm and the public physical sensor size is 8.16 × 6.14 mm.

Official-source evidence:

- `CONFIG_CUSTOM_KERNEL_IMGSENSOR` on `mt6878/Galaga/16b` includes `s5kgn9sp_mipi_raw` and an additional supplier/module variant `s5kgn9spofxian_mipi_raw`.
- The `s5kgn9sp` driver declares a full 8160 × 6144 array and standard preview/capture output of exactly 4080 × 3072.
- Its PDAF metadata also declares `i4FullRawW = 4080` and `i4FullRawH = 3072` for the binned path.

Discriminator:

- The same source family also compiles IMX882 candidates, but the inspected `imx882_mipi_raw` driver uses a 4000 × 3000 preview/capture path after cropping from the 8192 × 6144 sensor. That does not match the target's exact 4080 × 3072 public geometry as closely as `s5kgn9sp`.

Current conclusion:

- `s5kgn9sp` is the leading base-silicon mapping for the rear main camera.
- The exact supplier/module variant and runtime driver string remain unconfirmed.

## Rear ultrawide: `gc08a8`

Target evidence:

- The stock Expert 0.6× capture is 3264 × 2448 in landscape orientation.
- EXIF reports 1.64 mm physical focal length and 15 mm equivalent with digital zoom zero.

Official-source evidence:

- Galaga/16b compiles `gc08a8_mipi_raw`, `gc08a8xl_mipi_raw` and `gc08a8syx_mipi_raw` candidates.
- The base `gc08a8` driver declares 3264 × 2448 as its full, preview and capture geometry.
- The driver does not advertise PDAF in the inspected base implementation, which is plausible for the fixed-focus ultrawide role but is not independently decisive.

Current conclusion:

- `gc08a8` is the leading base-silicon mapping for the ultrawide camera.
- Supplier/module suffix remains unresolved.

## Rear telephoto: `ov50d40`

Target evidence:

- The stock Expert 2× capture is 4096 × 3072 in landscape orientation.
- EXIF reports 7.1 mm physical focal length, 50 mm equivalent, f/1.85 and digital zoom zero.

Official-source evidence:

- Galaga/16b compiles `ov50d40_mipi_raw` and `ov50d40ofilm_mipi_raw` candidates.
- The base `ov50d40` driver declares an 8192 × 6144 full array and exactly 4096 × 3072 preview/capture output.
- Its inspected preview/capture path exposes PDAF and 30 fps operation.

Current conclusion:

- `ov50d40` is the leading base-silicon mapping for the 2× telephoto camera.
- The exact module supplier variant remains unresolved.

## Front camera: `gc16b3c`

Target evidence:

- Public front Camera2 ID `1` has a 2320 × 1744 pixel/active array.
- It advertises 3.26 mm focal length and f/2.

Official-source evidence:

- Galaga/16b compiles several `gc16b3c` module variants.
- The base driver declares exactly 2320 × 1744 preview/capture geometry.

Current conclusion:

- `gc16b3c` is the leading base-silicon mapping for the front camera.

## System camera ID relationship

Direct target probing establishes that IDs `2`, `3`, `4` and `5` are recognized system-only camera devices. Existing stock-app routing analysis proposes:

| System ID | Proposed role | Confidence |
|---|---|---|
| `2` | ultrawide / `gc08a8` route | C2; ID mapping not yet dynamically observed |
| `3` | telephoto / `ov50d40` route | C2; ID mapping not yet dynamically observed |
| `4` | rear SAT/logical composite | C1; unresolved |
| `5` | portrait or another composite route | C1; unresolved |

The sensor-family correlations are stronger than the numeric ID assignments. The project must not merge these into a single certainty level.

## Why this is not yet C4

The official defconfig is a compiled candidate set shared by the source family. A driver can be built but absent from a particular device assembly. Exact confirmation requires at least one of:

- readable runtime image-sensor binding or kernel log;
- Galaga production device-tree/DTBO node with the selected module string;
- EEPROM/module identification output;
- stock HAL static metadata naming the sensor;
- target module strings extracted from the installed kernel modules;
- privileged characteristics/provider metadata correlated to IDs `2`–`5`.

## Immediate validation probes

1. Collect the new read-only device bundle from `tools/device/collect-camera-platform.sh`.
2. Add `dmesg`/logcat image-sensor probe output when available under an authorized debug context.
3. Extract and decompile the installed DTB/DTBO and search `sensor-names`.
4. Inspect `/sys` and `/proc` camera module-information nodes exposed by Nothing OEM drivers.
5. Compare camera EEPROM/module strings against the supplier-suffixed driver variants.
6. Hook stock `openCamera()` to establish the exact system ID used by each optical route.
