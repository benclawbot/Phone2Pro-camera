# Galaga camera hardware and driver map

**Index version:** 2026.08.04-1  
**Target:** CMF Phone 2 Pro (`A001`, `Galaga`, MT6878)  
**Observed build:** `2606151653`  
**Issue:** CAM-057 / #52

## Evidence scope

The map uses the official NothingOSS Galaga source release `B4.1-260415-1710`:

- kernel `6bed54e9d8b14850bb867ccba6607329cd6eaa06`;
- kernel modules `2866afdd56e09debbe373d919f17bacebcc4b765`;
- device modules `2b0af666da693dcf4088b583bae7d77f4a4373e3`.

This is direct Galaga source, but it predates the observed `2606151653` build. The map therefore separates source-confirmed topology from exact-build and runtime identity.

Machine-readable source: `data/hardware/galaga-camera-hardware-map.v1.json`.

## Physical routes

### Front — `sensor1`

- I²C: `i2c4`, 1 MHz, address `0x10`.
- Source candidates: `gc16b3c2_mipi_raw`, `gc16b3cofilm_mipi_raw`.
- CSI: port 0, `csi_efuse0`, `dphy-settle-delay-dt = 17`.
- MCLK: GPIO 96 / `CMMCLK4` / `CLK_TOP_CAMTG5_SEL`.
- Reset: GPIO 24.
- Rails: `ldo_avdd_front`, `ldo_dvdd_front`, shared `camera_common_dovdd`.
- EEPROM: `i2c4@0x50`.
- AF/OIS: no actuator or OIS node is evidenced.

The exact retail front module remains unknown.

### Main — `sensor0`

- I²C: `i2c8`, 1 MHz, address `0x2d`.
- Source candidate: `s5kgn9sp_mipi_raw`.
- CSI: port 1, `csi_efuse1`, `hs-trail-parameter = 0x20`.
- MCLK: GPIO 93 / `CMMCLK1` / `CLK_TOP_CAMTG2_SEL`.
- Reset: GPIO 25.
- Rails: `ldo_avdd_m`, `ldo_dvdd_m`, shared `camera_common_dovdd`, shared `ldo_afvdd_m_tele`.
- EEPROM: `i2c8@0x50`.
- AF: `mediatek,pd9302a` at `i2c8@0x0c`.
- OIS: no node or binding is evidenced.
- Runtime optical route: 5.56 mm physical / 24 mm equivalent in stock Expert evidence.

The DTS selects one sensor family, but build-matched sensor ID/module-vendor confirmation is still required.

### Ultrawide — `sensor2`

- I²C: `i2c7`, 1 MHz, address `0x31`.
- Source candidates: `gc08a8_mipi_raw`, `gc08a8xl_mipi_raw`.
- CSI: port 2, `csi_efuse2`, `hs-trail-parameter = 0x20`.
- MCLK: GPIO 94 / `CMMCLK2` / `CLK_TOP_CAMTG3_SEL`.
- Reset: GPIO 26.
- Rails: `ldo_avdd_uw`, `ldo_dvdd_uw`, shared `camera_common_dovdd`.
- EEPROM: `i2c7@0x50`.
- AF/OIS: no actuator or OIS node is evidenced.
- Runtime optical route: 1.64 mm physical / 15 mm equivalent in stock Expert evidence.

### Telephoto — `sensor3`

- I²C: `i2c9`, 1 MHz, address `0x36`.
- Source candidates: `ov50d40_mipi_raw`, `ov50d40ofilm_mipi_raw`.
- CSI: port 3, `csi_efuse3`, `hs-trail-parameter = 0x20`.
- MCLK: GPIO 95 / `CMMCLK3` / `CLK_TOP_CAMTG4_SEL`.
- Reset: GPIO 27.
- Rails: fixed `camera_tele_avdd`, `ldo_dvdd_tele`, shared `camera_common_dovdd`, shared `ldo_afvdd_m_tele`.
- EEPROM: `i2c9@0x58`.
- AF: `mediatek,cn3968` at `i2c9@0x0c`.
- OIS: no node or binding is evidenced.
- Runtime optical route: 7.1 mm physical / 50 mm equivalent in stock Expert evidence.

The tele actuator compatible is direct device-tree evidence, but a matching source driver was not located in the three indexed official repositories.

## Power and GPIO topology

### Shared digital I/O rail

`camera-common-dovdd` is a fixed 1.8 V regulator enabled by GPIO 23 and feeds all four sensors.

### Telephoto analogue rail

`camera-tele-avdd` is a fixed 2.8 V regulator enabled by GPIO 129 and feeds telephoto AVDD.

### Front/ultrawide regulator IC

`i2c3@0x28` is compatible with ET5924 or DIO8016 and uses GPIO 1 as enable. Its four outputs supply:

- front DVDD: 1.0–1.2 V;
- ultrawide DVDD: 1.0–1.23 V;
- front AVDD: 2.8 V;
- ultrawide AVDD: 2.8 V.

### Main/telephoto regulator IC

`i2c11@0x28` is compatible with ET5924 or DIO8016 and uses GPIO 21 as enable. Its outputs supply:

