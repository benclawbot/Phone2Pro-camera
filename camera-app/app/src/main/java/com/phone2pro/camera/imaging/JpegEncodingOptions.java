package com.phone2pro.camera.imaging;

import java.util.Objects;

/** Explicit JPEG output and metadata privacy options. */
public final class JpegEncodingOptions {
    private final int quality;
    private final ColorSpace outputColorSpace;
    private final boolean includeLocation;
    private final boolean includeDiagnosticMetadata;

    public JpegEncodingOptions(
            int quality,
            ColorSpace outputColorSpace,
            boolean includeLocation,
            boolean includeDiagnosticMetadata
    ) {
        if (quality < 1 || quality > 100) {
            throw new IllegalArgumentException("JPEG quality must be within [1, 100]");
        }
        this.outputColorSpace = Objects.requireNonNull(outputColorSpace, "outputColorSpace");
        if (outputColorSpace != ColorSpace.SRGB && outputColorSpace != ColorSpace.DISPLAY_P3) {
            throw new IllegalArgumentException("JPEG output must use nonlinear sRGB or Display P3");
        }
        this.quality = quality;
        this.includeLocation = includeLocation;
        this.includeDiagnosticMetadata = includeDiagnosticMetadata;
    }

    public int quality() { return quality; }
    public ColorSpace outputColorSpace() { return outputColorSpace; }
    public boolean includeLocation() { return includeLocation; }
    public boolean includeDiagnosticMetadata() { return includeDiagnosticMetadata; }
}
