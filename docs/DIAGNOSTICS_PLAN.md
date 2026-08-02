# CMF Phone 2 Pro diagnostics plan

The production architecture must be based on measurements from the real phone rather than specification sheets alone.

## Static capability audit

For every public and physical camera ID, collect:

- Camera2 hardware support level.
- Lens facing and sensor orientation.
- Logical multi-camera membership and physical camera IDs.
- Concurrent camera combinations.
- Available request capabilities, including RAW, burst capture, reprocessing, manual sensor controls, and logical multi-camera support.
- JPEG, YUV, RAW, and high-resolution output sizes.
- Sensor active array, pixel array, physical size, sensitivity and exposure ranges.
- Focal lengths, apertures, digital zoom and zoom-ratio ranges.
- Optical and electronic stabilization modes.
- Flash, autofocus regions, and maximum output stream counts.
- Camera extensions such as Auto, HDR, Night, Bokeh, and Face Retouch.

Also collect:

- Device and Android build information.
- Gyroscope and accelerometer availability and rates.
- Hardware-accelerated media codecs.
- Memory class and current thermal status.

## First on-device result

The 2026-08-02 report is summarized in `CAPABILITY_AUDIT_2026-08-02.md`.

The decisive static result is that public Camera2 exposes only one rear camera ID and one front camera ID. The rear camera is `LEVEL_3` and supports RAW, burst capture, manual controls, and YUV/PRIVATE reprocessing, but it does not advertise logical multi-camera or physical rear camera IDs. The public rear path exposes a maximum 4080 × 3072 frame rather than the nominal full 50 MP mode.

This is enough to begin a strong single-camera computational pipeline, but not enough to assume direct ultrawide/telephoto access or dual-rear-camera fusion.

## Dynamic benchmark — next required diagnostics stage

The next one-button workflow must collect the runtime evidence that the static report cannot provide:

- Enumerate standard and vendor characteristic/request/result/session key names.
- Record stream minimum-frame durations and JPEG/YUV/RAW stall durations.
- Capture controlled 1×, 2×, and 4× rear samples.
- Record per-frame focal length, crop region, zoom ratio, exposure, ISO, timestamps, rolling-shutter skew, and stabilization state.
- Determine whether the single public rear camera silently switches sensors at any zoom ratio.
- Benchmark sustained 8- and 15-frame YUV bursts at practical resolutions.
- Measure capture latency, inter-frame timing, dropped frames, and timestamp jitter.
- Measure Camera2-to-gyroscope timestamp alignment.
- Compare 1× crops against 2× and 4× output in daylight, indoor, and low-light scenes.
- Measure local alignment, fusion, and JPEG encoding time.
- Track memory peak and thermal changes during repeated Max Detail workloads.
- Verify whether reported rear OIS control changes capture results.

## Decision gates

- Use dual-camera fusion only if a later runtime or vendor-key audit exposes synchronized rear-lens streams and they materially improve detail.
- Otherwise use single-camera multi-frame super-resolution from the public rear camera.
- Treat 12.5 MP as the public source-resolution ceiling unless a tested maximum-resolution or vendor path proves otherwise.
- Use vendor extensions only when they are exposed consistently and outperform the app pipeline.
- Keep all processing and intermediate frames on-device.

## Report handling

The diagnostics app writes local reports to `Downloads/Phone2Pro Diagnostics`. It does not upload reports or image data. Reports and sample frames may be manually attached to a GitHub issue or conversation for analysis.
