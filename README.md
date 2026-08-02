# Phone2Pro-camera

Privacy-first, fully on-device camera development for the CMF Phone 2 Pro, with authentic zoom detail as the flagship goal.

## Current status

- A standalone diagnostics app lives under `diagnostics/`.
- The first on-device static capability report was completed on 2026-08-02.
- Findings are documented in `docs/CAPABILITY_AUDIT_2026-08-02.md`.
- Public Camera2 exposes one rear and one front camera ID; the rear path is `LEVEL_3` with RAW, burst, manual controls, and YUV/PRIVATE reprocessing, but no logical multi-camera or physical rear camera IDs.
- The next diagnostics stage is a one-button dynamic zoom and burst-throughput audit before the Max Detail algorithm is finalized.

See `docs/PRODUCT_IDEATION.md` for the agreed product direction and `docs/DIAGNOSTICS_PLAN.md` for the measurement gates.
