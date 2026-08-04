# Computational-photography literature review

**Index version:** 2026.08.04-1  
**Target:** CMF Phone 2 Pro replacement camera  
**Issue:** CAM-097 / #81

## Purpose

This review converts primary computational-photography literature and authoritative implementations into bounded requirements for `Quick`, `Auto`, and `Max Detail`. It records assumptions, common artefacts, compute, memory, licensing, mobile risks and benchmarks.

Paper descriptions are not implementation licences. A paper-only method must be independently implemented and reviewed for code, model, dataset and patent obligations before shipping.

## Mode policy

### Quick

Quick prioritizes bounded latency and memory. It may use a small constant-exposure burst only when timestamps and alignment are reliable. Global tone mapping and conservative detail enhancement are preferred. Any low-confidence alignment collapses to the reference frame.

### Auto

Auto may use motion-metered constant-exposure RAW bursts, tile alignment, robust merge and moderate tone/detail processing. Frame count and exposure must adapt to motion, noise, thermal and memory budgets.

### Max Detail

Max Detail may attempt RAW multi-frame super-resolution, larger bursts, gyro-assisted alignment and local Laplacian detail enhancement. Learned KPN denoising remains experimental until model provenance, target-sensor calibration and on-device budgets are verified.

## Methods

### `method-hdrplus-constant-exposure-raw-burst`

Hasinoff et al. capture equal-exposure underexposed RAW frames, align them and merge with a hybrid spatial/temporal Wiener approach. Constant exposure avoids bracket-alignment instability and protects highlights.

**Assumptions:** manual per-frame control, RAW access, calibrated black/white levels, stable exposure, enough motion diversity, reliable timestamps.  
**Artefacts:** ghosting, zippering, local blur, fixed-pattern/noise-model mismatch, highlight colour errors.  
**Budget:** medium-to-high compute and memory; the paper reports seconds for a 12 MP mobile image.  
**Modes:** Auto, Max Detail.  
**Licence:** production code is not published as a reusable reference; independent implementation and patent review are required.

### `method-motion-metered-low-light-burst`

Liba et al. choose frame count and exposure from estimated camera/scene motion, then use high-noise alignment and robust merging. This is a policy layer, not one fixed denoiser.

**Assumptions:** pre-capture motion estimate, exposure control, low-light noise model, subject-motion rejection.  
**Artefacts:** motion trails, frozen/noisy moving regions, colour/WB errors, unnatural day-like low-light rendering.  
**Budget:** variable; long bursts and high ISO raise memory, thermal and latency risk.  
**Modes:** Auto and Max Detail; never unconditional Quick.

### `method-fft-tile-alignment`

The HDR+ pipeline uses coarse-to-fine tile alignment with frequency-domain matching. Small independent tiles limit the impact of parallax and local motion.

**Assumptions:** textured tiles, bounded displacement, sufficient signal, stable clock/frame identity.  
**Artefacts:** repeated-texture mismatch, block boundaries, invalid low-texture tiles and occlusion leakage.  
**Budget:** medium compute, low-to-medium temporary memory when tiled.  
**Modes:** Quick with small bursts, Auto, Max Detail.

### `method-robust-wiener-burst-merge`

HDR+ combines aligned frames with spatial/temporal frequency filtering and rejects inconsistent content. It is a learning-free baseline for noise reduction without invented detail.

**Assumptions:** valid local alignment, calibrated signal-dependent noise, enough consistent samples.  
**Artefacts:** waxy texture, ringing, chroma blotches and residual ghosts when confidence is wrong.  
**Budget:** medium compute and memory proportional to tile/frame count.  
**Modes:** Auto and Max Detail; a reduced variant may be used in Quick.

### `method-handheld-raw-mfsr`

Wronski et al. use natural hand tremor to reconstruct full-colour output directly from shifted CFA RAW frames, increasing resolution and signal-to-noise without a separate demosaic stage.

**Assumptions:** subpixel sampling diversity, accurate local motion, RAW CFA knowledge, robust occlusion masks.  
**Artefacts:** false detail, moiré, zippering, texture collapse, edge doubling and route-change inconsistency.  
**Budget:** high compute and high burst memory; the reported production implementation processes each 12 MP input frame on mobile but remains substantially more expensive than a reference-frame path.  
**Modes:** Max Detail; Auto only for verified zoom/detail scenarios.

### `method-kpn-burst-denoising`

Mildenhall et al. predict spatially varying kernels that jointly align and denoise a burst. The authoritative training repository is Apache-2.0 but archived and is not a mobile inference implementation.

**Assumptions:** representative sensor/noise training distribution, fixed input conventions, model/runtime support.  
**Artefacts:** hallucinated or smeared texture, temporal leakage, colour shifts and severe domain mismatch on a new sensor.  
**Budget:** high model compute, activation memory and model storage.  
**Modes:** experimental Max Detail only.

### `method-gyro-aided-alignment-seed`

