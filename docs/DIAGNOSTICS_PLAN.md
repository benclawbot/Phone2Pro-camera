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

## Dynamic benchmarks to add after static reporting

- Sustained 8–15 frame JPEG/YUV bursts at main and telephoto focal lengths.
- Capture latency, inter-frame timing, dropped frames, and timestamp jitter.
- Main/telephoto timestamp synchronization and geometric alignment.
- Main-camera crop versus telephoto quality across daylight, indoor, and low-light scenes.
- Local alignment, fusion, and JPEG encoding time.
- Memory peak, battery consumption, and thermal throttling during repeated Max Detail captures.
- Subject-motion and hand-motion thresholds for Quick, Auto, and Max Detail fallback.

## Decision gates

- Use dual-camera fusion only if concurrent or physical-camera streams can be synchronized and materially improve detail.
- Otherwise use single-camera multi-frame super-resolution with automatic lens selection.
- Use vendor extensions only when they are exposed consistently and outperform the app pipeline.
- Keep all processing and intermediate frames on-device.

## Report handling

The diagnostics app writes a local JSON report to `Downloads/Phone2Pro Diagnostics`. It does not upload reports or image data. The report may be manually attached to a GitHub issue or conversation for analysis.
