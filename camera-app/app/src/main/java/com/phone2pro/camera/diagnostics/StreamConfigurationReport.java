package com.phone2pro.camera.diagnostics;

import java.util.Objects;

/** Non-content stream description safe for diagnostic reports. */
public final class StreamConfigurationReport {
    private final String role;
    private final String format;
    private final int width;
    private final int height;
    private final int maxImages;

    public StreamConfigurationReport(
            String role,
            String format,
            int width,
            int height,
            int maxImages
    ) {
        this.role = requireText(role, "role");
        this.format = requireText(format, "format");
        if (width <= 0 || height <= 0 || maxImages <= 0) {
            throw new IllegalArgumentException("stream dimensions and maxImages must be positive");
        }
        this.width = width;
        this.height = height;
        this.maxImages = maxImages;
    }

    public String role() { return role; }
    public String format() { return format; }
    public int width() { return width; }
    public int height() { return height; }
    public int maxImages() { return maxImages; }

    private static String requireText(String value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + " must not be empty");
        }
        return value;
    }
}