Zhang and Stevenson combine gyro-derived rotation with feature-derived translation as an initial homography estimate and refine it with an unscented Kalman filter.

**Assumptions:** calibrated gyro/camera clocks, intrinsics, rolling-shutter awareness, low sensor bias and correct frame exposure timing.  
**Artefacts:** global warp error, edge stretch and worse alignment when clocks or calibration are wrong.  
**Budget:** low sensor-buffer memory and medium estimation compute.  
**Modes:** Auto or Max Detail only after clock-domain validation; image alignment remains authoritative.

### `method-exposure-fusion`

Mertens et al. fuse bracketed images using contrast, saturation and well-exposedness weights in a multiresolution pyramid without constructing a radiometric HDR image. OpenCV provides an Apache-2.0 reference implementation.

**Assumptions:** aligned bracketed inputs, consistent colour response and sufficient exposure coverage.  
**Artefacts:** ghosting, halos, local contrast reversal and saturation shifts.  
**Budget:** low-to-medium compute and pyramid memory.  
**Modes:** Quick/Auto only when bracket alignment is verified; not the default moving-scene burst path.

### `method-reinhard-global-tone-map`

Reinhard et al. provide a simple photographic global/local tone-reproduction family. OpenCV includes an Apache-2.0 global implementation suitable as a validation oracle.

**Assumptions:** linear/high-bit-depth luminance and stable white balance.  
**Artefacts:** flat local contrast, grey shadows, highlight compression and colour shifts if applied in the wrong space.  
**Budget:** low compute and memory.  
**Modes:** Quick and Auto baseline; Max Detail may use it as fallback.

### `method-local-laplacian-detail-tone`

Paris et al. use Laplacian pyramids and pointwise remapping for edge-aware smoothing, detail enhancement and tone mapping without optimization.

**Assumptions:** correctly linearized colour/luminance, bounded detail gain and enough pyramid precision.  
**Artefacts:** halos when approximated poorly, amplified noise, crunchy microcontrast and memory spikes at full resolution.  
**Budget:** medium-to-high compute and multi-level full-frame memory.  
**Modes:** Max Detail, or moderate Auto after memory/thermal benchmarks.

## Benchmarks

### `benchmark-hdrplus-burst`

Use the HDR+ burst dataset for alignment, merge and noise-model regression. Its sensor/scene distribution is not Galaga, so it cannot replace target captures.

### `benchmark-burstsr`

The BurstSR dataset pairs smartphone bursts with DSLR ground truth and is useful for RAW burst super-resolution. Registration and cross-camera ground truth can reward colour/optics differences unrelated to the target.

### `benchmark-sidd`

SIDD contains real smartphone noisy/clean pairs across five devices and is useful for sensor-domain and sRGB denoising checks. Training/test use remains subject to the dataset’s published terms.

### `benchmark-dnd`

DND evaluates real photographic noise with carefully produced references and guards against overfitting to synthetic Gaussian noise. It is not a burst or mobile-route benchmark.

### `benchmark-galaga-controlled`

A private project-owned benchmark must cover exact Galaga builds, all verified routes, static/moving scenes, low light, backlight, fine texture, foliage, faces, text, saturated colour and tripod/handheld motion. Originals remain private; hashes, protocols and aggregate metrics may be committed.

## Acceptance metrics and failure gates

Measure at minimum:

- alignment confidence and invalid-region rate;
- ghost/double-edge and motion-mask precision;
- noise power, colour error, clipped highlights and shadow detail;
- spatial detail without hallucination;
- peak memory, processing latency, thermal rise and cancellation latency;
- fallback frequency and reference-frame quality.

PSNR/SSIM alone are insufficient. No method advances when it improves a public benchmark but causes target-device ghosts, colour instability, excessive memory, unbounded latency or misleading detail.

## Implementation direction

1. Start with constant-exposure RAW bursts only when RAW and metadata are verified.
2. Make tile alignment and confidence masks replaceable behind `FrameAligner`.
3. Use robust learning-free merge as the Auto baseline.
4. Keep reference-frame fallback mandatory at every stage.
5. Gate MFSR, KPN and local Laplacian processing behind Max Detail and resource policy.
6. Treat gyro as an optional alignment seed with fail-closed clock calibration.
7. Use global tone mapping first; enable local detail only after noise and halo tests.
8. Preserve method/code/model/dataset licences in the compliance register before implementation.

## Non-claims

- A paper’s reported runtime is not a Galaga benchmark.
- A published method does not prove patent clearance or code reuse rights.
- Public datasets do not represent the target sensor, lens stack, ISP or user population.
- A learned model does not generalize to Galaga without sensor/noise validation.
- Mode assignment is a design recommendation until executable resource benchmarks replace it.

## Maintenance

Update this review when benchmark evidence changes, an implementation/model licence is resolved, Galaga RAW/gyro capability is verified, or resource measurements change a mode assignment.

Machine-readable source: `research/computational-photography-literature.v1.json`  
Validation: `tools/validate-computational-photography-literature.py`
