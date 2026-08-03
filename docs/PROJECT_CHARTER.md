# Project Charter

## Mission

Produce an evidence-backed, versioned technical specification of the CMF Phone 2 Pro camera platform and use it to build a high-quality replacement camera application.

The scope includes the complete path from application UI to sensor:

```text
Nothing Camera / replacement app
        ↓
Camera2 / CameraX / hidden or vendor APIs
        ↓
Android CameraService and provider interfaces
        ↓
MediaTek camera HAL and feature pipelines
        ↓
ISP, sensor, actuator, flash, OIS and kernel drivers
```

## Core research question

How does Nothing Camera's Expert mode select and configure the 15 mm-equivalent ultrawide, 24 mm-equivalent main, and 50 mm-equivalent telephoto routes, and which parts of that mechanism can be reproduced by a non-privileged application?

A negative result is valid only for the exact tested interface. The project must distinguish:

- an ignored external parameter;
- a non-exported application route;
- a hidden Camera2/vendor API;
- a signature or privileged permission;
- a Binder identity check;
- a CameraService/system-camera policy;
- a HAL restriction;
- an SELinux restriction;
- a sensor/firmware limitation.

## Workstreams

1. **Evidence and reproducibility** — artifacts, hashes, firmware/build matrix, test protocols.
2. **Public camera surface** — Camera2, CameraX, NDK, extensions, streams and controls.
3. **Nothing Camera static analysis** — manifests, resources, call graphs, mode controllers, vendor-key call sites and JNI.
4. **Nothing Camera dynamic analysis** — differential traces for 0.6×, 1× and 2×, request/session reconstruction and native hooks.
5. **Firmware and framework** — services, AIDL/HIDL, CameraService, camera provider, HAL, libraries, properties, XML and overlays.
6. **MediaTek feature mapping** — MFNR, AIS, HDR, 3A, ZSL, in-sensor zoom, seamless scenarios, CameraFlex, ISP tuning and related features.
7. **Security boundaries** — permissions, allowlists, package identity, SELinux, hidden/system camera policy and exact failure points.
8. **External research** — AOSP, Android documentation, Nothing OSS, MediaTek public source, firmware archives, community reports, open-source camera projects and papers.
9. **Replacement application specification** — backend, capture engine, lens abstraction, processing, storage, performance and test strategy.
10. **Canonical outputs** — capability matrix, routing specification, vendor API reference, firmware interface reference and SDK guide.

## Product constraints

- Processing remains on-device.
- CameraX and Camera2 interoperability are used where appropriate; Camera2 remains available for precise control.
- The image pipeline targets natural colour, texture and sharpening.
- Capture modes are `Quick`, `Auto` and `Max Detail`.
- RAW support is planned after the main multi-frame pipeline.
- The design remains modular so privileged or auxiliary-lens backends can be added without rewriting the processing stack.

## Definition of done

The research programme is complete only when each material camera feature is represented in the capability database with:

- owning subsystem;
- API or call path;
- valid configuration and dependencies;
- evidence source and firmware version;
- user-app reachability;
- privilege requirements;
- observed result or exact failure mode;
- confidence level;
- replacement-app design consequence.

Unknowns may remain, but they must be explicit, bounded and linked to a reproducible test or unavailable artifact.
