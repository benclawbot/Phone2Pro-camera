package com.phone2pro.camera.capture;

import com.phone2pro.camera.imaging.TimestampDomain;

import java.util.Objects;

/** Pixel-free identity and timestamp for an acquired image buffer. */
public final class ImageTimestamp {
    private final String requestId;
    private final long frameNumber;
    private final long timestampNs;
    private final TimestampDomain timestampDomain;

    public ImageTimestamp(
            String requestId,
            long frameNumber,
            long timestampNs,
            TimestampDomain timestampDomain
    ) {
        this.requestId = requireText(requestId, "requestId");
        if (frameNumber < 0 || timestampNs < 0) {
            throw new IllegalArgumentException("frameNumber and timestampNs must be non-negative");
        }
        this.timestampDomain = Objects.requireNonNull(timestampDomain, "timestampDomain");
        if (timestampDomain == TimestampDomain.UNKNOWN) {
            throw new IllegalArgumentException("image timestamp domain must be known");
        }
        this.frameNumber = frameNumber;
        this.timestampNs = timestampNs;
    }

    public String requestId() { return requestId; }
    public long frameNumber() { return frameNumber; }
    public long timestampNs() { return timestampNs; }
    public TimestampDomain timestampDomain() { return timestampDomain; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.trim().isEmpty()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
