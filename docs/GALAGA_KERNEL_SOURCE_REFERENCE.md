# Official Galaga kernel source reference

**Index version:** 2026.08.04-1  
**Device:** CMF Phone 2 Pro (`Galaga`, A001, MT6878)  
**Machine-readable index:** [`research/galaga-kernel-source-index.v1.json`](../research/galaga-kernel-source-index.v1.json)

## Provenance and build relation

NothingOSS publishes three official Android 16 Galaga branches:

| Repository ID | Official repository | Branch | Pinned commit | Role |
|---|---|---|---|---|
| `nothing-kernel-6.1-mt6878` | `NothingOSS/android_kernel_6.1_nothing_mt6878` | `mt6878/Galaga/16b` | `6bed54e9d8b14850bb867ccba6607329cd6eaa06` | Base kernel |
| `nothing-kernel-modules-mt6878` | `NothingOSS/android_kernel_modules_nothing_mt6878` | `mt6878/Galaga/16b` | `2866afdd56e09debbe373d919f17bacebcc4b765` | Companion kernel modules |
| `nothing-device-modules-6.1-mt6878` | `NothingOSS/android_kernel_device_modules_6.1_nothing_mt6878` | `mt6878/Galaga/16b` | `2b0af666da693dcf4088b583bae7d77f4a4373e3` | Device modules, device tree, camera-related drivers/configuration |

All three branch heads identify release `Galaga-B4.1-260415-1710` and were committed on 2026-04-22.

The project’s observed diagnostic firmware is:

```text
Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys
```

The official source release is therefore **official but not an exact build match**. It predates the observed `2606151653` build. This index may establish official Galaga topology and source provenance, but it must not be used to claim exact binary/source equivalence for the tested firmware.

## Galaga camera topology

### `galaga-camera-device-tree`

Source: `arch/arm64/boot/dts/mediatek/cust_mt6878_galaga_camera_v4l2.dtsi` at the pinned device-modules commit.

The Galaga camera overlay declares:

- four SENINF CSI ports connected to `sensor0` through `sensor3`;
- project camera regulators, reset/MCLK pins, and EEPROM nodes;
- main and telephoto autofocus endpoints;
- two flash channels and compatible controller candidates;
- enabled image-sensor nodes with candidate driver names.

The declared sensor candidate lists are:

| Device-tree node | Candidate names | Related board role inferred from supplies/endpoints |
|---|---|---|
| `sensor0` | `s5kgn9sp_mipi_raw` | Main route candidate; main AF and main/tele shared AF supply |
| `sensor1` | `gc16b3c2_mipi_raw`, `gc16b3cofilm_mipi_raw` | Front route candidate |
| `sensor2` | `gc08a8_mipi_raw`, `gc08a8xl_mipi_raw` | Ultrawide-labelled supplies |
| `sensor3` | `ov50d40_mipi_raw`, `ov50d40ofilm_mipi_raw` | Telephoto-labelled supplies and tele AF |

These are **device-tree driver candidates**, not proof that every retail unit contains one exact module vendor. Production module identity still requires module/EEPROM/diagnostic evidence for the tested unit.

### `galaga-board-device-tree`

`arch/arm64/boot/dts/mediatek/k6878v1_64_galaga.dts` is the official Galaga board overlay and includes the common MT6878 board source. It establishes device-specific source provenance but is not by itself the complete camera graph.

### Shared MT6878 camera device tree

- `mt6878-base-device-tree`: `arch/arm64/boot/dts/mediatek/mt6878.dts`
- `mt6878-camera-base-device-tree`: `arch/arm64/boot/dts/mediatek/cust_mt6878_camera_v4l2.dtsi`

These files define shared SoC and V4L2 camera infrastructure consumed by project overlays.

## Configuration and camera subsystems

### `mt6878-device-defconfig`

`arch/arm64/configs/mgk_64_k61_defconfig` enables or declares:

- `CONFIG_MTK_IMGSENSOR` and a custom image-sensor driver list containing the Galaga candidate names;
- MediaTek lens and V4L2 lens support;
- MT6878 CAM, CCU, and IMG clocks;
- V4L2 flash and multiple flash-controller drivers;
- camera-related memory, command queue, and platform support.

A configured driver candidate does not establish that the driver is selected at runtime for a specific retail module.

### `device-modules-kconfig-root`

`Kconfig.ext` connects the device-module build to the media and ISP configuration trees.

### `media-platform-kconfig`

`drivers/media/platform/Kconfig` indexes the MediaTek ISP, AI engine, depth engine, codecs, and optional CAMSYS vendor hooks.

### `mtk-isp-kconfig`

`drivers/media/platform/mtk-isp/Kconfig` defines:

