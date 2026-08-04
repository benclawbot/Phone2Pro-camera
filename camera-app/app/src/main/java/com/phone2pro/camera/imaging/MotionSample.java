package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Timestamped gyroscope or optical-stabilization sample. */
public final class MotionSample {
    public enum Source {
        GYROSCOPE_RAD_PER_SECOND,
        OIS_LENS_POSITION,
        UNKNOWN_VENDOR_SIGNAL
    }

    private final Source source;
    private final long timestampNs;
    private final TimestampDomain timestampDomain;
    private final double x;
    private final double y;
    private final double z;

    public MotionSample(
            Source source,
            long timestampNs,
            TimestampDomain timestampDomain,
            double x,
            double y,
            double z
    ) {
        this.source = Objects.requireNonNull(source, "source");
        this.timestampDomain = Objects.requireNonNull(timestampDomain, "timestampDomain");
        if (timestampDomain == TimestampDomain.UNKNOWN) {
            throw new IllegalArgumentException("motion timestamp domain must be known");
        }
        if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)) {
            throw new IllegalArgumentException("motion vector must be finite");
        }
        this.timestampNs = timestampNs;
        this.x = x;
        this.y = y;
        this.z = z;
    }

    public Source source() { return source; }
    public long timestampNs() { return timestampNs; }
    public TimestampDomain timestampDomain() { return timestampDomain; }
    public double x() { return x; }
    public double y() { return y; }
    public double z() { return z; }
}
