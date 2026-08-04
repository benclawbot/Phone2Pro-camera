package com.phone2pro.camera.capture;

import java.util.Objects;

/** Negotiated stream requirements before Android surfaces are allocated. */
public final class StreamSpec {
    private final StreamRole role;
    private final String format;
    private final int width;
    private final int height;
    private final int maxImages;
    private final boolean physicalOutput;
    private final String physicalCameraId;

    public StreamSpec(
            StreamRole role,
            String format,
            int width,
            int height,
            int maxImages,
            boolean physicalOutput,
            String physicalCameraId
    ) {
        this.role = Objects.requireNonNull(role, "role");
        this.format = Objects.requireNonNull(format, "format");
        if (format.isEmpty() || width <= 0 || height <= 0 || maxImages <= 0) {
            throw new IllegalArgumentException("invalid stream format, size or buffer count");
        }
        if (physicalOutput && (physicalCameraId == null || physicalCameraId.isEmpty())) {
            throw new IllegalArgumentException("physical output requires a physical camera ID");
        }
        if (!physicalOutput && physicalCameraId != null) {
            throw new IllegalArgumentException("non-physical output cannot carry a physical camera ID");
        }
        this.width = width;
        this.height = height;
        this.maxImages = maxImages;
        this.physicalOutput = physicalOutput;
        this.physicalCameraId = physicalCameraId;
    }

    public static StreamSpec publicOutput(
            StreamRole role,
            String format,
            int width,
            int height,
            int maxImages
    ) {
        return new StreamSpec(role, format, width, height, maxImages, false, null);
    }

    public StreamRole role() { return role; }
    public String format() { return format; }
    public int width() { return width; }
    public int height() { return height; }
    public int maxImages() { return maxImages; }
    public boolean physicalOutput() { return physicalOutput; }
    public String physicalCameraId() { return physicalCameraId; }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof StreamSpec)) {
            return false;
        }
        StreamSpec stream = (StreamSpec) other;
        return role == stream.role
                && format.equals(stream.format)
                && width == stream.width
                && height == stream.height
                && maxImages == stream.maxImages
                && physicalOutput == stream.physicalOutput
                && Objects.equals(physicalCameraId, stream.physicalCameraId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(
                role,
                format,
                width,
                height,
                maxImages,
                physicalOutput,
                physicalCameraId
        );
    }
}
