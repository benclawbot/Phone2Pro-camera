# CMF Phone 2 Pro Camera Platform Project

This repository documents and validates the complete camera platform of the CMF Phone 2 Pro (`A001`, `Galaga`) and turns that knowledge into the engineering specification for an on-device replacement camera application.

The project does **not** assume that auxiliary-lens access is impossible merely because public Camera2 enumeration exposes only the main and front cameras. The central reverse-engineering question is how Nothing Camera routes Expert mode to the ultrawide, main, and telephoto sensors, which firmware interfaces it invokes, and where any reproducibility or privilege boundary actually lies.

## Objectives

1. Map the public Android Camera2/CameraX surface.
2. Reverse-engineer Nothing Camera, including Expert-mode lens routing, session setup, vendor keys, feature flags, JNI, and native calls.
3. Map the Android framework, MediaTek camera stack, firmware services, HAL, native libraries, kernel interfaces, permissions, and SELinux boundaries.
4. Correlate device evidence with AOSP, Nothing OSS, MediaTek public sources, firmware dumps, community findings, and computational-photography research.
5. Produce a versioned capability database and a reusable replacement-camera architecture.
6. Build the production camera around on-device processing, natural rendering, and the `Quick`, `Auto`, and `Max Detail` modes.

## Current evidence baseline

- Device: Nothing/CMF Phone 2 Pro, model `A001`, codename `Galaga`, MediaTek `MT6878`.
- Public Camera2 IDs observed: rear `0`, front `1`.
- Rear public camera `0`: Camera2 `LEVEL_3`, RAW, burst, private/YUV reprocessing, OIS, manual sensor and post-processing controls.
- Nothing Camera Expert mode has been independently observed to use distinct 15 mm-equivalent, 24 mm-equivalent, and 50 mm-equivalent optical routes.
- External widget focal presets opened Nothing Camera but the audited outputs remained on the 24 mm-equivalent main lens. This is evidence about that entry path only; it is not treated as proof that the internal Expert routing mechanism cannot be reproduced.
- The device publishes a substantial MediaTek vendor-metadata surface, including MFNR/AIS, HDR, ZSL, ISP tuning, in-sensor zoom, seamless sensor scenarios, CameraFlex/multicam, EIS, and Nothing-specific tuning keys.

## Repository layout

- `docs/` — architecture, research, reverse-engineering notes, specifications, decisions.
- `data/` — structured capability, vendor-tag, service, permission, and test-result datasets.
- `schemas/` — machine-readable schemas for evidence and capability records.
- `tools/` — repeatable extraction, static-analysis, dynamic-analysis, and diagnostic tooling.
- `app/` — replacement camera application when implementation begins.
- `.github/ISSUE_TEMPLATE/` — evidence-driven issue templates.

## Evidence rules

Every material claim must identify its source and confidence:

- `device-observed`
- `source-confirmed`
- `documentation-confirmed`
- `community-corroborated`
- `inferred`
- `unverified`

Negative tests are scoped to the exact mechanism tested. A failed intent, widget, Camera2 request, or camera-ID open does not become a platform-wide impossibility claim without tracing the enforcing layer.

## Architecture constraints

- CameraX with Camera2 interoperability where appropriate.
- Fully on-device processing; no cloud image processing.
- Natural colour and texture, avoiding an oversharpened synthetic look.
- Modular capture and processing stages.
- `Quick`, `Auto`, and `Max Detail` capture modes.
- RAW capture and processing as a later milestone.

See `docs/PROJECT_CHARTER.md`, `docs/EVIDENCE_MODEL.md`, `docs/BASELINE_CAPABILITY_MAP.md`, and the GitHub issue backlog for the complete work programme.
