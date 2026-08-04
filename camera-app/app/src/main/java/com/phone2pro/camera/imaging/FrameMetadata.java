package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Normalized capture metadata required by burst scoring and alignment. */
public final class FrameMetadata {
    private final long frameNumber;
    private final long timestampNs;
    private final TimestampDomain timestampDomain;
    private final long exposureTimeNs;
    private final int sensitivityIso;
    private final long frameDurationNs;
    private final long rollingShutterSkewNs;
    private final float focalLengthMm;

    public FrameMetadata(
            long frameNumber,
            long timestampNs,
            TimestampDomain timestampDomain,
            long exposureTimeNs,
            int sensitivityIso,
            long frameDurationNs,
            long rollingShutterSkewNs,
            float focalLengthMm
    ) {
        if (frameNumber < 0) {
            throw new IllegalArgumentException("frameNumber must be non-negative");
        }
        this.timestampDomain = Objects.requireNonNull(timestampDomain, "timestampDomain");
        if (timestampDomain == TimestampDomain.UNKNOWN) {
            throw new IllegalArgumentException("frame timestamp domain must be known");
        }
        if (exposureTimeNs <= 0 || sensitivityIso <= 0 || frameDurationNs < exposureTimeNs) {
            throw new IllegalArgumentException("invalid exposure, sensitivity or frame duration");
        }
        if (rollingShutterSkewNs < 0) {
            throw new IllegalArgumentException("rollingShutterSkewNs must be non-negative");
        }
        if (!(focalLengthMm > 0.0f) || !Float.isFinite(focalLengthMm)) {
            throw new IllegalArgumentException("focalLengthMm must be finite and positive");
        }
        this.frameNumber = frameNumber;
        this.timestampNs = timestampNs;
        this.exposureTimeNs = exposureTimeNs;
        this.sensitivityIso = sensitivityIso;
        this.frameDurationNs = frameDurationNs;
        this.rollingShutterSkewNs = rollingShutterSkewNs;
        this.focalLengthMm = focalLengthMm;
    }

    public long frameNumber() { return frameNumber; }
    public long timestampNs() { return timestampNs; }
    public TimestampDomain timestampDomain() { return timestampDomain; }
    public long exposureTimeNs() { return exposureTimeNs; }
    public int sensitivityIso() { return sensitivityIso; }
    public long frameDurationNs() { return frameDurationNs; }
    public long rollingShutterSkewNs() { return rollingShutterSkewNs; }
    public float focalLengthMm() { return focalLengthMm; }
}
