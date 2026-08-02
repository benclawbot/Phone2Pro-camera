# Phone2Pro Camera

An on-device Android camera project for the CMF Phone 2 Pro, beginning with a hardware and Camera2 capability audit before the production camera pipeline is finalized.

## Repository layout

- `docs/PRODUCT_IDEATION.md` — agreed product direction and UX decisions.
- `docs/DIAGNOSTICS_PLAN.md` — measurements required from the real phone.
- `docs/GALLERY_INTEROP.md` — standard gallery thumbnail and default photo-viewer behavior.
- `diagnostics/` — standalone Android diagnostics app.

## Current phase

Phase 0 establishes what the phone actually exposes: Camera2 hardware levels, physical and concurrent cameras, RAW and reprocessing support, vendor extensions, stream sizes, sensors, codecs, and thermal limits. The production camera app will be designed from the resulting JSON report rather than assumptions.
