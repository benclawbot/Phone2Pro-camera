# Stock-camera behaviour reference

**Reference:** `2026.08.04-1`  
**Target:** CMF Phone 2 Pro (`A001`, `Galaga`)  
**Firmware:** `2606151653`  
**Stock camera:** `com.nothing.camera` `16.1.01.93.20`  
**Issue:** CAM-124 / #99

The machine-readable reference is
`data/stock-camera/behaviour-reference.v1.json`.

It covers Expert, Photo, Portrait, Night and Video as a benchmark and
compatibility baseline. It records evidence gaps instead of filling them with
generic Android behavior or diagnostic-app results.

## Evidence rules

- `VERIFIED`: directly observed on the named build or recovered deterministically
  from the hashed stock APK.
- `PARTIALLY_VERIFIED`: independently supported, with a missing dynamic,
  identity or implementation link.
- `HYPOTHESIS`: a falsifiable implementation candidate.
- `UNKNOWN`: the required stock evidence has not been captured.
- Diagnostic-app and public-capability facts use `nonStock=true`; they are
  comparison baselines, not stock-mode behavior.
- Unknown latency contains no estimates.

## Mode status

| Mode | Status | Current conclusion |
|---|---|---|
| Expert | `PARTIALLY_VERIFIED` | Stock outputs and APK routing agree on IDs `2`, `0`, `3` for 0.6x, 1x, 2x |
| Photo | `UNKNOWN` | External focal launch stayed on the main route; internal behavior is untraced |
| Portrait | `UNKNOWN` | No stock capture; endpoint `5` remains only a candidate composite route |
| Night | `UNKNOWN` | Eight-frame low-light evidence is from the diagnostics app, not stock Night |
| Video | `UNKNOWN` | Public high-speed capability is known; stock stream, stabilization and encoder behavior are not |

## Expert route

| Control | Endpoint | Optical role | Equivalent | Physical focal length | Digital zoom ratio |
|---|---:|---|---:|---:|---:|
| 0.6x | `2` | ultrawide | 15 mm | 1.64 mm | 0 |
| 1x | `0` | wide | 24 mm | 5.56 mm | 0 |
| 2x | `3` | telephoto | 50 mm | 7.10 mm | 0 |

The stock APK uses a direct endpoint table and ultimately passes the selected
integer endpoint to `CameraManager.openCamera` as a string. The exact package
authorization, session parameters, request metadata, processing sequence and
latency remain unresolved.

The exported widget focal route is a verified fallback boundary: audited 15 mm,
24 mm and 50 mm launches all remained on the 5.56 mm / 24 mm-equivalent main
route. It is not a substitute for the internal Expert state machine.

## Reproduction gaps

Photo, Portrait, Night and Video each include required artifacts and a capture
protocol. Closing a gap requires original stock outputs plus synchronized
endpoint, session, request, result, service and file timing under the exact
firmware/package build.

The diagnostic eight-frame low-light burst must not become a stock Night frame
count claim. The public rear high-speed capability must not become a stock Video
profile claim.

## Validation

```bash
python3 tools/validate-stock-camera-behaviour-reference.py
python3 -m unittest tests/test_validate_stock_camera_behaviour_reference.py
```

The validator enforces the five modes, exact Expert route table,
observed-versus-inferred separation, non-stock labels, explicit unknowns, empty
unknown latency metrics and fail-closed compatibility decisions.
