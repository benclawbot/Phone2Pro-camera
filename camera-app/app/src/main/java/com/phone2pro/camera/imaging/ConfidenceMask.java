package com.phone2pro.camera.imaging;

import java.util.Arrays;

/** Dense per-cell confidence or validity mask with values in the closed range [0, 1]. */
public final class ConfidenceMask {
    private final int width;
    private final int height;
    private final float[] values;

    public ConfidenceMask(int width, int height, float[] values) {
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("mask dimensions must be positive");
        }
        if (values == null || values.length != width * height) {
            throw new IllegalArgumentException("mask value count must match dimensions");
        }
        for (float value : values) {
            if (!Float.isFinite(value) || value < 0.0f || value > 1.0f) {
                throw new IllegalArgumentException("mask values must be finite and within [0, 1]");
            }
        }
        this.width = width;
        this.height = height;
        this.values = Arrays.copyOf(values, values.length);
    }

    public static ConfidenceMask filled(int width, int height, float value) {
        float[] values = new float[Math.multiplyExact(width, height)];
        Arrays.fill(values, value);
        return new ConfidenceMask(width, height, values);
    }

    public int width() { return width; }
    public int height() { return height; }

    public float valueAt(int x, int y) {
        if (x < 0 || x >= width || y < 0 || y >= height) {
            throw new IndexOutOfBoundsException("mask coordinate outside dimensions");
        }
        return values[y * width + x];
    }

    public float[] copyValues() {
        return Arrays.copyOf(values, values.length);
    }
}
