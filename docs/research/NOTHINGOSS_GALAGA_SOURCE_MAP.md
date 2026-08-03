# Official NothingOSS Galaga Source Map

Status: official source repositories and Galaga branches resolved.

Research issue: CAM-092 / #76.

## Official repositories

Nothing publishes the MT6878 kernel stack across separate repositories:

| Component | Official repository | Galaga branches |
|---|---|---|
| GKI/common kernel tree | `NothingOSS/android_kernel_6.1_nothing_mt6878` | `mt6878/Galaga/v`, `mt6878/Galaga/16b` |
| Vendor kernel modules | `NothingOSS/android_kernel_modules_nothing_mt6878` | `mt6878/Galaga/v`, `mt6878/Galaga/16b` |
| Device kernel modules | `NothingOSS/android_kernel_device_modules_6.1_nothing_mt6878` | `mt6878/Galaga/v`, `mt6878/Galaga/16b` |
| Build support | `NothingOSS/android_kernel_build_nothing_mt6878` | default branch; no Galaga-named branch located in the initial pass |

Canonical repository URLs:

- https://github.com/NothingOSS/android_kernel_6.1_nothing_mt6878
- https://github.com/NothingOSS/android_kernel_modules_nothing_mt6878
- https://github.com/NothingOSS/android_kernel_device_modules_6.1_nothing_mt6878
- https://github.com/NothingOSS/android_kernel_build_nothing_mt6878

## Published release mapping

### `mt6878/Galaga/v`

The official kernel README lists the OS 3.2 source releases:

| Published build | Source note |
|---|---|
| `Galaga-V3.2-250425-1517` | First open-source kernel and kernel-modules release |
| `Galaga-V3.2-250526-1427` | No kernel update |
| `Galaga-V3.2-250605-1102` | No kernel update |
| `Galaga-V3.2-250616-1258` | No kernel update |
| `Galaga-V3.2-250715-1813` | No kernel update |
| `Galaga-V3.2-250903-2153` | Merged GKI `android14-6.1-2025-02_r10` |

The README heading says “CMF by NOTHING Phone 1,” while the branch and build names are Galaga. This project records the text verbatim as an upstream naming inconsistency and uses the branch/build identifiers as the reliable scope markers.

### `mt6878/Galaga/16b`

The official kernel README lists the OS 4.x source releases:

| Published build | Source note |
|---|---|
| `Galaga-B4.0-260108-1654` | First open-source kernel and kernel-modules release for this branch |
| `Galaga-B4.0-260226-1122` | No common-kernel update; module README mentions Wi-Fi changes |
| `Galaga-B4.1-260415-1710` | Updated GKI boot to `android14-6.1-2025-09_r6`; module README mentions Wi-Fi changes |

## Baseline-build relationship

The active diagnostic baseline is:

```text
Nothing/GalagaEEA/Galaga:16/BP2A.250605.031.A3/2606151653:user/release-keys
```

It is an Android 16 build dated later than the latest release listed in the `Galaga/16b` README. Therefore:

- `mt6878/Galaga/16b` is the correct official source family to compare first.
- The exact commit corresponding to build token `2606151653` has not yet been established.
- The published repository may lag the installed firmware, or the installed build may contain no kernel changes after the listed source release.
- No exact source equivalence should be claimed until `uname -a`, kernel build ID, module hashes, boot image metadata and Git commit history are correlated.

## Camera-relevant source areas

The device-modules repository contains the MediaTek camera kernel stack, including:

```text
drivers/misc/mediatek/imgsensor/
drivers/misc/mediatek/ccu/
```

High-value areas include:

- image-sensor registration and power sequencing;
- I²C access and sensor feature-control ioctls;
- camera control-unit interfaces;
- actuator, flash, EEPROM and OIS drivers;
- device-tree and project configuration selecting enabled modules;
- ISP6S camera hardware integration.

The generic `imgsensor_sensor_list.c` contains many compile-time sensor candidates. Presence in that file is not evidence that a sensor is enabled on Galaga. The project must resolve actual build configuration, device tree and runtime module binding before naming the physical sensors.

## Source-analysis procedure

1. Pin the exact heads of both Galaga branches in all three repositories.
2. Clone with immutable commit SHAs and record repository object hashes.
3. Diff `Galaga/v` and `Galaga/16b` camera-relevant paths.
4. Identify Galaga build configuration and enabled `IMGSENSOR` macros.
5. Extract camera device-tree nodes, compatible strings, regulators, GPIOs, clocks and I²C addresses.
6. Map sensor, actuator, EEPROM, flash and OIS drivers to runtime module names.
7. Compare runtime `/vendor_dlkm` and `/odm_dlkm` modules with official source outputs.
8. Treat proprietary userspace HAL, ISP tuning and stock-app routing as separate artifacts; the GPL kernel release does not imply that those layers are published.

## Current conclusions

- Official Galaga kernel sources are available and no longer an unresolved discovery item.
- The Android 16 baseline should begin with the `mt6878/Galaga/16b` source family.
- Exact build-to-commit correspondence remains open.
- The source tree supplies valuable hardware and kernel-interface evidence but cannot alone explain CameraService system-camera policy or Nothing Camera's Expert-mode routing.