- main DVDD: 1.0–1.2 V;
- telephoto DVDD: 1.0–1.2 V;
- main AVDD: 2.8 V;
- shared main/telephoto AFVDD: 2.8 V.

### Sequencing boundary

The device tree maps each rail plus MCLK/reset states. Ordered enables, voltages and delays are candidate-driver `pw_seq` responsibilities. Because the active front/ultrawide/telephoto module variant and exact-build binaries are unknown, this map links every candidate sequence source but does not invent one universal sequence.

Direct power control is not an application interface.

## Flash

The dual-channel flash is on `i2c6@0x63` with compatible candidates `mediatek,sgm37864` and `mediatek,ocp81375`.

- I²C clock: 400 kHz.
- Hardware enable: GPIO 39.
- Two logical flash channels.
- Thermal cooling interface: two cooling cells.
- Companion gate controller: `i2c6@0x11`, GPIO 103.

The exact shipped controller identity is unresolved.

## Kernel interfaces

### Sensor V4L2 subdevices

MediaTek sensor adapters enumerate dynamically as `/dev/v4l-subdev*`; fixed minor numbers are not part of the map.

Relevant private ioctl families include:

- sensor/scenario information;
- crop and virtual-channel layout;
- PDAF info, data and capability;
- HDR and multi-exposure capability/ranges;
- seamless target scenarios;
- output format and sensor profile;
- video frame rate and scenario maximum FPS.

Examples include `VIDIOC_MTK_G_SENSOR_INFO`, `VIDIOC_MTK_G_CROP_BY_SCENARIO`, `VIDIOC_MTK_G_VCINFO_BY_SCENARIO`, `VIDIOC_MTK_G_PDAF_INFO_BY_SCENARIO`, `VIDIOC_MTK_G_HDR_CAP`, `VIDIOC_MTK_G_SEAMLESS_SCENARIO`, `VIDIOC_MTK_G_SENSOR_PROFILE`, `VIDIOC_MTK_S_VIDEO_FRAMERATE`, and `VIDIOC_MTK_S_MAX_FPS_BY_SCENARIO`.

These are kernel/HAL interfaces, not public Android SDK controls.

### Main autofocus

The PD9302A driver registers a V4L2 lens subdevice with:

- `V4L2_CID_FOCUS_ABSOLUTE`;
- `VCM_IOC_POWER_ON`;
- `VCM_IOC_POWER_OFF`.

It also performs regulator/pinctrl/runtime-PM handling and lens parking during release.

### Telephoto autofocus

The device tree binds `mediatek,cn3968`, but no matching source implementation is indexed. Its controls and private ioctls remain unknown.

### EEPROM calibration

The MediaTek calibration driver creates dynamic instances:

- character devices matching `/dev/camera_eeprom*`;
- classes matching `/sys/class/camera_eepromdrv*`.

It implements `open`, `read`, `write`, `llseek`, `unlocked_ioctl`, and compat ioctl operations. `CAM_CALIOC_S_SENSOR_INFO` selects the sensor/device context. Device ownership and SELinux access must be measured on the target build.

### Flash subdevices

The SGM37864/OCP81375 drivers use V4L2 flash controls for LED mode, torch/flash intensity, timeout, strobe and fault state. Thermal cooling devices may enumerate dynamically under `/sys/class/thermal/cooling_device*`.

## Kernel configuration

The indexed defconfig/source enables or names:

- `CONFIG_MTK_IMGSENSOR=m`;
- `CONFIG_MTK_V4L2_LENS=m`;
- `CONFIG_MTK_V4L2_FLASHLIGHT=m`;
- `CONFIG_MTK_FLASHLIGHT=m`;
- `CONFIG_COMMON_CLK_MT6878_CAM=m`;
- `CONFIG_COMMON_CLK_MT6878_CCU=m`;
- MediaTek CAMSYS, HCP, IMGSYS 7SP, DPE, AIE/FD, PDA and camera power/performance scheduling components.

This establishes kernel subsystem availability, not Android app access.

## Replacement-app consequences

- Four wired sensors do not imply four public Camera2 IDs.
- The replacement app remains on CameraX/Camera2 unless a separately verified privileged route exists.
- Candidate sensor names must not be displayed as retail module identity without runtime proof.
- EEPROM, actuator, flash and sensor device nodes are non-portable and subject to ownership/SELinux/package policy.
- OIS remains unsupported/unknown because no source binding is evidenced.
- Direct register or power sequencing is out of scope for the replacement app.

## Known gaps

- `gap-exact-build-source`: no source/partition set is matched to build `2606151653`.
- `gap-shipped-module-identity`: candidate families are known, exact module variants are not.
- `gap-tele-actuator-driver`: `mediatek,cn3968` source is missing from the indexed repositories.
- `gap-userspace-routing`: kernel topology does not reveal logical IDs, package allowlists, stock routing or vendor-tag meanings.

## Non-claims

The map does not prove exact retail module vendors, exact-build driver loading, public Camera2 reachability, OIS absence, direct app access, or authorization for register/power/calibration control.

Validation: `tools/validate-galaga-camera-hardware-map.py`.
