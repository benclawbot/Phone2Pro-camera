package com.phone2pro.camera.capture;

import com.phone2pro.camera.imaging.FrameMetadata;

import java.util.Objects;

/** One image/metadata pair whose frame identity and timestamp correlation were validated. */
public final class CorrelatedCaptureFrame {
    private final ImageTimestamp image;
    private final FrameMetadata metadata;
    private final long timestampDeltaNs;

    CorrelatedCaptureFrame(
            ImageTimestamp image,
            FrameMetadata metadata,
            long timestampDeltaNs
    ) {
        this.image = Objects.requireNonNull(image, "image");
        this.metadata = Objects.requireNonNull(metadata, "metadata");
        if (timestampDeltaNs < 0) {
            throw new IllegalArgumentException("timestampDeltaNs must be non-negative");
        }
        this.timestampDeltaNs = timestampDeltaNs;
    }

    public ImageTimestamp image() { return image; }
    public FrameMetadata metadata() { return metadata; }
    public long timestampDeltaNs() { return timestampDeltaNs; }
}