- common V4L2/VB2 camera helpers;
- CAMSYS with 3A/tuning, CSI-2 hosting, and simultaneous-camera support;
- HCP communication with a userspace daemon;
- AOV, IMGSYS, IPESYS, CMDQ, and ISP-generation variants;
- camera power/performance scheduling.

The HCP description is an explicit boundary: the open kernel driver expects userspace cooperation, while the exact production Galaga daemon/middleware is not supplied by these kernel repositories.

### `mtk-aie-kconfig`

`drivers/media/platform/mtk-aie/Kconfig` declares a V4L2 memory-to-memory hardware face-detection engine.

### `mtk-dpe-kconfig`

`drivers/media/platform/mtk-dpe/Kconfig` declares depth engines that calculate depth from dual-camera image pairs. Presence in source or configuration does not prove a stock mode uses the engine on Galaga.

### `mtk-image-sensor-kconfig`

`drivers/misc/mediatek/imgsensor/Kconfig` defines MediaTek image-sensor and V4L2 sensor-level driver frameworks plus the custom image-sensor list interface.

## Clock, calibration, PDA, and flash interfaces

### `mt6878-camera-clock-driver`

`drivers/clk/mediatek/clk-mt6878-cam.c` defines camera clock gates for CAM, CAMTG, SENINF, CAMSV, MRAW, RAW/YUV paths, and CCUSYS.

### `mt6878-clock-bindings`

`include/dt-bindings/clock/mt6878-clk.h` defines top-level CAMTG, SENINF, CAM, CCU, IMG, and IPE clock selectors used by device tree and drivers.

### `camera-calibration-format`

`drivers/misc/mediatek/cam_cal/inc/cam_cal_format.h` defines calibration containers and error states for lens shading, 3A gains, PDAF, stereo data, lens/fuse identifiers, and related EEPROM content. It defines formats, not the private production calibration payloads.

### `isp7sp-pda-driver`

`drivers/misc/mediatek/cameraisp/pda/isp_7sp/camera_pda.c` implements PDA hardware integration with CAMSYS registers, DMA buffers, interrupts, MMQoS, runtime power, and clocks.

### Flash drivers

The source set includes:

- `v4l2-flash-lm3644`
- `v4l2-flash-ocp81375`
- `v4l2-flash-sgm37864`

The Galaga DTS lists `sgm37864` and `ocp81375` compatible candidates. The DTS declaration does not prove which compatible device is fitted to every unit.

## Missing userspace and firmware boundary

The three official kernel repositories do **not** supply the complete Android camera stack for the observed firmware. The following remain outside this source index:

| ID | Missing component | Why it matters |
|---|---|---|
| `camera-provider-hal-service` | Exact CameraProvider/HAL service and provider configuration | Maps Android IDs, characteristics, sessions, requests, and results to native/kernel interfaces. |
| `mediatek-camera-middleware` | Proprietary MediaTek camera middleware, feature graphs, tuning control, and userspace daemons | The open HCP driver explicitly expects userspace messaging, but its exact Galaga counterpart is absent. |
| `sensor-tuning-and-calibration-payloads` | Production ISP/sensor tuning and module calibration | Kernel schemas and EEPROM nodes do not contain the private production payloads. |
| `vendor-tags-and-semantics` | Complete Android vendor-tag types, values, dependencies, and effects | Kernel code does not define the safe Android request contract. |
| `stock-camera-controller` | Stock APK mode/controller/request-routing implementation | Required to reproduce stock 0.6×/1×/2× decisions and identity behavior. |
| `isp-ccu-sensor-firmware` | Camera processor and peripheral firmware blobs | Drivers expose interfaces, not every runtime firmware implementation. |
| `exact-build-source-drop` | Source matching build `2606151653` | The official indexed release is `260415-1710`. |

These gaps are linked to the corresponding stock-app, firmware, vendor, provider, and caller-identity issues in the machine-readable index.

## Non-claims

This reference does not claim:

- that a DTS sensor candidate identifies every retail module;
- that kernel source presence proves public Android reachability;
- that an available AIE/DPE/ISP block is used by a specific stock mode;
- that `Galaga-B4.1-260415-1710` exactly matches firmware build `2606151653`;
- that the open repositories constitute a complete Android camera implementation;
- that userspace or vendor behavior can be reproduced without the missing proprietary/build-matched components.

## Update procedure

Update the index when NothingOSS publishes a newer Galaga branch or commit, when an exact source match for the observed build appears, or when camera userspace/firmware artifacts are acquired with provenance.

Run:

```sh
python3 tools/validate-kernel-source-index.py
```

The validator enforces official owner/repository identity, exact 40-character commits, branch/release/build consistency, unique source IDs/paths, explicit build mismatch, userspace-gap issue links, and document coverage of every indexed ID.
