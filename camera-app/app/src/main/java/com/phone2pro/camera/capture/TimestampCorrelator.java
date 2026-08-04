package com.phone2pro.camera.capture;

import com.phone2pro.camera.imaging.FrameMetadata;

import java.util.Objects;

/** Fail-closed image/result correlation using frame identity, clock domain and tolerance. */
public final class TimestampCorrelator {
    private final long maximumDeltaNs;

    public TimestampCorrelator(long maximumDeltaNs) {
        if (maximumDeltaNs < 0) {
            throw new IllegalArgumentException("maximumDeltaNs must be non-negative");
        }
        this.maximumDeltaNs = maximumDeltaNs;
    }

    public CorrelatedCaptureFrame correlate(
            ImageTimestamp image,
            FrameMetadata metadata
    ) {
        Objects.requireNonNull(image, "image");
        Objects.requireNonNull(metadata, "metadata");
        if (image.frameNumber() != metadata.frameNumber()) {
            throw new IllegalArgumentException("image and metadata frame numbers do not match");
        }
        if (image.timestampDomain() != metadata.timestampDomain()) {
            throw new IllegalArgumentException("image and metadata clock domains do not match");
        }
        long delta = absoluteDifference(image.timestampNs(), metadata.timestampNs());
        if (delta > maximumDeltaNs) {
            throw new IllegalArgumentException("image and metadata timestamps exceed tolerance");
        }
        return new CorrelatedCaptureFrame(image, metadata, delta);
    }

    public long maximumDeltaNs() { return maximumDeltaNs; }

    private static long absoluteDifference(long left, long right) {
        if (left >= right) {
            return left - right;
        }
        return right - left;
    }
}
